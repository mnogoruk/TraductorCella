import asyncio
import threading
import time

from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction, DatabaseError
import logging
import pandas as pd
from django.db.models import OuterRef, Subquery, Exists, F, Q, Count
from background_task import background

from cella.models import File
from cella.service import Operators
from specification.models import Specification
from utils.function import random_str

from .models import Resource, ResourceCost, ResourceProvider, ResourceAction

logger = logging.getLogger(__name__)


class Resources:
    class ResourceDoesNotExist(ObjectDoesNotExist):
        pass

    class ExternalIdUniqueError(Exception):
        pass

    class CreateError(Exception):
        pass

    class QueryError(Exception):
        pass

    class UpdateError(Exception):
        pass

    @classmethod
    def get(cls, resource, related=None, prefetched=None):
        if prefetched is None:
            prefetched = []
        if related is None:
            related = []
        if not isinstance(resource, Resource):
            try:
                return Resource.objects.select_related(*related).prefetch_related(*prefetched).get(id=resource)
            except IntegrityError:
                logger.warning(f"Resource does not exist. Id: '{resource}'")
                raise cls.ResourceDoesNotExist()
        else:
            return resource

    @classmethod
    def set_amount(cls, resource, amount_value, user, save=True):
        resource = cls.get(resource)

        resource.amount = amount_value
        if amount_value < 0:
            logger.warning(f"resources amount < 0 for resources '{resource.id}'")

        action = ResourceAction(
            resource=resource,
            action_type=ResourceAction.ActionType.SET_AMOUNT,
            operator=Operators.get_operator(user),
            value=str(amount_value)
        )

        if save:
            resource.save()
            action.save()

        return amount_value, action

    @classmethod
    def change_amount(cls, resource, delta_amount, user=None, save=True):
        resource = cls.get(resource)

        resource.amount += delta_amount
        if resource.amount < 0:
            logger.warning(f"resources amount < 0 for resources '{resource.id}'")
        action = ResourceAction(
            resource=resource,
            action_type=ResourceAction.ActionType.CHANGE_AMOUNT,
            operator=Operators.get_operator(user),
            value=str(delta_amount)
        )

        if save:
            resource.save()
            action.save()

        return resource.amount, action

    @classmethod
    def set_cost(cls, resource, cost_value, user, save=True, verified=False):
        if not verified:
            resource = cls.get(resource, prefetched=['res_specs__specification'])
            specifications = []
            for res__spec in resource.res_specs.all():
                specification = res__spec.specification
                specification.verified = False
                specifications.append(specification)
            Specification.objects.bulk_update(specifications, fields=['verified'])

        else:
            resource = cls.get(resource)

        if cost_value < 0:
            logger.warning(f"resources cost < 0 for resources '{resource.id}'")
        cost = ResourceCost(
            resource=resource,
            value=cost_value,
            verified=verified
        )

        action = ResourceAction(
            resource=resource,
            action_type=ResourceAction.ActionType.SET_COST,
            operator=Operators.get_operator(user),
            value=str(cost_value)
        )

        if save:
            cost.save()
            action.save()

        return cost, action

    @classmethod
    def expired_count(cls):
        count = Resource.objects.aggregate(
            count=Count('id', filter=Q(amount_limit__gte=F('amount'))))
        print(count)
        return count['count']

    @classmethod
    def update_fields(cls, resource, resource_name=None, external_id=None, provider_name: str = None, user=None):

        resource = cls.get(resource)
        operator = Operators.get_operator(user)
        value_data = []
        try:
            with transaction.atomic():
                if resource_name is not None:
                    resource.name = resource_name
                    value_data.append(f"name={resource_name}")
                if external_id is not None:
                    resource.external_id = external_id
                    value_data.append(f"external_id={external_id}")
                if provider_name is not None:
                    resource.provider = ResourceProvider.objects.get_or_create(name=provider_name)[0]
                    value_data.append(f"provider_name={provider_name}")

                if len(value_data) == 0:
                    logger.warning(f"No fields updated for resources with id '{resource.id}'")
                    return cls.detail(resource)
                else:
                    ResourceAction.objects.create(
                        resource=resource,
                        action_type=ResourceAction.ActionType.UPDATE_FIELDS,
                        operator=operator,
                        value="|".join(value_data)
                    )
        except DatabaseError:
            raise cls.UpdateError()

        return cls.detail(resource)

    @classmethod
    def detail(cls, resource):

        resource = cls.get(resource)
        try:
            cost = ResourceCost.objects.filter(resource=resource).latest('time_stamp')
        except ResourceCost.DoesNotExist:
            logger.warning(f"ResourceCost does not exist for Resource with id '{resource.id}'")
            cost = ResourceCost.objects.create(resource=resource, value=0)

        resource.cost = cost.value
        resource.verified = cost.verified

        return resource

    @classmethod
    def create(cls, resource_name: str, external_id: str, cost_value: float = 0, amount_value: float = 0,
               provider_name: str = None, user=None):

        if cost_value is None:
            cost_value = .0

        if amount_value is None:
            amount_value = .0

        if provider_name is not None:
            provider = ResourceProvider.objects.get_or_create(name=provider_name)[0]

        else:
            provider = None

        try:
            with transaction.atomic():
                try:
                    resource = Resource.objects.create(name=resource_name,
                                                       external_id=external_id,
                                                       provider=provider,
                                                       amount=amount_value)

                except IntegrityError:
                    logger.warning(f"Not unique external id '{external_id}'")
                    raise cls.ExternalIdUniqueError()

                operator = Operators.get_operator(user)

                ResourceAction(
                    resource=resource,
                    action_type=ResourceAction.ActionType.CREATE,
                    operator=operator
                ).save()

                cost, cost_action = cls.set_cost(resource, cost_value, operator, True, True)
                amount, amount_action = cls.set_amount(resource, amount_value, operator)

                resource.cost = cost.value
                resource.cost_time_stamp = cost.time_stamp
                resource.amount_time_stamp = amount_action.time_stamp
                resource.verified = cost.verified

        except DatabaseError as ex:
            logger.warning(f"Create error resource_name={resource_name}, external_id={external_id}, "
                           f"cost_value={cost_value}, amount_value={amount_value}, provider_name={provider_name}")
            raise cls.CreateError(ex)

        return resource

    @classmethod
    def bulk_create(cls, data: list, user):
        # TODO: test, optimize
        errors = []
        for resource in data:
            resource['user'] = user
            try:
                cls.create(**resource)
            except cls.ExternalIdUniqueError as ex:
                errors.append(ex)
                logger.warning(f"Exceptions caught while bulk creating {ex}")
                continue
        return errors

    @classmethod
    def list(cls):
        try:
            cost_qr = ResourceCost.objects.filter(resource=OuterRef('pk')).order_by('-time_stamp')
            amount_action = ResourceAction.objects.filter(
                resource=OuterRef('pk'),
                action_type__in=[ResourceAction.ActionType.SET_AMOUNT, ResourceAction.ActionType.CHANGE_AMOUNT]
            ).order_by('-time_stamp')
            query = Resource.objects.select_related('provider').annotate(
                cost=Subquery(cost_qr.values('value')[:1]),
                last_change_cost=Subquery(cost_qr.values('time_stamp')[:1]),
                last_change_amount=Subquery(amount_action.values('time_stamp')[:1]),
                verified=Subquery(cost_qr.values('verified')[:1]),
            )
        except DatabaseError as ex:
            logger.error(f"Error while getting resource list: {ex}")
            raise cls.QueryError()

        return query.order_by('verified')

    @classmethod
    def shortlist(cls):
        query_cost = ResourceCost.objects.filter(resource=OuterRef('pk')).order_by('-time_stamp')
        query = Resource.objects.select_related('provider').annotate(cost=Subquery(query_cost.values('value')[:1]))
        return query

    @classmethod
    def providers(cls):
        return ResourceProvider.objects.all()

    @classmethod
    def with_unverified_cost(cls):
        try:
            cost_ver_qr = ResourceCost.objects.filter(resource=OuterRef('pk'), verified=True).order_by('-time_stamp')
            cost_unver_qr = ResourceCost.objects.filter(resource=OuterRef('pk'), verified=False).order_by('-time_stamp')
            amount_action = ResourceAction.objects.filter(
                resource=OuterRef('pk'),
                action_type__in=[ResourceAction.ActionType.SET_AMOUNT, ResourceAction.ActionType.CHANGE_AMOUNT]
            ).order_by('-time_stamp')
            query = Resource.objects.select_related('provider').annotate(
                verified=~Exists(cost_unver_qr),
                old_cost=Subquery(cost_ver_qr.values('value')[:1]),
                new_cost=Subquery(cost_unver_qr.values('value')[:1]),
                last_change_cost=Subquery(cost_unver_qr.values('time_stamp')[:1]),
                last_change_amount=Subquery(amount_action.values_list('time_stamp')[:1])
            ).filter(verified=False)
            return query
        except DatabaseError as ex:
            logger.error(f"Database error: {ex}")
            raise cls.QueryError()

    @classmethod
    def verify_cost(cls, ids, user):
        with transaction.atomic():
            resources = Resource.objects.filter(id__in=ids)
            for resource in resources:
                costs = ResourceCost.objects.filter(resource=resource, verified=False).update(verified=True)
                ResourceAction.objects.create(
                    resource=resource,
                    action_type=ResourceAction.ActionType.VERIFY_COST,
                    operator=Operators.get_operator(user)
                )
        return costs

    @classmethod
    def actions(cls, r_id):
        return ResourceAction.objects.filter(resource_id=r_id).order_by('-time_stamp')

    @classmethod
    def delete(cls, resource, user):
        resource = cls.get(resource)
        resource.delete()

    @classmethod
    def bulk_delete(cls, ids, user):
        Resource.objects.filter(id__in=ids).delete()

    @classmethod
    async def create_from_excel(cls, file_instance_id, operator_id):
        asyncio.create_task(create_from_excel(file_instance_id, operator_id))
        return


async def create_from_excel(file_instance_id, operator_id=None):
    try:
        file = await sync_to_async(File.objects.get)(id=file_instance_id)
        excel = pd.read_excel(file.file)
    except Exception:
        logger.warning(f"Error while reading excel file {file_instance_id}", exc_info=True)
        raise
    try:
        operator = await (sync_to_async(Operators.get_operator)(operator_id))
        actions = []
        costs = []
        provider_dict = {}
        ext = []
        resources = []
        for x in range(excel.shape[0]):

            row = excel.iloc[x]
            if (not pd.isnull(row['Спецификация / Ресурс'])) and \
                    row['Спецификация / Ресурс'].lower() == 'resource':
                obj = dict()
                obj['name'] = row['Название']

                if pd.isnull(row['ID']):
                    external_id = random_str(24)

                else:
                    external_id = str(int(row['ID']))

                if external_id in ext:
                    continue
                else:
                    ext.append(external_id)

                obj['external_id'] = external_id

                if pd.isnull(row['Количество ']):
                    amount_value = 0
                else:
                    amount_value = row['Количество ']

                if pd.isnull(row['Поставщик']):
                    provider = None
                else:
                    provider_name = row['Поставщик']
                    if provider_name not in provider_dict:
                        provider = (await (sync_to_async(ResourceProvider.objects.get_or_create)(name=provider_name)))[
                            0]
                        provider_dict[provider_name] = provider
                    else:
                        provider = provider_dict[provider_name]

                obj['provider'] = provider
                resource = await (sync_to_async(Resource.objects.create)(**obj))
                if pd.isnull(row['Цена']):
                    cost_value = 0
                else:
                    cost_value = row['Цена']
                cost, cost_action = Resources.set_cost(resource, cost_value, operator, verified=True, save=False)
                amount, amount_action = Resources.set_amount(resource, amount_value, operator, save=False)
                create_action = ResourceAction(
                    resource=resource,
                    operator=operator,
                    action_type=ResourceAction.ActionType.CREATE)

                costs.append(cost)
                actions.append(cost_action)
                actions.append(amount_action)
                actions.append(create_action)
                resources.append(resource)

        group = asyncio.gather((sync_to_async(ResourceCost.objects.bulk_create)(costs)),
                               (sync_to_async(ResourceAction.objects.bulk_create)(actions)),
                               (sync_to_async(Resource.objects.bulk_update)(resources, fields=['amount'])))
        await group
    except Exception as ex:
        logger.warning(f"Error while creating resources from excel", exc_info=True)
        raise Resources.CreateError()

import asyncio
from datetime import datetime

import aiohttp
from asgiref.sync import sync_to_async, async_to_sync
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction, DatabaseError
import logging
import pandas as pd
from django.db.models import OuterRef, Subquery, Exists, F, Q, Count, Sum

from cella.models import File
from cella.service import Operators
from specification.models import Specification, SpecificationResource
from utils.function import random_str

from .models import Resource, ResourceCost, ResourceProvider, ResourceAction, ResourceDelivery

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
    def make_delivery(cls, resource, name=None, provider_name=None, cost=0, amount=0, comment=None, time_stamp=None,
                      user=None):
        resource = cls.get(resource)
        print(f'{resource}')
        print(f'{name}')
        print(f'{provider_name}')
        print(f'{cost}')
        print(f'{amount}')
        print(f'{comment}')
        print(f'{time_stamp}')
        print(f'{user}')
        print(type(time_stamp))
        if name is not None:
            resource.name = name

        resource.comment = comment
        provider = ResourceProvider.objects.get_or_create_by_name(provider_name).object()

        resource.provider = provider
        delivery = cls._create_delivery(resource, provider, cost, amount, comment, time_stamp, name)

        cost, cost_action = cls.set_cost(resource, cost, user=user, save=False)
        amount, amount_action = cls.change_amount(resource, amount, user=user, save=False)
        cost_action.time_stamp = datetime(
            year=time_stamp.year,
            month=time_stamp.month,
            day=time_stamp.day,
        )
        print(cost_action.time_stamp)
        amount_action.time_stamp = datetime(
            year=time_stamp.year,
            month=time_stamp.month,
            day=time_stamp.day,
        )
        try:
            with transaction.atomic():
                delivery.save()
                resource.save()
                cost.save()
                cost_action.save()
                amount_action.save()
        except Exception as ex:
            logger.error(f"make delivery error | {cls.__name__}", exc_info=True)

        return delivery

    @classmethod
    def _create_delivery(cls, resource, provider, cost, amount, comment, time_stamp, name):
        delivery = ResourceDelivery()
        delivery.set_resource(resource)
        delivery.set_amount(amount)
        delivery.set_provider(provider)
        delivery.set_comment(comment)
        delivery.set_cost(cost)
        delivery.set_name(name)
        delivery.set_time_stamp(time_stamp)

        return delivery

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

        resource.amount = float(resource.amount) + float(delta_amount)
        if resource.amount < 0:
            logger.warning(f"resources amount < 0 for resources '{resource}'")
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
    def set_cost(cls, resource, cost_value, user, save=True, verified=False, send=False):
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
            query_cost = ResourceCost.objects.filter(resource_id=OuterRef('resource_id')).order_by('-time_stamp')

            query_res_spec = SpecificationResource.objects.filter(
                specification=OuterRef('pk'),
            ).values('specification_id').annotate(
                total_cost=Sum(Subquery(query_cost.values('value')[:1]) * F('amount')))

            specifications = Specification.objects.filter(res_specs__resource=resource).annotate(
                prime_cost=Subquery(query_res_spec.values('total_cost'))).values('product_id', 'prime_cost')
            specifications = sync_to_async(specifications.all)
            spc = async_to_sync(cls.send_prime_cost)

            spc(specifications)
        return cost, action

    @classmethod
    def expired_count(cls):
        count = Resource.objects.aggregate(
            count=Count('id', filter=Q(amount_limit__gte=F('amount'))))
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
            logger.warning(f"Update error | {cls.__name__}", exc_info=True)
            raise cls.UpdateError()

        return cls.detail(resource)

    @classmethod
    def detail(cls, resource):

        resource = cls.get(resource)
        try:
            cost = ResourceCost.objects.filter(resource=resource).latest('created_at')
        except ResourceCost.DoesNotExist:
            logger.warning(f"ResourceCost does not exist for Resource '{resource}' | {cls.__name__}", exc_info=True)
            cost = ResourceCost.objects.create(resource=resource, value=0)

        resource.cost = cost.value
        resource.verified = cost.verified

        return resource

    @classmethod
    def create(cls, resource_name: str, external_id: str, cost_value: float = 0, amount_value: float = 0,
               provider_name: str = None, storage_place=None, user=None):

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
                                                       amount=amount_value,
                                                       storage_place=storage_place)

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
                           f"cost_value={cost_value}, amount_value={amount_value}, provider_name={provider_name} | "
                           f"{cls.__name__}", exc_info=True)
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
                logger.warning(f"Exceptions caught while bulk creating {ex} | {cls.__name__}", exc_info=True)
                continue
        return errors

    @classmethod
    def list(cls):
        try:
            cost_qr = ResourceCost.objects.filter(resource=OuterRef('pk')).order_by('-created_at')
            query = Resource.objects.select_related('provider').annotate(
                cost=Subquery(cost_qr.values('value')[:1]),
                last_change_cost=Subquery(cost_qr.values('created_at')[:1]),
                last_change_amount=Subquery(cost_qr.values('created_at')[:1]),
                verified=Subquery(cost_qr.values('verified')[:1]),
            )
        except DatabaseError as ex:
            logger.error(f"Error while getting resource list: {ex} | {cls.__name__}", exc_info=True)
            raise cls.QueryError()

        return query.order_by('verified')

    @classmethod
    def shortlist(cls):
        query_cost = ResourceCost.objects.filter(resource=OuterRef('pk')).order_by('-created_at')
        query = Resource.objects.select_related('provider').annotate(
            cost=Subquery(query_cost.values('value')[:1])).order_by('name')
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
            logger.error(f"Database error: {ex} | {cls.__name__}", exc_info=True)
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

    @classmethod
    async def send_prime_cost(cls, products):
        products = await products()
        return asyncio.create_task(send_prime_cost(products))


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


bitrix_url = settings.BITRIX_URL + "ajax/tsenaobnov.php "


def session_post(session, products, lnp):
    i = 0
    headers = {'content-type': 'application/json'}
    while i < lnp:
        product = products[i]
        logger.info(f"sent prime cost {product}")
        i += 1
        yield session.post(bitrix_url,
                           json={"ID": str(product["product_id"]), "primeCost": float(product['prime_cost'])},
                           headers=headers)


async def send_prime_cost(products):
    tasks = []
    ln = sync_to_async(len)
    lnp = await ln(products)
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(**settings.BITRIX_AUF_CONF)) as session:
        for sp in session_post(session, products, lnp):
            tasks.append(sp)
        try:
            await asyncio.gather(*tasks)
        except Exception as ex:
            logger.error(f"error while sending products new prime_cost", exc_info=True)

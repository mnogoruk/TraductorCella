import asyncio

import aiohttp
from asgiref.sync import sync_to_async, async_to_sync
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction, DatabaseError
import logging
import pandas as pd
from django.db.models import OuterRef, Subquery, F, Q, Count, Sum

from authentication.models import Operator
from cella.models import File
from specification.models import Specification, SpecificationResource
from utils.function import random_str

from .models import Resource, ResourceProvider, ResourceDelivery

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
    def make_delivery(cls, resource, new_name=None, provider_name=None, cost=0, amount=0, comment=None, time_stamp=None,
                      user=None):
        resource = cls.get(resource)

        if new_name is not None:
            resource.name = new_name

        resource.comment = comment
        provider = ResourceProvider.objects.get_or_create_by_name(provider_name).object()

        resource.provider = provider
        delivery = cls._create_delivery(resource, provider, cost, amount, comment, time_stamp)

        cls.set_cost(resource, cost, user=user, save=True)
        cls.change_amount(resource, amount, user=user, save=True)

        try:
            with transaction.atomic():
                delivery.save()
                resource.save()
        except Exception as ex:
            logger.error(f"make delivery error | {cls.__name__}", exc_info=True)

        return delivery

    @classmethod
    def _create_delivery(cls, resource, provider, cost, amount, comment, time_stamp):
        delivery = ResourceDelivery()
        delivery.set_resource(resource)
        delivery.set_amount(amount)
        delivery.set_provider(provider)
        delivery.set_comment(comment)
        delivery.set_cost(cost)
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
            except Resource.DoesNotExist:
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

        if save:
            resource.save()

        return amount_value

    @classmethod
    def change_amount(cls, resource, delta_amount, user=None, save=True):
        resource = cls.get(resource)

        resource.amount = float(resource.amount) + float(delta_amount)
        if resource.amount < 0:
            logger.warning(f"resources amount < 0 for resources '{resource.id}'")

        if save:
            resource.save()

        return resource.amount

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
        resource.cost = cost_value
        if cost_value < 0:
            logger.warning(f"resources cost < 0 for resources '{resource.id}'")

        if save:
            resource.save()
            query_cost = Resource.objects.filter(id=OuterRef('resource_id'))

            query_res_spec = SpecificationResource.objects.filter(
                specification=OuterRef('pk'),
            ).values('specification_id').annotate(
                total_cost=Sum(Subquery(query_cost.values('cost')) * F('amount')))

            specifications = Specification.objects.filter(res_specs__resource=resource).annotate(
                prime_cost=Subquery(query_res_spec.values('total_cost'))).values('product_id', 'prime_cost')
            specifications = sync_to_async(specifications.all)
            spc = async_to_sync(cls.send_prime_cost)

            spc(specifications)
        return cost_value

    @classmethod
    def expired_count(cls):
        count = Resource.objects.aggregate(
            count=Count('id', filter=Q(amount_limit__gte=F('amount'))))
        return count['count']

    @classmethod
    def update_fields(cls, resource, resource_name=None, external_id=None, provider_name: str = None, user=None):

        resource = cls.get(resource)
        operator = Operator.objects.get_or_create_operator(user)
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

        except DatabaseError:
            logger.warning(f"Update error | {cls.__name__}", exc_info=True)
            raise cls.UpdateError()

        return cls.detail(resource)

    @classmethod
    def detail(cls, resource):

        resource = cls.get(resource)
        resource.last_delivery_date = \
        ResourceDelivery.objects.values('time_stamp').filter(resource=resource).latest('time_stamp')['time_stamp']
        print(resource.last_delivery_date)
        return resource

    @classmethod
    def create(cls, resource_name: str, external_id: str, cost_value: float = 0, amount_value: float = 0,
               provider_name: str = None, storage_place=None, user=None, amount_limit=10.0):

        if cost_value is None:
            cost_value = .0

        if amount_value is None:
            amount_value = .0

        if amount_limit is None:
            amount_limit = 10.0

        if provider_name is not None and provider_name != '':
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
                                                       storage_place=storage_place,
                                                       cost=cost_value,
                                                       amount_limit=amount_limit)

                except IntegrityError as ex:
                    logger.warning(f"Not unique external id '{external_id}'")
                    raise cls.ExternalIdUniqueError(ex)

                operator = Operator.objects.get_or_create_operator(user)

                cost = cls.set_cost(resource, cost_value, operator, True, True)
                amount = cls.set_amount(resource, amount_value, operator)

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
            resource['applicant'] = user
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
            delivery_query = ResourceDelivery.objects.filter(resource=OuterRef('pk')).order_by('-time_stamp')
            query = Resource.objects.select_related('provider').annotate(
                last_delivery_date=Subquery(delivery_query.values('time_stamp')[:1]),
                comment=Subquery(delivery_query.values('comment')[:1]),
            )
        except DatabaseError as ex:
            logger.error(f"Error while getting resource list: {ex} | {cls.__name__}", exc_info=True)
            raise cls.QueryError()

        return query

    @classmethod
    def shortlist(cls):

        query = Resource.objects.select_related('provider')
        return query

    @classmethod
    def providers(cls):
        return ResourceProvider.objects.all()

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
        operator = await (sync_to_async(Operator.objects.get_or_create_operator)(operator_id))
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
                resource = Resource(**obj)
                if pd.isnull(row['Цена']):
                    cost_value = 0
                else:
                    cost_value = row['Цена']
                await sync_to_async(Resources.set_cost)(resource, cost_value, operator, verified=True, save=False)
                await sync_to_async(Resources.set_amount)(resource, amount_value, operator, save=False)

                resources.append(resource)

        group = asyncio.gather((sync_to_async(Resource.objects.bulk_create)(resources)))
        await group
    except Exception as ex:
        logger.warning(f"Error while creating resources from excel", exc_info=True)
        raise Resources.CreateError()


bitrix_url = settings.BITRIX_URL + "ajax/tsenaobnov.php"


def session_post(session, products, lnp):
    i = 0
    headers = {'content-type': 'application/json'}
    while i < lnp:
        product = products[i]
        logger.info(f"sent prime cost {product}")
        i += 1
        yield session.post(bitrix_url, json={"ID": product["product_id"], "primeCost": product['prime_cost']},
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

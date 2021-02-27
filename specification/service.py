from typing import List, Dict
from xml.dom import minidom

import aiohttp
import asyncio

from asgiref.sync import async_to_sync, sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction, DatabaseError
import logging

from django.db.models import OuterRef, Subquery, Exists, Sum, Min, IntegerField, F, Count, Q
from django.db.models.functions import Cast

from cella.models import File
from cella.service import Operators
from resources.models import ResourceCost, Resource, ResourceAction
from resources.service import Resources
from utils.function import resource_amounts
from .models import Specification, SpecificationAction, SpecificationCategory, SpecificationResource
from django.conf import settings

logger = logging.getLogger(__name__)


class Specifications:
    class CreateError(Exception):
        pass

    class EditError(Exception):
        pass

    class DoesNotExist(ObjectDoesNotExist):
        pass

    class UniqueField(Exception):
        pass

    class CantBuildSet(Exception):
        pass

    class QueryError(Exception):
        pass

    @classmethod
    def get(cls, specification, related=None, prefetched=None):
        if related is None:
            related = []
        if prefetched is None:
            prefetched = []
        if not isinstance(specification, Specification):
            try:
                return Specification.objects.select_related(*related).prefetch_related(*prefetched).get(
                    id=specification, is_active=True)
            except DatabaseError:
                logger.warning(f"Specification does not exist. Id: '{specification}' | {cls.__name__}", exc_in=True)
                raise cls.DoesNotExist()
        else:
            return specification

    @classmethod
    def shortlist(cls):
        return Specification.objects.all()

    @classmethod
    def get_category(cls, category):
        if not isinstance(category, SpecificationCategory):
            try:
                return SpecificationCategory.objects.get(id=category)
            except IntegrityError:
                logger.warning(f"Category does not exist. Id: '{category}' | {cls.__name__}", exc_info=True)
                raise cls.DoesNotExist()
        else:
            return category

    @classmethod
    def verify_price_count(cls):
        count = Specification.objects.aggregate(count=Count('id', filter=Q(verified=False)))
        return count['count']

    @classmethod
    def set_coefficient(cls, specification, coefficient: float, user=None, save=True):
        specification = cls.get(specification)
        specification.coefficient = coefficient
        if coefficient < 0:
            logger.warning(f"specification coefficient < 0 for specification '{specification.id}' | {cls.__name__}")

        action = SpecificationAction(
            specification=specification,
            action_type=SpecificationAction.ActionType.SET_COEFFICIENT,
            operator=Operators.get_operator(user),
            value=str(coefficient)
        )
        if save:
            specification.save()
            action.save()

        return coefficient, action

    @classmethod
    def set_price(cls, specification, price: float, user=None, save=True, send=False):
        specification = cls.get(specification)
        specification.price = price
        specification.verified = True

        if price < 0:
            logger.warning(f"specification price < 0 for specification '{specification.id}' | {cls.__name__}")

        action = SpecificationAction(
            specification=specification,
            action_type=SpecificationAction.ActionType.SET_PRICE,
            operator=Operators.get_operator(user),
            value=str(price)
        )

        if save:
            specification.save()
            action.save()

        if send:
            s_p = async_to_sync(cls.send_price)
            s_p(specification.product_id, price)
        return price, action

    @classmethod
    def set_amount(cls, specification, amount: float, user=None, save=True):
        specification = cls.get(specification)
        specification.amount = amount
        if amount < 0:
            logger.warning(f"specification amount < 0 for specification '{specification.id}' | {cls.__name__}")

        action = SpecificationAction(
            specification=specification,
            action_type=SpecificationAction.ActionType.SET_AMOUNT,
            operator=Operators.get_operator(user),
            value=str(amount)
        )

        if save:
            specification.save()
            action.save()

        return amount, action

    @classmethod
    def set_category(cls, specification, category, user=None, save=True):
        category = cls.get_category(category)
        specification = cls.get(specification)
        specification.category = category

        action = SpecificationAction(
            specification=specification,
            action_type=SpecificationAction.ActionType.SET_CATEGORY,
            operator=Operators.get_operator(user),
            value=category.name
        )

        if save:
            specification.save()
            action.save()

        return category, action

    @classmethod
    def set_category_many(cls, ids: List, category, user):
        category = cls.get_category(category)
        Specification.objects.filter(id__in=ids).update(category=category, coefficient=category.coefficient)
        actions = []
        for s_id in ids:
            actions.append(
                SpecificationAction(
                    specification_id=s_id,
                    action_type=SpecificationAction.ActionType.SET_CATEGORY,
                    operator=Operators.get_operator(user),
                    value=category.name
                )
            )
        try:
            SpecificationAction.objects.bulk_create(actions)
        except DatabaseError:
            logger.error(f"Set category Error, ids={ids}, category={category} | {cls.__name__}", exc_info=True)
            raise cls.CreateError()
        return category, actions

    @classmethod
    def detail(cls, specification):
        try:
            specification = cls.get(specification, prefetched=['res_specs', 'res_specs__resource'])
            query_res_spec = SpecificationResource.objects.filter(specification=specification, resource=OuterRef('pk'))
            cost_qr = ResourceCost.objects.filter(resource=OuterRef('pk')).order_by('-time_stamp')
            resources = Resource.objects.annotate(
                cost=Subquery(cost_qr.values('value')[:1]),
                res_spec_ex=Exists(query_res_spec.values('id')),
                needed_amount=Subquery(query_res_spec.values('amount')[:1]),
                verified=Subquery(cost_qr.values('verified')[:1])).filter(res_spec_ex=True)
            reses = []
            prime_cost = 0
            for resource in resources:
                reses.append({'resource': resource, 'amount': resource.needed_amount})
                prime_cost += resource.cost * resource.needed_amount

            specification.resources = reses
            specification.prime_cost = prime_cost
            specification.available_to_assemble = cls.assemble_info(specification)
        except DatabaseError as ex:
            logger.error(f"Error while detail. | {cls.__name__}", exc_info=True)
            raise cls.QueryError()
        return specification

    @classmethod
    def list(cls):
        try:
            query_cost = ResourceCost.objects.filter(resource_id=OuterRef('resource_id')).order_by('-time_stamp')
            query_res_spec = SpecificationResource.objects.filter(specification=OuterRef('pk')).values(
                'specification_id').annotate(
                total_cost=Sum(Subquery(query_cost.values('value')[:1]) * F('amount')),
                verified=Min(Cast(query_cost.values('verified')[:1], output_field=IntegerField())))
            specifications = Specification.objects.select_related('category').annotate(
                prime_cost=Subquery(query_res_spec.values('total_cost')))
        except DatabaseError:
            logger.warning(f"list query error. | {cls.__name__}", exc_info=True)
            raise cls.QueryError()
        return specifications

    @classmethod
    def categories(cls):
        try:
            return SpecificationCategory.objects.all()
        except DatabaseError:
            raise cls.QueryError()

    @classmethod
    def create(cls, name: str, product_id: str, price: float = None, coefficient: float = None,
               resources: List[Dict[str, str]] = None, category_name: str = None, amount: int = None,
               user=None):

        try:
            with transaction.atomic():

                operator = Operators.get_operator(user)

                if Specification.objects.filter(product_id=product_id, is_active=True).exists():
                    s = Specification.objects.filter(product_id=product_id).get(is_active=True)
                    s.is_active = False
                    s.save()

                    SpecificationAction.objects.create(specification=s,
                                                       action_type=SpecificationAction.ActionType.DEACTIVATE,
                                                       operator=operator)

                if price is None:
                    price = 0

                if amount is None:
                    amount = 0

                specification = Specification.objects.create(
                    name=name,
                    product_id=product_id,
                    is_active=True)

                actions = []

                if category_name is not None and category_name != "":
                    category = SpecificationCategory.objects.get_or_create(name=category_name)[0]
                    category, category_action = cls.set_category(specification, category, operator, False)
                    actions.append(category_action)
                else:
                    category = None

                if coefficient is not None:
                    _, coefficient_action = cls.set_coefficient(specification, coefficient, operator, False)
                    actions.append(coefficient_action)

                elif category is not None and category.coefficient is not None:
                    _, coefficient_action = cls.set_coefficient(specification, category.coefficient, operator,
                                                                False)
                    actions.append(coefficient_action)

                _, amount_action = cls.set_amount(specification, amount, operator, False)
                actions.append(amount_action)

                _, price_action = cls.set_price(specification, price, operator, False)
                actions.append(price_action)

                if resources is not None and len(resources) != 0:
                    resource_objects = Resource.objects.prefetch_related('resourcecost_set').filter(
                        id__in=map(lambda x: x['id'], resources))
                    res_specs_dict = resource_amounts(resource_objects, resources)
                    for resource in res_specs_dict:
                        res = resource['resource']
                        res.cost = res.resourcecost_set.last().value

                        SpecificationResource.objects.create(
                            resource=res,
                            amount=resource['amount'],
                            specification=specification
                        )

                        specification.resources = res_specs_dict

                SpecificationAction.objects.create(
                    specification=specification,
                    action_type=SpecificationAction.ActionType.CREATE,
                    operator=operator
                )

                specification.save()
                SpecificationAction.objects.bulk_create(actions)

        except DatabaseError as ex:
            logger.warning(f"Create error specification_name={name}, product_id={product_id}, "
                           f"price={price}, amount={amount}, category_name={category_name}  | {cls.__name__}",
                           exc_info=True)
            raise cls.CreateError(ex)

        return specification

    @classmethod
    def edit(cls, specification, name: str = None, product_id: str = None, price: float = None,
             coefficient: float = None, resource_to_add: List[Dict[str, str]] = None,
             resource_to_delete: List[str] = None, category_name: str = None, storage_amount: int = None, user=None):
        try:
            with transaction.atomic():

                specification = cls.get(specification)
                operator = Operators.get_operator(user)

                value_data = []

                # Model field block

                # ----------
                if name is not None:
                    specification.name = name
                    value_data.append(f"name={name}")

                if product_id is not None:
                    specification.product_id = product_id
                    value_data.append(f"product_id={product_id}")

                SpecificationAction.objects.create(specification=specification,
                                                   action_type=SpecificationAction.ActionType.UPDATE_FIELDS,
                                                   operator=operator)
                # -----------

                # Setting category, price, coefficient, amount block

                # -----------
                actions = []
                if category_name is not None:
                    if category_name != "":
                        category = SpecificationCategory.objects.get_or_create(name=category_name)[0]
                        category, category_action = cls.set_category(specification, category, operator, False)
                        actions.append(category_action)
                        value_data.append(f"category={category_name}")

                        if category.coefficient is not None:
                            coefficient, coefficient_action = cls.set_coefficient(specification, category.coefficient,
                                                                                  operator, False)
                    else:
                        specification.category = None

                if price is not None:
                    _, price_action = cls.set_price(specification, price, operator, False)
                    actions.append(price_action)

                if coefficient is not None:
                    _, coefficient_action = cls.set_coefficient(specification, coefficient, operator, False)
                    actions.append(coefficient_action)

                if storage_amount is not None:
                    _, amount_action = cls.set_amount(specification, storage_amount, operator, False)
                    actions.append(amount_action)
                # -----------

                # Resource block

                # -----------
                if resource_to_delete is not None and len(resource_to_delete) != 0:
                    SpecificationResource.objects.filter(
                        specification=specification,
                        resource_id__in=resource_to_delete
                    ).delete()

                if resource_to_add is not None and len(resource_to_add) != 0:
                    res_specs = []
                    _resources = []
                    for resource in resource_to_add:
                        res = Resource.objects.get(id=resource['id'])
                        res.cost = ResourceCost.objects.filter(resource=res).latest('time_stamp').value
                        res_specs.append(
                            SpecificationResource.objects.create(
                                resource_id=resource['id'],
                                amount=resource['amount'],
                                specification=specification
                            )
                        )
                        _resources.append({'resources': res, 'amount': resource['amount']})

                try:
                    res_specs = SpecificationResource.objects.select_related('resource').filter(
                        specification=specification)
                    for res_spec in res_specs:
                        res = res_spec.resource
                        res_cost = ResourceCost.objects.filter(resource=res).latest('time_stamp')
                        res.cost = res_cost.value

                    specification.resources = res_specs

                except SpecificationResource.DoesNotExist:
                    raise Resources.ResourceDoesNotExist()
        except DatabaseError as ex:
            logger.error(f"Specification edit error. | {cls.__name__}", exc_info=True)
            raise cls.EditError()

        return specification

    @classmethod
    def assemble_info(cls, specification):
        specification = cls.get(specification, prefetched=['res_specs', 'res_specs__resource'])

        min_amount = None
        try:
            for res_spec in specification.res_specs.all():
                if min_amount is None:
                    min_amount = int(res_spec.resource.amount / res_spec.amount)
                min_amount = min(min_amount, int(res_spec.resource.amount / res_spec.amount))
        except ZeroDivisionError:
            logger.warning(f"Zero division error while finding assemble_info.  | {cls.__name__}", exc_info=True)
        return min_amount

    @classmethod
    def delete(cls, specification, user):
        specification = cls.get(specification)
        specification.delete()

    @classmethod
    def bulk_delete(cls, ids, user):
        Specification.objects.filter(id__in=ids).delete()

    @classmethod
    def build_set(cls, specification, amount, from_resources=False, user=None):
        try:
            with transaction.atomic():
                if not isinstance(specification, Specification):
                    if from_resources:
                        specification = Specification.objects.prefetch_related(
                            'res_specs',
                            'res_specs__resource'
                        ).get(id=specification)
                    else:
                        specification = Specification.objects.get(id=specification)

                resources = []
                actions = []

                operator = Operators.get_operator(user)
                if from_resources:
                    for res_spec in specification.res_specs.all():
                        resource = res_spec.resource

                        if resource.amount < res_spec.amount * amount:
                            raise cls.CantBuildSet()

                        else:
                            _, action = Resources.change_amount(resource, -res_spec.amount * amount, operator,
                                                                False)
                            resources.append(resource)
                            actions.append(action)

                    Resource.objects.bulk_update(resources, fields=['amount'])
                    ResourceAction.objects.bulk_create(actions)

                    value = 'from_resources=True'
                else:
                    value = 'from_resources=False'

                SpecificationAction.objects.create(
                    specification=specification,
                    action_type=SpecificationAction.ActionType.BUILD_SET,
                    value=value,
                    operator=Operators.get_operator(user)
                )
                specification.amount += amount
                specification.save()
        except DatabaseError as ex:
            logger.error(f"Error while building set. | {cls.__name__}", exc_info=True)
            raise cls.CantBuildSet()

    @classmethod
    async def send_price(cls, product_id, price):
        return asyncio.create_task(send_price(product_id, price))

    @classmethod
    async def create_from_xml(cls, file_instance_id, operator_id):
        print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        asyncio.create_task(upload_specifications(file_instance_id, operator_id))


bitrix_url = settings.BITRIX_URL + "cella/test/"


async def send_price(product_id, price):
    async with aiohttp.ClientSession() as session:
        await session.post(bitrix_url, data={"ID": product_id, "price": price})


async def upload_specifications(file_instance_id, operator_id=None):
    try:
        file = await sync_to_async(File.objects.get)(id=file_instance_id)
        tree = minidom.parse(file.file)
        offers = tree.getElementsByTagName('offer')
        specifications = []
        for offer in offers:
            obj = dict(
                name=str(offer.getElementsByTagName('shop-sku')[0].childNodes[0].nodeValue),
                product_id=str(offer.getElementsByTagName('market-sku')[0].childNodes[0].nodeValue),
                price=float(offer.getElementsByTagName('price')[0].childNodes[0].nodeValue)
            )
            specification = Specification(**obj)
            specifications.append(specification)
        await sync_to_async(Specification.objects.bulk_create)(specifications)
    except Exception:
        logger.error("file read exception", exc_info=True)

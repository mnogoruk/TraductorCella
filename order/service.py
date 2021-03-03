import asyncio
from typing import List, Dict
import logging

import aiohttp
from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction, DatabaseError
from django.db.models import Count, Q

from cella.service import Operators
from order.models import Order, OrderSource, OrderSpecification, OrderAction
from resources.service import Resources
from specification.models import Specification
from specification.service import Specifications
from utils.function import product_amounts

logger = logging.getLogger(__name__)


class Orders:
    class AssembleError(Exception):
        pass

    class DoesNotExist(ObjectDoesNotExist):
        pass

    class CreateError(Exception):
        pass

    class EditError(Exception):
        pass

    class QueryError(Exception):
        pass

    class ActionError(Exception):
        pass

    @classmethod
    def get(cls, order):
        if not isinstance(order, Order):
            try:
                return Order.objects.select_related('source').get(id=order)
            except IntegrityError:
                logger.warning(f"Order does not exist. Id: '{order}' | {cls.__name__}", exc_info=True)
                raise cls.DoesNotExist()
        else:
            return order

    @classmethod
    def sources(cls):
        return OrderSource.objects.all()

    @classmethod
    def list(cls):
        orders = Order.objects.prefetch_related(
            'order_specification',
            'order_specification__specification',
            'order_specification__specification__res_specs',
            'order_specification__specification__res_specs__resource'

        ).exclude(
            status__in=[
                Order.OrderStatus.ARCHIVED
            ]
        ).order_by('status')

        return orders

    @classmethod
    def add_assembling_info(cls, orders):
        for order in orders:
            if order.status in [Order.OrderStatus.INACTIVE]:
                m, n = cls.assembling_info(order)
            else:
                m = 0
                n = 0
            order.missing_resources = n
            order.missing_specifications = m
        return orders

    @classmethod
    def assembling_info(cls, order):
        if not isinstance(order, Order):
            order = Order.objects.prefetch_related(
                'order_specification',
                'order_specification__specification',
                'order_specification__specification__res_specs',
                'order_specification__specification__res_specs__resource'
            ).get(id=order)

        resources = {}
        miss_resources = set()
        miss_specification = set()
        try:
            for order_spec in order.order_specification.all():
                specification = order_spec.specification

                for res_spec in specification.res_specs.all():
                    resource = res_spec.resource

                    if resource.id not in resources:
                        resources[resource.id] = [
                            resource.amount,
                            res_spec.amount * (order_spec.amount - specification.amount)
                        ]

                    else:
                        resources[resource.id][1] += res_spec.amount * (order_spec.amount - specification.amount)

                    if resources[resource.id][0] < resources[resource.id][1]:
                        miss_resources.add(resource.id)
                        miss_specification.add(specification.id)
        except Exception:
            logger.warning(f"Assemble info error. order: {order} | {cls.__name__}", exc_info=True)
            raise cls.AssembleError()
        return miss_specification, miss_resources

    @classmethod
    def detail(cls, order):
        order = Order.objects.prefetch_related(
            'order_specification',
            'order_specification__specification',
            'order_specification__specification__res_specs',
            'order_specification__specification__res_specs__resource',
            'order_specification__specification__res_specs__resource__resourcecost_set'
        ).get(id=order)
        m, n = cls.assembling_info(order)
        order.missing_resources = n
        order.missing_specifications = m

        for oder_spec in order.order_specification.all():
            spec = oder_spec.specification
            for res_spec in spec.res_specs.all():
                resource = res_spec.resource
                resource.cost = resource.resourcecost_set.last().value
        return order

    @classmethod
    def assemble_specification(cls, order, specification, user=None):
        order = cls.get(order)
        specification = Specifications.get(specification)

        if not (order.status == Order.OrderStatus.ACTIVE or order.status == Order.OrderStatus.ASSEMBLING):
            logger.warning(
                f"Can't assemble specification. Order status: {order.status}. Order: {order} | {cls.__name__}")
            raise cls.AssembleError()

        operator = Operators.get_operator(user)
        try:
            OrderSpecification.objects.filter(specification=specification, order=order).update(assembled=True)

            OrderAction.objects.create(
                order=order,
                action_type=OrderAction.ActionType.ASSEMBLING_SPECIFICATION,
                operator=operator
            )

            if order.status == Order.OrderStatus.ACTIVE:
                cls._assembling(order, operator)

            if not OrderSpecification.objects.filter(order=order, assembled=False).exists():
                cls._ready(order, operator)
            order.save()
        except DatabaseError:
            logger.warning(f"Assembling specification error. Order: {order} | {cls.__name__}", exc_info=True)
            raise cls.AssembleError()

    @classmethod
    def disassemble_specification(cls, order, specification, user=None):
        order = cls.get(order)
        specification = Specifications.get(specification)

        if not (order.status == Order.OrderStatus.READY or order.status == Order.OrderStatus.ASSEMBLING):
            logger.warning(
                f"Can't disassemble specification. Order status: {order.status}. Order: {order} | {cls.__name__}")
            raise cls.AssembleError()

        try:

            operator = Operators.get_operator(user)

            OrderSpecification.objects.filter(specification=specification, order=order).update(assembled=False)

            OrderAction.objects.create(
                order=order,
                action_type=OrderAction.ActionType.DISASSEMBLING_SPECIFICATION,
                operator=operator
            )

            if order.status == Order.OrderStatus.READY:
                cls._assembling(order, operator)

            if not OrderSpecification.objects.filter(order=order, assembled=True).exists():
                cls._activate(order, operator)

            order.save()
        except DatabaseError:
            logger.warning(f"Disassembling specification error | {cls.__name__}", exc_in=True)
            raise cls.AssembleError()

    @classmethod
    def delete(cls, order, user):
        order = cls.get(order)
        order.delete()

    @classmethod
    def bulk_delete(cls, ids, user):
        Order.objects.filter(id__in=ids).delete()

    @classmethod
    def confirm(cls, order, user):
        try:
            order = cls.get(order)
            if not order.status == Order.OrderStatus.READY:
                logger.warning(f"Cant confirm order with status {order.status}. Order: {order} | {cls.__name__}")
                raise cls.ActionError()
            cls._confirm(order, Operators.get_operator(user))
            order.save()

            ch_s = async_to_sync(cls.change_status)
            ch_s(order.external_id, 'DF')
        except Exception:
            logger.warning("")
            raise cls.ActionError()

    @classmethod
    def cancel(cls, order, user):
        order = cls.get(order)
        if order.status in [Order.OrderStatus.READY, Order.OrderStatus.ASSEMBLING, Order.OrderStatus.ACTIVE]:
            cls.deactivate(order, user)
            cls._cancel(order, user)
        elif order.status in [Order.OrderStatus.CANCELED, Order.OrderStatus.ARCHIVED, Order.OrderStatus.CONFIRMED]:
            logger.warning(f"Can't cancel order with status {order.status}. Order: {order} | {cls.__name__}")
            raise cls.ActionError()
        elif order.status == Order.OrderStatus.INACTIVE:
            cls._cancel(order, user)
        else:
            logger.warning(f"Can't cancel order. Unexpected status {order.status}. Order: {order} | {cls.__name__}")

    @classmethod
    def activate(cls, order, user):
        order = Order.objects.prefetch_related(
            'order_specification',
            'order_specification__specification',
            'order_specification__specification__res_specs',
            'order_specification__specification__res_specs__resource',
        ).get(id=order)

        if not order.status == Order.OrderStatus.INACTIVE:
            logger.warning(f"Can't activate order with status {order.status}. Order: {order} | {cls.__name__}")
            raise cls.ActionError()

        order_specs = order.order_specification
        operator = Operators.get_operator(user)

        try:
            with transaction.atomic():
                for order_spec in order_specs.all():
                    specification = order_spec.specification
                    res_specs = specification.res_specs

                    if specification.amount > order_spec.amount:
                        Specifications.set_amount(specification, specification.amount - order_spec.amount, operator)
                        continue

                    else:
                        storage_amount = specification.amount
                        Specifications.set_amount(specification, 0, operator, False)

                    for res_spec in res_specs.all():
                        resource = res_spec.resource
                        amount = resource.amount
                        if amount >= res_spec.amount * (order_spec.amount - storage_amount):
                            Resources.change_amount(resource,
                                                    - (res_spec.amount * (order_spec.amount - storage_amount)),
                                                    operator)

                        else:
                            logger.warning(f"Can`t assemble Order. Not enough resources")
                            raise cls.ActionError(f"resource {resource.name}, amount {amount}")

                    specification.save()

                cls._activate(order, Operators.get_operator(user))
                order.save()
            ch_s = async_to_sync(cls.change_status)
            ch_s(order.external_id, 'S')
        except DatabaseError:
            logger.warning(f"Activation error. Order: {order} | {cls.__name__}", exc_info=True)
            raise cls.ActionError()

    @classmethod
    def deactivate(cls, order, user):
        order = cls.get(order)
        operator = Operators.get_operator(user)

        if order.status not in [Order.OrderStatus.ACTIVE, Order.OrderStatus.ASSEMBLING, Order.OrderStatus.READY]:
            logger.warning(f"Can't deactivate order with status {order.status}. Order: {order} | {cls.__name__}",
                           exc_info=True)
            raise cls.ActionError()

        order_specs = order.order_specification
        try:
            for order_spec in order_specs.all():
                specification = order_spec.specification
                res_specs = specification.res_specs
                order_spec.assembled = False
                order_spec.save()

                for res_spec in res_specs.all():
                    resource = res_spec.resource
                    Resources.change_amount(resource, res_spec.amount * order_spec.amount, operator)

            cls._deactivate(order, Operators.get_operator(user))
            order.save()

            ch_s = async_to_sync(cls.change_status)
            ch_s(order.external_id, 'P')
        except DatabaseError:
            logger.warning(f"Can't deactivate order. Order: {order} | {cls.__name__}", exc_info=True)
            raise cls.ActionError()

    @classmethod
    def create(cls, external_id, source: str = None, products: List[Dict[str, str]] = None, user=None):
        try:
            with transaction.atomic():
                if source is not None and source != '':
                    source = OrderSource.objects.get_or_create(name=source)[0]
                else:
                    source = None

                order = Order.objects.create(
                    external_id=external_id,
                    status=Order.OrderStatus.INACTIVE,
                    source=source)

                OrderAction.objects.create(
                    order=order,
                    action_type=OrderAction.ActionType.CREATE,
                    operator=Operators.get_operator(user)
                )

                if products is not None and len(products) != 0:
                    order_specs = []
                    specifications_objects = []
                    for product in products:
                        specification = Specification.objects.get_or_create(product_id=product['product_id'],
                                                                            is_active=True)[0]
                        specifications_objects.append(specification)
                    # specifications_objects = Specification.objects.filter(
                    #     product_id__in=map(lambda x: x['product_id'], products), is_active=True)
                    order_specs_dict = product_amounts(specifications_objects, products)

                    for product in order_specs_dict:
                        order_spec = OrderSpecification(
                            order=order,
                            specification=product['specification'],
                            amount=product['amount']
                        )

                        order_specs.append(order_spec)

                    OrderSpecification.objects.bulk_create(order_specs)
                    order.specifications = order_specs_dict

        except DatabaseError as ex:
            logger.warning(f"Create error | {cls.__name__}", exc_info=True)
            raise cls.CreateError(ex)
        return order

    @classmethod
    def status_count(cls):
        count = Order.objects.aggregate(
            inactive=Count('id', filter=Q(status=Order.OrderStatus.INACTIVE)),
            active=Count('id', filter=Q(status=Order.OrderStatus.ACTIVE)),
            assembling=Count('id', filter=Q(status=Order.OrderStatus.ASSEMBLING)),
            ready=Count('id', filter=Q(status=Order.OrderStatus.READY)),
        )
        return count

    @classmethod
    def _activate(cls, order, operator):
        order.status = Order.OrderStatus.ACTIVE
        OrderAction.objects.create(
            order=order,
            action_type=OrderAction.ActionType.ACTIVATE,
            operator=operator
        )

    @classmethod
    def _deactivate(cls, order, operator):
        order.status = Order.OrderStatus.INACTIVE
        OrderAction.objects.create(
            order=order,
            action_type=OrderAction.ActionType.DEACTIVATE,
            operator=operator
        )

    @classmethod
    def _assembling(cls, order, operator):
        order.status = Order.OrderStatus.ASSEMBLING
        OrderAction.objects.create(
            order=order,
            action_type=OrderAction.ActionType.ASSEMBLING,
            operator=operator
        )

    @classmethod
    def _ready(cls, order, operator):
        order.status = Order.OrderStatus.READY
        OrderAction.objects.create(
            order=order,
            action_type=OrderAction.ActionType.PREPARING,
            operator=operator
        )

    @classmethod
    def _confirm(cls, order, operator):
        order.status = Order.OrderStatus.CONFIRMED
        OrderAction.objects.create(
            order=order,
            action_type=OrderAction.ActionType.CONFIRM,
            operator=operator
        )

    @classmethod
    def _archive(cls, order, operator):
        order.status = Order.OrderStatus.ARCHIVED
        OrderAction.objects.create(
            order=order,
            action_type=OrderAction.ActionType.ARCHIVATION,
            operator=operator
        )

    @classmethod
    def _cancel(cls, order, operator):
        order.status = Order.OrderStatus.CANCELED
        OrderAction.objects.create(
            oreder=order,
            action_type=OrderAction.ActionType.CANCEL,
            operator=operator,
        )

    @classmethod
    async def change_status(cls, order_id, status):
        return asyncio.create_task(change_status(order_id, status))


bitrix_url = settings.BITRIX_URL + "ajax/smenastatusa.php"


async def change_status(order_id, status):

    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(**settings.BITRIX_AUF_CONF)) as session:
        logger.info(f"send changed status. id: {order_id}, status: {status}")
        headers = {'content-type': 'application/json'}
        try:
            await session.post(bitrix_url, json={"ID": order_id, "status": status}, headers=headers)
        except Exception as ex:
            logger.error("Error while posting new status", exc_info=True)


import asyncio
from typing import List, Dict
import logging

import aiohttp
from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction, DatabaseError
from django.db.models import Count, Q

from order.models import Order, OrderSource, OrderSpecification
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
    def get_by_external_id(cls, external_id):
        return Order.objects.get(external_id=external_id)

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
            'order_specifications',
            'order_specifications__specification',
            'order_specifications__specification__res_specs',
            'order_specifications__specification__res_specs__resource'

        ).exclude(
            status__in=[
                Order.OrderStatus.ARCHIVED
            ]
        ).order_by('status')
        return orders

    @classmethod
    def add_assembling_info(cls, orders):
        for order in orders:
            m, n = cls.assembling_info(order)
            order.missing_resources = n
            order.missing_specifications = m
        return orders

    @classmethod
    def assembling_info(cls, order):
        if not isinstance(order, Order):
            order = Order.objects.prefetch_related(
                'order_specifications',
                'order_specifications__specification',
                'order_specifications__specification__res_specs',
                'order_specifications__specification__res_specs__resource'
            ).get(id=order)

        resources = {}
        miss_resources = set()
        miss_specification = set()
        try:
            for order_spec in order.order_specifications.all():
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
            'order_specifications',
            'order_specifications__specification',
            'order_specifications__specification__res_specs',
            'order_specifications__specification__res_specs__resource',
        ).get(id=order)
        if order.status in [Order.OrderStatus.INACTIVE]:
            m, n = cls.assembling_info(order)
        else:
            m = []
            n = []
        order.missing_resources = n
        order.missing_specifications = m
        return order

    @classmethod
    def delete(cls, order, user=None):
        order = cls.get(order)
        order.delete()

    @classmethod
    def bulk_delete(cls, ids, user=None):
        Order.objects.filter(id__in=ids).delete()

    @classmethod
    def confirm(cls, order, user=None):
        try:
            with transaction.atomic():
                order = cls.get(order)
                for order_specification in order.order_specifications.all():
                    specification = order_specification.specification
                    if specification.amount >= order_specification.amount:
                        specification.amount -= order_specification.amount
                    else:
                        missing_amount = order_specification.amount - specification.amount
                        specification.amount = 0
                        for specification_resource in specification.res_specs.all():
                            resource = specification_resource.resource
                            resource.amount -= specification_resource.amount * missing_amount
                            resource.save()
                    Specifications.notify_new_amount(specification)
                    specification.save()
                order.confirm()
                order.save()
        except Exception:
            logger.error(f"Error while confirming order: {order} | {cls.__name__}", exc_info=True)
            raise cls.ActionError(f"Error while confirming order: {order} | {cls.__name__}")

    @classmethod
    def cancel(cls, order, user=None):
        order.cancel()
        order.save()

    @classmethod
    def archive(cls, order, user=None):
        order.archive()
        order.save()

    @classmethod
    def notify_new_status(cls, order):
        request_body = cls.form_request_body_for_changed_status(order)
        async_to_sync(send_status)(request_body)

    @classmethod
    def change(cls, external_id, source: str = None, products: List[Dict[str, str]] = None, user=None):
        try:
            with transaction.atomic():
                order = Order.objects.get(external_id=external_id)
                if source is None:
                    source = order.source
                order.delete()
                cls.create(external_id, source, products, user)

        except DatabaseError as ex:
            logger.warning(f"Change error | {cls.__name__}", exc_info=True)
            raise cls.EditError(ex)
        return order

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

                if products is not None and len(products) != 0:
                    order_specs = []
                    specifications_objects = []
                    for product in products:
                        specification = Specification.objects.get_or_create(product_id=product['product_id'],
                                                                            is_active=True)[0]
                        specifications_objects.append(specification)
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
            canceld=Count('id', filter=Q(status=Order.OrderStatus.CANCELED)),
            confirmed=Count('id', filter=Q(status=Order.OrderStatus.CONFIRMED)),
        )
        return count

    @classmethod
    def form_request_body_for_changed_status(cls, order):
        body = {"ID": order.external_id}
        if order.canceled():
            body['cancel'] = True
        elif order.confirmed():
            body['ship'] = True
        else:
            raise ValueError(f"Wrong status for forming request body. Status: {order.status}")
        return body

    @classmethod
    async def change_status(cls, body):
        return asyncio.create_task(send_status(body))


bitrix_url = settings.BITRIX_URL + "ajax/smenastatusa.php"


async def send_status(body: dict):
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(**settings.BITRIX_AUF_CONF)) as session:
        headers = {'content-type': 'application/json'}
        try:
            await session.post(bitrix_url, json=body, headers=headers)
        except Exception as ex:
            logger.error("Error while posting new status", exc_info=True)

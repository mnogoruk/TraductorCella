from typing import List, Dict
from rest_framework.exceptions import APIException
from django.utils.translation import gettext_lazy as _

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max, Q, Subquery, OuterRef, Exists, Sum, F, ExpressionWrapper, Min, IntegerField, \
    BooleanField
from django.db.models.functions import Cast

from .models import (Operator,
                     ResourceProvider,
                     Resource,
                     ResourceCost,
                     ResourceAmount,
                     ResourceAction,
                     Specification,
                     SpecificationAction,
                     SpecificationPrice,
                     SpecificationCategory,
                     SpecificationCoefficient,
                     SpecificationAmount,
                     ResourceSpecification,
                     Order,
                     OrderSpecification,
                     OrderAction)
from django.db import IntegrityError, transaction, DatabaseError


class Operators:

    @classmethod
    def get_operator_by_user(cls, user):
        if user is None:
            operator = Operator.get_system_operator()
        elif user.is_anonymous:
            operator = Operator.get_anonymous_operator()
        else:
            operator = Operator.get_user_operator(user)
        return operator


class Resources:
    class ResourceDoesNotExist(ObjectDoesNotExist):
        pass

    class UniqueField(APIException):
        status_code = 400
        default_detail = _('Не уникальное значение')
        default_code = 'bad_request'

    @classmethod
    def detail(cls, r_id):

        resource = Resource.objects.select_related('provider').get(id=r_id)
        cost = ResourceCost.objects.defer('value').filter(resource_id=r_id).latest('time_stamp')
        amount = ResourceAmount.objects.defer('value').filter(resource_id=r_id).latest('time_stamp')

        resource.cost = cost.value
        resource.amount = amount.value
        resource.cost_time_stamp = cost.time_stamp
        resource.amount_time_stamp = amount.time_stamp
        resource.verified = cost.verified

        return resource

    @classmethod
    def create(cls,
               resource_name: str,
               external_id: str,
               cost_value: float = 0,
               amount_value: float = 0,
               provider_name: str = None,
               user=None):

        if cost_value is None:
            cost_value = .0
        if amount_value is None:
            amount_value = .0

        if provider_name is not None:
            provider = ResourceProvider.objects.get_or_create(name=provider_name)[0]
        else:
            provider = None
        try:
            resource = Resource.objects.create(name=resource_name,
                                               external_id=external_id,
                                               provider=provider)
        except IntegrityError:
            raise cls.UniqueField()

        cost = ResourceCost.objects.create(resource=resource,
                                           value=cost_value,
                                           verified=True)
        amount = ResourceAmount.objects.create(resource=resource,
                                               value=amount_value)

        operator = Operators.get_operator_by_user(user)

        ResourceAction(
            resource=resource,
            action_type=ResourceAction.ActionType.CREATE,
            message=ResourceAction.ActionType.CREATE,
            operator=operator
        ).save()

        actions = [
            ResourceAction(
                resource=resource,
                action_type=ResourceAction.ActionType.SET_COST,
                message=ResourceAction.ActionMessage.SET_COST.format(cost_value=cost_value),
                operator=operator
            ),
            ResourceAction(
                resource=resource,
                action_type=ResourceAction.ActionType.SET_AMOUNT,
                message=ResourceAction.ActionMessage.SET_AMOUNT.format(amount_value=amount_value),
                operator=operator
            ),
        ]

        ResourceAction.objects.bulk_create(actions)
        resource.cost = cost.value
        resource.amount = amount.value
        resource.cost_time_stamp = cost.time_stamp
        resource.amount_time_stamp = amount.time_stamp
        resource.verified = cost.verified

        return resource

    @classmethod
    def bulk_create(cls, data: list, user):
        # TODO: test, optimize
        errors = []
        for resource in data:
            resource['user'] = user
            try:
                cls.create(**resource)
            except cls.UniqueField as ex:
                errors.append(ex)
        return errors

    @classmethod
    def update_fields(cls,
                      r_id,
                      resource_name=None,
                      external_id=None,
                      provider_name: str = None,
                      user=None):

        data = dict()

        message = "Изменён ресурс"
        operator = Operators.get_operator_by_user(user)

        if resource_name is not None:
            data['name'] = resource_name
            message += f"новое название ресурса: {resource_name}|"
        if external_id is not None:
            data['external_id'] = external_id
            message += f" новое внешение id: {external_id}|"
        if provider_name is not None:
            data['provider'] = ResourceProvider.objects.get_or_create(name=provider_name)[0]
            message += f"новый поставщик: {provider_name}"

        try:
            Resource.objects.filter(id=r_id).update(**data)
        except IntegrityError as ex:
            raise cls.UniqueField(ex)

        ResourceAction.objects.create(
            resource_id=r_id,
            action_type=ResourceAction.ActionType.UPDATE_FIELDS,
            message=message,
            operator=operator
        )

        return cls.detail(r_id)

    @classmethod
    def set_cost(cls, r_id, cost_value, user):
        cost = ResourceCost.objects.create(
            resource_id=r_id,
            value=cost_value
        )

        ResourceAction.objects.create(
            resource_id=r_id,
            action_type=ResourceAction.ActionType.SET_COST,
            message=ResourceAction.ActionMessage.SET_COST.format(cost_value=cost_value),
            operator=Operators.get_operator_by_user(user)
        )

        return cost

    @classmethod
    def bulk_set_cost(cls, data, user):
        ret = []
        for cost in data:
            cost['user'] = user
            ret.append(cls.set_cost(**cost))
        return ret

    @classmethod
    def set_amount(cls, r_id, amount_value, user):
        amount = ResourceAmount.objects.create(
            resource_id=r_id,
            value=amount_value
        )
        ResourceAction.objects.create(
            resource_id=r_id,
            action_type=ResourceAction.ActionType.SET_AMOUNT.format(amount_value=amount_value),
            operator=Operators.get_operator_by_user(user)
        )

        return amount

    @classmethod
    def change_amount(cls, r_id, delta_amount, user):
        amount = ResourceAmount.objects.create(
            resource_id=r_id,
            value=float(ResourceAmount.objects.defer('value').filter(resource_id=r_id).latest(
                'time_stamp').value) + delta_amount
        )
        if delta_amount > 0:
            action_type = ResourceAction.ActionType.RISE_AMOUNT
            action_message = ResourceAction.ActionMessage.RISE_AMOUNT.format(delta_amount=delta_amount)
        else:
            action_type = ResourceAction.ActionType.DROP_AMOUNT
            action_message = ResourceAction.ActionMessage.DROP_AMOUNT.format(delta_amount=abs(delta_amount))

        ResourceAction.objects.create(
            resource_id=r_id,
            action_type=action_type,
            message=action_message,
            operator=Operators.get_operator_by_user(user)
        )

        return amount

    def bulk_change_amount(self, data, user):
        # TODO: test, optimize
        ret = []
        for amount in data:
            amount['user'] = user
            ret.append(self.change_amount(**amount))
        return ret

    @classmethod
    def list(cls):
        cost_qr = ResourceCost.objects.filter(resource=OuterRef('pk')).order_by('-time_stamp')
        amount_qr = ResourceAmount.objects.filter(resource=OuterRef('pk')).order_by('-time_stamp')
        query = Resource.objects.select_related('provider').annotate(
            cost=Subquery(cost_qr.values('value')[:1]),
            last_change_cost=Subquery(cost_qr.values('time_stamp')[:1]),
            amount=Subquery(amount_qr.values('value')[:1]),
            last_change_amount=Subquery(amount_qr.values('time_stamp')[:1]),
            verified=Subquery(cost_qr.values('verified')[:1]),
        )

        return query.order_by('verified')

    @classmethod
    def providers(cls):
        return ResourceProvider.objects.all()

    @classmethod
    def with_unverified_cost(cls):
        cost_ver_qr = ResourceCost.objects.filter(resource=OuterRef('pk'), verified=True).order_by('-time_stamp')
        cost_unver_qr = ResourceCost.objects.filter(resource=OuterRef('pk'), verified=False).order_by('-time_stamp')
        amount_qr = ResourceAmount.objects.filter(resource=OuterRef('pk')).order_by('-time_stamp')
        query = Resource.objects.select_related('provider').annotate(
            unverified=Exists(cost_unver_qr),
            old_cost=Subquery(cost_ver_qr.values('value')[:1]),
            new_cost=Subquery(cost_unver_qr.values('value')[:1]),
            last_change_cost=Subquery(cost_unver_qr.values('time_stamp')[:1]),
            amount=Subquery(amount_qr.values_list('value')[:1]),
            last_change_amount=Subquery(amount_qr.values_list('time_stamp')[:1])
        ).filter(unverified=True)
        return query

    @classmethod
    def verify_cost(cls, r_id, user):
        with transaction.atomic():
            resource = Resource.objects.get(id=r_id)
            costs = ResourceCost.objects.filter(resource=resource, verified=False).update(verified=True)
            ResourceAction.objects.create(
                resource=resource,
                action_type=ResourceAction.ActionType.VERIFY_COST,
                message=ResourceAction.ActionMessage.VERIFY_COST,
                operator=Operators.get_operator_by_user(user)
            )
        return costs

    @classmethod
    def actions(cls, r_id):
        return ResourceAction.objects.filter(resource_id=r_id).order_by('-time_stamp')

    @classmethod
    def delete(cls, resource, user):
        if not isinstance(resource, Resource):
            Resource.objects.filter(id=resource).delete()
        resource.delete()

    @classmethod
    def bulk_delete(cls, ids, user):
        Resource.objects.filter(id__in=ids).delete()

    @classmethod
    def shortlist(cls):
        query_amount = ResourceAmount.objects.filter(resource=OuterRef('pk')).order_by('-time_stamp')
        query_cost = ResourceCost.objects.filter(resource=OuterRef('pk')).order_by('-time_stamp')
        query = Resource.objects.select_related('provider').annotate(
            cost=Subquery(query_cost.values('value')[:1]),
            amount=Subquery(query_amount.values('value')[:1]),
        )
        return query


class Specifications:
    class CreateException(Exception):
        pass

    @classmethod
    def detail(cls, specification):
        if not isinstance(specification, Specification):
            specification = Specification.objects.select_related('category').get(id=specification)

        query_res_spec = ResourceSpecification.objects.filter(specification=specification, resource=OuterRef('pk'))
        cost_qr = ResourceCost.objects.filter(resource=OuterRef('pk')).order_by('-time_stamp')
        amount_qr = ResourceAmount.objects.filter(resource=OuterRef('pk')).order_by('-time_stamp')
        resources = Resource.objects.annotate(
            cost=Subquery(cost_qr.values('value')[:1]),
            amount=Subquery(amount_qr.values('value')[:1]),
            res_spec_ex=Exists(query_res_spec.values('id')),
            needed_amount=Subquery(query_res_spec.values('amount')[:1]),
            verified=Subquery(cost_qr.values('verified')[:1])).filter(res_spec_ex=True)
        specification.verified = not resources.filter(verified=False).exists()
        try:
            price = SpecificationPrice.objects.filter(specification=specification).latest('time_stamp')
            specification.price = price.value
            specification.price_time_stamp = price.time_stamp

        except SpecificationPrice.DoesNotExist:
            specification.price = None
            specification.price_time_stamp = None

        try:
            coefficient = SpecificationCoefficient.objects.filter(specification=specification).latest('time_stamp')
            specification.coefficient = coefficient.value
            specification.coefficient_time_stamp = coefficient.time_stamp

        except SpecificationCoefficient.DoesNotExist:
            specification.coefficient = None
            specification.coefficient_time_stamp = None

        try:
            storage_amount = SpecificationAmount.objects.filter(specification=specification).latest('time_stamp').value
            specification.storage_amount = storage_amount

        except SpecificationAmount.DoesNotExist:
            specification.storage_amount = None

        resources = [{'resource': resource, 'amount': resource.needed_amount} for resource in resources]
        specification.resources = resources

        return specification

    @classmethod
    def list(cls):
        query_cost = ResourceCost.objects.filter(resource_id=OuterRef('resource_id')).order_by('-time_stamp')
        query_res_spec = ResourceSpecification.objects.filter(specification=OuterRef('pk')).values(
            'specification_id').annotate(
            total_cost=Sum(Subquery(query_cost.values('value')[:1]) * F('amount')),
            verified=Cast(Min(Cast(query_cost.values('verified')[:1], output_field=IntegerField())),
                          output_field=BooleanField()))
        query_price = SpecificationPrice.objects.filter(specification=OuterRef('pk')).order_by('-time_stamp')
        query_coefficient = SpecificationCoefficient.objects.filter(specification=OuterRef('pk')).order_by(
            '-time_stamp')
        query_amount = SpecificationAmount.objects.filter(specification=OuterRef('pk')).order_by('-time_stamp')
        specifications = Specification.objects.select_related('category').annotate(
            prime_cost=Subquery(query_res_spec.values('total_cost')),
            price=Subquery(query_price.values('value')[:1]),
            price_time_stamp=Subquery(query_price.values('time_stamp')[:1]),
            coefficient=Subquery(query_coefficient.values('value')[:1]),
            coefficient_time_stamp=Subquery(query_coefficient.values('time_stamp')[:1]),
            verified=Subquery(query_res_spec.values('verified')[:1]),
            storage_amount=Subquery(query_amount.values('value')[:1])
        )
        return specifications

    @classmethod
    def categories(cls):
        return SpecificationCategory.objects.all()

    @classmethod
    def create(cls,
               name: str,
               product_id: str,
               price: float = None,
               coefficient: float = None,
               resources: List[Dict[str, str]] = None,
               category_name: str = None,
               storage_amount: int = None,
               user=None):
        try:
            with transaction.atomic():
                operator = Operators.get_operator_by_user(user)

                if category_name is not None:
                    category = SpecificationCategory.objects.get_or_create(name=category_name)[0]

                else:
                    category = None

                if Specification.objects.filter(product_id=product_id, is_active=True).exists():
                    s = Specification.objects.filter(product_id=product_id).get(is_active=True)
                    s.is_active = False
                    s.save()

                    SpecificationAction.objects.create(
                        specification=s,
                        action_type=SpecificationAction.ActionType.DEACTIVATE,
                        operator=operator)

                specification = Specification.objects.create(
                    name=name,
                    product_id=product_id,
                    category=category,
                    is_active=True)

                res_specs = []
                _resources = []
                if resources is not None and len(resources) != 0:
                    for resource in resources:
                        # optimize it...
                        res = Resource.objects.get(id=resource['id'])
                        res.amount = ResourceAmount.objects.filter(resource=res).latest('time_stamp').value
                        res.cost = ResourceCost.objects.filter(resource=res).latest('time_stamp').value
                        res_specs.append(
                            ResourceSpecification(
                                resource=res,
                                amount=resource['amount'],
                                specification=specification
                            )
                        )
                        _resources.append({'resource': res, 'amount': resource['amount']})

                    ResourceSpecification.objects.bulk_create(res_specs)

                specification.resources = _resources

                SpecificationAction.objects.create(
                    specification=specification,
                    action_type=SpecificationAction.ActionType.CREATE,
                    operator=operator
                )

                if price is None:
                    price = 0

                if storage_amount is None:
                    storage_amount = 0

                price = cls.set_price(specification, price, user)
                specification.price = price.value
                specification.price_time_stamp = price.time_stamp

                storage_amount = cls.set_amount(specification, storage_amount, user)
                specification.storage_amount = storage_amount.value

                if coefficient is not None:
                    coefficient = cls.set_coefficient(specification, coefficient, user)
                    specification.coefficient = coefficient.value
                    specification.coefficient_time_stamp = coefficient.time_stamp

                elif category is not None and category.coefficient is not None:
                    coefficient = cls.set_coefficient(specification, category.coefficient, user)
                    specification.coefficient = coefficient.value
                    specification.coefficient_time_stamp = coefficient.time_stamp

                else:
                    specification.coefficient = None
                    specification.coefficient_time_stamp = None

        except DatabaseError as ex:
            raise cls.CreateException(ex)

        return specification

    @classmethod
    def edit(cls,
             specification,
             name: str = None,
             product_id: str = None,
             price: float = None,
             coefficient: float = None,
             resource_to_add: List[Dict[str, str]] = None,
             resource_to_delete: List[str] = None,
             category_name: str = None,
             storage_amount: int = None,
             user=None):

        if not isinstance(specification, Specification):
            specification = Specification.objects.get(id=specification)

        if name is not None:
            specification.name = name
        if product_id is not None:
            specification.product_id = product_id
        if category_name is not None:
            specification.category = SpecificationCategory.objects.get_or_create(name=category_name)[0]

        specification.save()
        operator = Operators.get_operator_by_user(user)

        SpecificationAction.objects.create(specification=specification,
                                           action_type=SpecificationAction.ActionType.UPDATE,
                                           operator=operator)

        if price is not None:
            price = cls.set_price(specification, price, user)

            specification.price = price.value
            specification.price_time_stamp = price.time_stamp

        else:
            try:
                price = SpecificationPrice.objects.filter(specification=specification).latest('time_stamp')
                specification.price = price.value
                specification.price_time_stamp = price.time_stamp

            except SpecificationPrice.DoesNotExist():
                specification.price = None
                specification.price_time_stamp = None

        if coefficient is not None:
            coefficient = cls.set_coefficient(specification, coefficient, user)
            specification.coefficient = coefficient.value
            specification.coefficient_time_stamp = coefficient.time_stamp

        else:
            try:
                coefficient = SpecificationCoefficient.objects.filter(specification=specification).latest('time_stamp')
                specification.coefficient = coefficient.value
                specification.coefficient_time_stamp = coefficient.time_stamp

            except SpecificationCoefficient.DoesNotExist:
                specification.coefficient = None
                specification.coefficient_time_stamp = None

        if storage_amount is not None:
            storage_amount = cls.set_amount(specification, storage_amount, user)
            specification.storage_amount = storage_amount.value

        else:
            try:
                storage_amount = SpecificationAmount.objects.filter(specification=specification).latest('time_stamp')
                specification.storage_amount = storage_amount.value

            except SpecificationAmount.DoesNotExist:
                specification.storage_amount = None

        if resource_to_delete is not None and len(resource_to_delete) != 0:
            ResourceSpecification.objects.filter(resource_id__in=resource_to_delete).delete()

        if resource_to_add is not None and len(resource_to_add) != 0:
            res_specs = []
            _resources = []
            for resource in resource_to_add:
                res = Resource.objects.get(id=resource['id'])
                res.cost = ResourceCost.objects.filter(resource=res).latest('time_stamp').value
                res_specs.append(
                    ResourceSpecification(
                        resource_id=resource['id'],
                        amount=resource['amount'],
                        specification=specification
                    )
                )
                _resources.append({'resource': res, 'amount': resource['amount']})

            ResourceSpecification.objects.bulk_create(res_specs)

        try:
            res_specs = ResourceSpecification.objects.select_related('resource').filter(specification=specification)
            for res_spec in res_specs:
                res = res_spec.resource
                res_cost = ResourceCost.objects.filter(resource=res).latest('time_stamp')
                res.cost = res_cost.value
                res_amount = ResourceAmount.objects.filter(resource=res).latest('time_stamp')
                res.amount = res_amount.value

        except ResourceSpecification.DoesNotExist():
            res_specs = []

        specification.resources = res_specs

        return specification

    @classmethod
    def set_coefficient(cls, specification, coefficient: float, user=None):
        if not isinstance(specification, Specification):
            specification = Specification.objects.get(id=specification)

        coefficient = SpecificationCoefficient.objects.create(specification=specification, value=coefficient)
        SpecificationAction.objects.create(
            specification=specification,
            action_type=SpecificationAction.ActionType.SET_COEFFICIENT,
            operator=Operators.get_operator_by_user(user)
        )
        return coefficient

    @classmethod
    def set_price(cls, specification, price: float, user=None):
        if not isinstance(specification, Specification):
            specification = Specification.objects.get(id=specification)

        price = SpecificationPrice.objects.create(specification=specification, value=price)
        SpecificationAction.objects.create(
            specification=specification,
            action_type=SpecificationAction.ActionType.SET_PRICE,
            operator=Operators.get_operator_by_user(user)
        )
        return price

    @classmethod
    def set_amount(cls, specification, amount: float, user=None):
        if not isinstance(specification, Specification):
            specification = Specification.objects.get(id=specification)

        amount = SpecificationAmount.objects.create(specification=specification, value=amount)
        SpecificationAction.objects.create(
            specification=specification,
            action_type=SpecificationAction.ActionType.SET_AMOUNT,
            operator=Operators.get_operator_by_user(user)
        )
        return amount

    @classmethod
    def set_category(cls, ids: List, category):
        if not isinstance(category, SpecificationCategory):
            category = SpecificationCategory.objects.get(id=category)
        if category.coefficient is not None:
            for s_id in ids:
                SpecificationCoefficient.objects.create(
                    specification_id=s_id,
                    value=category.coefficient
                )
        Specification.objects.filter(id__in=ids).update(category=category)

    @classmethod
    def assemble_info(cls, specification):
        if not isinstance(specification, Specification):
            specification = Specification.objects.prefetch_related(
                'res_specs__resource',
                'res_specs__resource__amounts'
            ).get(id=specification)

        min_amount = None

        for res_spec in specification.res_specs.all():
            if min_amount is None:
                min_amount = int(res_spec.resource.amounts.latest('time_stamp').value / res_spec.amount)
            min_amount = min(min_amount, int(res_spec.resource.amounts.latest('time_stamp').value / res_spec.amount))

        return min_amount

    @classmethod
    def delete(cls, specification, user):
        if not isinstance(specification, Specification):
            specification = Specification.objects.get(id=specification)
        specification.delete()

    @classmethod
    def bulk_delete(cls, ids, user):
        Specification.objects.filter(id__in=ids).delete()

    @classmethod
    def build_set(cls, specification, amount, from_resources=False, user=None):
        if not isinstance(specification, Specification):
            if from_resources:
                specification = Specification.objects.select_related(
                    'res_specs',
                    'res_specs__resource'
                    'res_specs__resource__amounts'
                ).get(id=specification)
            else:
                specification = Specification.objects.get(id=specification)

        res_amount = []
        if from_resources:
            for res_spec in specification.res_specs:
                res_amount.append(
                    ResourceAmount(
                        resource=res_spec.resource,
                        value=res_spec.resource.amounts.latest('time_stamp').value - res_spec.amount * amount
                    )
                )
            ResourceAmount.objects.bulk_create(res_amount)

        if SpecificationAmount.objects.filter(specification=specification).exists():
            spec_amount = SpecificationAmount.objects.filter(specification=specification).latest('time_stamp')
            SpecificationAmount.objects.create(
                specification=specification,
                value=spec_amount.value + amount
            )

        else:
            SpecificationAmount.objects.create(
                specification=specification,
                value=amount
            )

        return


class Orders:
    class CanNotAssembleOrder(Exception):
        pass

    class CanNotManageAction(Exception):
        pass

    @classmethod
    def list(cls):
        orders = Order.objects.prefetch_related(
            'order_specification',
            'order_specification__specification'
        ).exclude(
            status__in=[
                Order.OrderStatus.ARCHIVED
            ]
        ).order_by('status')
        return orders

    @classmethod
    def assembling_info(cls, order):
        if not isinstance(order, Order):
            order = Order.objects.prefetch_related(
                'order_specification',
                'order_specification__specification',
                'order_specification__specification__amounts',
                'order_specification__specification__res_specs',
                'order_specification__specification__res_specs__resource',
                'order_specification__specification__res_specs__resource__amounts'
            ).get(id=order)

        resources = {}
        miss_resources = set()
        miss_specification = set()

        for order_spec in order.order_specification.all():
            specification = order_spec.specification

            for res_spec in specification.res_specs.all():
                resource = res_spec.resource
                amount = resource.amounts.latest('time_stamp').value
                storage_amount = specification.amounts.latest('time_stamp').value

                if resource.id not in resources:
                    resources[resource.id] = [
                        amount,
                        res_spec.amount * (order_spec.amount - storage_amount)
                    ]

                else:
                    resources[resource.id][1] += res_spec.amount * (order_spec.amount - storage_amount)

                if resources[resource.id][0] < resources[resource.id][1]:
                    miss_resources.add(resource.id)
                    miss_specification.add(specification.id)

        return miss_specification, miss_resources

    @classmethod
    def detail(cls, o_id):
        order = Order.objects.prefetch_related(
            'order_specification',
            'order_specification__specification',
        ).get(id=o_id)

        return order

    @classmethod
    def assemble_specification(cls, order_id, specification_id, user=None):
        order = Order.objects.get(id=order_id)

        if not (order.status == Order.OrderStatus.ACTIVE or order.status == Order.OrderStatus.ASSEMBLING):
            raise cls.CanNotAssembleOrder()

        operator = Operators.get_operator_by_user(user)

        OrderSpecification.objects.filter(specification_id=specification_id, order=order).update(assembled=True)

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

    @classmethod
    def disassemble_specification(cls, order_id, specification_id, user=None):
        order = Order.objects.get(id=order_id)
        if not (order.status == Order.OrderStatus.READY or order.status == Order.OrderStatus.ASSEMBLING):
            raise cls.CanNotAssembleOrder()

        operator = Operators.get_operator_by_user(user)

        OrderSpecification.objects.filter(specification_id=specification_id, order=order).update(assembled=False)

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

    @classmethod
    def delete(cls, order, user):
        if not isinstance(order, Order):
            Order.objects.filter(id=order).delete()
        order.delete()

    @classmethod
    def bulk_delete(cls, ids, user):
        Order.objects.filter(id__in=ids).delete()

    @classmethod
    def confirm(cls, order_id, user):
        order = Order.objects.get(id=order_id)
        if not order.status == Order.OrderStatus.READY:
            raise cls.CanNotManageAction()
        cls._confirm(order, Operators.get_operator_by_user(user))
        order.save()

    @classmethod
    def activate(cls, order_id, user):
        order = Order.objects.prefetch_related(
            'order_specification',
            'order_specification__specification',
            'order_specification__specification__amounts',
            'order_specification__specification__res_specs',
            'order_specification__specification__res_specs__resource',
            'order_specification__specification__res_specs__resource__amounts'
        ).get(id=order_id)

        order_specs = order.order_specification

        for order_spec in order_specs.all():
            specification = order_spec.specification
            res_specs = specification.res_specs
            if specification.amounts.exists():
                storage_amount = specification.amounts.latest('time_stamp').value
            else:
                storage_amount = 0
            if storage_amount > order_spec.amount:
                storage_amount -= order_spec.amount
                Specifications.set_amount(specification, storage_amount, user)
                continue

            else:
                storage_amount = specification.amounts.latest('time_stamp').value
                Specifications.set_amount(specification, 0, user)

            for res_spec in res_specs.all():
                resource = res_spec.resource
                amount = resource.amounts.latest('time_stamp').value
                print(f"amount={amount}")
                print(f"storage_amount={storage_amount}")
                print(f"order_spec.amount={order_spec.amount}")
                print(f"res_spec.amount={res_spec.amount}")
                if amount >= res_spec.amount * (order_spec.amount - storage_amount):
                    ResourceAmount.objects.create(
                        resource=resource,
                        value=amount - res_spec.amount * (order_spec.amount - storage_amount)
                    )

                else:
                    raise cls.CanNotManageAction(f"resource {resource.name}, amount {amount}")

        if not order.status == Order.OrderStatus.INACTIVE:
            raise cls.CanNotManageAction()
        cls._activate(order, Operators.get_operator_by_user(user))
        order.save()

    @classmethod
    def deactivate(cls, order_id, user):
        order = Order.objects.get(id=order_id)
        if order.status not in [Order.OrderStatus.ACTIVE, Order.OrderStatus.ASSEMBLING, Order.OrderStatus.READY]:
            raise cls.CanNotManageAction()

        order_specs = order.order_specification

        for order_spec in order_specs.all():
            specification = order_spec.specification
            res_specs = specification.res_specs
            order_spec.assembled = False
            order_spec.save()
            for res_spec in res_specs.all():
                resource = res_spec.resource
                amount = resource.amounts.latest('time_stamp').value

                ResourceAmount.objects.create(
                    resource=resource,
                    value=amount + res_spec.amount * order_spec.amount
                )

        cls._deactivate(order, Operators.get_operator_by_user(user))
        order.save()

    @classmethod
    def create(cls,
               external_id,
               source: str = None,
               products: List[Dict[str, str]] = None):

        order = Order.objects.create(external_id=external_id,
                                     source=source,
                                     status=Order.OrderStatus.INACTIVE)

        order_specs = []
        _specs = []

        for product in products:
            order_spec = OrderSpecification(
                order=order,
                specification=Specification.objects.get(
                    product_id=product['product_id'],
                    is_active=True
                ),
                amount=product['amount']
            )
            order_specs.append(
                order_spec
            )
            _specs.append({'specification': order_spec, 'amount': product['amount']})

        OrderSpecification.objects.bulk_create(order_specs)
        order.specifications = _specs
        return order

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
            operator=operator
        )

from typing import List, Dict

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max, Q, Subquery, OuterRef, Exists, Sum, F, ExpressionWrapper

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
                     ResourceSpecificationAssembled,
                     ResourceSpecification)
from django.db import IntegrityError, transaction


class Service:

    def __init__(self, request=None):
        self.request = request


class Operators(Service):

    @classmethod
    def get_operator_by_user(cls, user):
        if user is None:
            operator = Operator.get_system_operator()
        elif user.is_anonymous:
            operator = Operator.get_anonymous_operator()
        else:
            operator = Operator.get_user_operator(user)
        return operator


class Providers(Service):

    @classmethod
    def get_by_name(cls, name):
        return ResourceProvider.objects.get(name=name)


class Resources(Service):
    class ResourceDoesNotExist(ObjectDoesNotExist):
        pass

    class UniqueField(IntegrityError):
        pass

    def detail(self, r_id):
        # TODO: test
        resource = Resource.objects.select_related('provider').get(id=r_id)
        cost = ResourceCost.objects.defer('value').filter(resource_id=r_id).latest('time_stamp')
        amount = ResourceAmount.objects.defer('value').filter(resource_id=r_id).latest('time_stamp')
        resource.cost = cost.value
        resource.amount = amount.value
        resource.cost_time_stamp = cost.time_stamp
        resource.amount_time_stamp = amount.time_stamp
        return resource

    def create(self,
               resource_name: str,
               external_id: str,
               cost_value: float = 0,
               amount_value: float = 0,
               provider_name: str = None):
        if cost_value is None:
            cost_value = .0
        if amount_value is None:
            amount_value = .0
        # TODO: test
        if provider_name is not None:
            provider = ResourceProvider.objects.get_or_create(name=provider_name)[0]
        else:
            provider = None
        try:
            resource = Resource.objects.create(name=resource_name,
                                               external_id=external_id,
                                               provider=provider)
        except IntegrityError:
            raise Resources.UniqueField()
        cost = ResourceCost.objects.create(resource=resource,
                                           value=cost_value,
                                           verified=True)
        amount = ResourceAmount.objects.create(resource=resource,
                                               value=amount_value)

        operator = Operators.get_operator_by_user(self.request.user)

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
        return resource, actions

    def bulk_create(self, data: list):
        # TODO: test, optimize
        for resource in data:
            self.create(**resource)

    def update_fields(self,
                      r_id,
                      resource_name=None,
                      external_id=None,
                      provider_name: str = None,
                      ):
        # TODO: test
        data = dict()

        message = "Изменён ресурс"
        operator = Operators.get_operator_by_user(self.request.user)

        if resource_name is not None:
            data['name'] = resource_name
            message += f"новое название ресурса: {resource_name}|"
        if external_id is not None:
            data['external_id'] = external_id
            message += f" новое внешение id: {external_id}|"
        if provider_name is not None:
            data['provider'] = ResourceProvider.objects.get_or_create(name=provider_name)[0]
            message += f"новый поставщик: {provider_name}"

        Resource.objects.filter(id=r_id).update(**data)

        action = ResourceAction.objects.create(
            resource_id=r_id,
            action_type=ResourceAction.ActionType.UPDATE_FIELDS,
            message=message,
            operator=operator
        )

        return self.detail(r_id), action

    def set_cost(self, r_id, cost_value):
        # TODO: test
        cost = ResourceCost.objects.create(
            resource_id=r_id,
            value=cost_value
        )

        action = ResourceAction.objects.create(
            resource_id=r_id,
            action_type=ResourceAction.ActionType.SET_COST,
            message=ResourceAction.ActionMessage.SET_COST.format(cost_value=cost_value),
            operator=Operators.get_operator_by_user(self.request.user)
        )

        return cost, action

    def bulk_set_cost(self, data):
        # TODO: test, optimize
        ret = []
        for cost in data:
            ret.append(self.set_cost(**cost))
        return ret

    def set_amount(self, r_id, amount_value):
        # TODO: test
        amount = ResourceAmount.objects.create(
            resource_id=r_id,
            value=amount_value
        )
        action = ResourceAction.objects.create(
            resource_id=r_id,
            action_type=ResourceAction.ActionType.SET_AMOUNT.format(amount_value=amount_value),
            operator=Operators.get_operator_by_user(self.request.user)
        )

        return amount, action

    def change_amount(self, r_id, delta_amount):
        #  TODO: test
        amount = ResourceAmount.objects.create(
            resource_id=r_id,
            value=ResourceAmount.objects.defer('value').filter(resource_id=r_id).latest(
                'time_stamp').value + delta_amount
        )
        if delta_amount > 0:
            action_type = ResourceAction.ActionType.RISE_AMOUNT
            action_message = ResourceAction.ActionMessage.RISE_AMOUNT.format(delta_amount=delta_amount)
        else:
            action_type = ResourceAction.ActionType.DROP_AMOUNT
            action_message = ResourceAction.ActionMessage.DROP_AMOUNT.format(delta_amount=abs(delta_amount))

        action = ResourceAction.objects.create(
            resource_id=r_id,
            action_type=action_type,
            message=action_message,
            operator=Operators.get_operator_by_user(self.request.user)
        )

        return amount, action

    def bulk_change_amount(self, data):
        # TODO: test, optimize
        ret = []
        for amount in data:
            ret.append(self.change_amount(**amount))
        return ret

    def list(self):
        cost_qr = ResourceCost.objects.filter(resource=OuterRef('pk')).order_by('-time_stamp')
        amount_qr = ResourceAmount.objects.filter(resource=OuterRef('pk')).order_by('-time_stamp')
        query = Resource.objects.select_related('provider').annotate(
            cost=Subquery(cost_qr.values('value')[:1]),
            last_change_cost=Subquery(cost_qr.values('time_stamp')[:1]),
            amount=Subquery(amount_qr.values_list('value')[:1]),
            last_change_amount=Subquery(amount_qr.values_list('time_stamp')[:1])
        )

        return query

    def shortlist(self):
        return Resource.objects.all()

    def providers(self):
        return ResourceProvider.objects.all()

    def with_unverified_cost(self):
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

    def verify_cost(self, r_id):
        with transaction.atomic():
            resource = Resource.objects.get(id=r_id)
            costs = ResourceCost.objects.filter(resource=resource, verified=False).update(verified=True)
        return costs

    def actions(self, r_id):
        return ResourceAction.objects.filter(resource_id=r_id).order_by('-time_stamp')


class Specifications(Service):

    def detail(self, s_id):
        specification = Specification.objects.select_related('category').get(id=s_id)

        service = Resources(self.request)
        query_res_spec = ResourceSpecification.objects.filter(specification=specification, resource=OuterRef('pk'))
        resources = service.list().annotate(
            res_spec_ex=Exists(query_res_spec.values('id')),
            needed_amount=Subquery(query_res_spec.values('amount')[:1])).filter(res_spec_ex=True)
        try:
            price = SpecificationPrice.objects.filter(specification=specification).latest('time_stamp')
            specification.price = price.value
            specification.price_time_stamp = price.time_stamp
        except SpecificationPrice.DoesNotExist:
            specification.price = None
            specification.price_time_stamp = None
        resources = [{'resource': resource, 'amount': resource.needed_amount} for resource in resources]
        specification.resources = resources

        return specification

    def list(self):
        query_cost = ResourceCost.objects.filter(resource_id=OuterRef('resource_id')).order_by('-time_stamp')
        query_res_spec = ResourceSpecification.objects.filter(specification=OuterRef('pk')).values(
            'specification_id').annotate(
            total_cost=Sum(Subquery(query_cost.values('value')[:1]) * F('amount')))
        query_price = SpecificationPrice.objects.filter(specification=OuterRef('pk')).order_by('-time_stamp')
        specifications = Specification.objects.select_related('category').annotate(
            prime_cost=Subquery(query_res_spec.values('total_cost')[:2]),
            price=Subquery(query_price.values('value')[:1]),
            price_time_stamp=Subquery(query_price.values('time_stamp')[:1])
        )
        return specifications

    def categories(self):
        return SpecificationCategory.objects.all()

    @classmethod
    def create(cls,
               name: str,
               product_id: str,
               price: float = None,
               resources: List[Dict[str, str]] = None,
               category_name: str = None,
               user=None):

        operator = Operators.get_operator_by_user(user)

        if price is None:
            price = 0
        if category_name is not None:
            category = SpecificationCategory.objects.get_or_create(name=category_name)[0]
        else:
            category = None
        deactivated = False
        if Specification.objects.filter(product_id=product_id, is_active=True).exists():
            s = Specification.objects.filter(product_id=product_id).get(is_active=True)
            s.is_active = False
            s.save()
            SpecificationAction.objects.create(
                specification=s,
                action_type=SpecificationAction.ActionType.DEACTIVATE,
                operator=operator
            )
            deactivated = True
        specification = Specification.objects.create(
            name=name,
            product_id=product_id,
            category=category,
            is_active=True
        )
        res_specs = []
        if resources is not None and len(resources) != 0:
            for resource in resources:
                res_specs.append(
                    ResourceSpecification(
                        resource_id=resource['id'],
                        amount=resource['amount'],
                        specification=specification
                    )
                )
            res_specs = ResourceSpecification.objects.bulk_create(res_specs)

        SpecificationAction.objects.create(
            specification=specification,
            action_type=SpecificationAction.ActionType.CREATE,
            operator=operator
        )

        if price is not None:
            price = SpecificationPrice.objects.create(
                specification=specification,
                value=price,
                verified=True
            )
            SpecificationAction.objects.create(
                specification=specification,
                action_type=SpecificationAction.ActionType.SET_PRICE,
                operator=operator
            )
            specification.price = price.value
            specification.price_time_stamp = price.time_stamp
            specification.resources = res_specs
        else:
            price = None
            specification.price = None
            specification.price_time_stamp = None
        specification.resources = res_specs

        return specification

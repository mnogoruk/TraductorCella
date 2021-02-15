from typing import List, Dict
from rest_framework.exceptions import APIException
from django.utils.translation import gettext_lazy as _
import pandas as pd

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max, Q, Subquery, OuterRef, Exists, Sum, F, ExpressionWrapper, Min, IntegerField, \
    BooleanField
from django.db.models.functions import Cast

from .models import (Operator,
                     ResourceProvider,
                     Resource,
                     ResourceCost,
                     ResourceAction,
                     Specification,
                     SpecificationAction,
                     SpecificationCategory,
                     ResourceSpecification,
                     OrderSource,
                     Order,
                     OrderSpecification,
                     OrderAction)
from django.db import IntegrityError, transaction, DatabaseError
import random, string


def random_str(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))


def resource_amounts(objects, amount_list):
    ret = []
    for obj in objects:
        for pair in amount_list:
            if pair['id'] == obj.id:
                ret.append({'resource': obj, 'amount': pair['amount']})
                break
    return ret


def product_amounts(objects, amount_list):
    ret = []
    for obj in objects:
        for pair in amount_list:
            if pair['product_id'] == obj.product_id:
                ret.append({'specification': obj, 'amount': pair['amount']})
                break
    return ret


class Operators:

    @classmethod
    def get_operator(cls, user):

        if isinstance(user, Operator):
            return user
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

    class CreateException(Exception):
        pass

    @classmethod
    def get(cls, resource):
        if not isinstance(resource, Resource):
            try:
                return Resource.objects.select_related('provider').get(id=resource)
            except IntegrityError:
                raise cls.ResourceDoesNotExist()
        else:
            return resource

    @classmethod
    def set_amount(cls, resource, amount_value, user, save=True):
        resource = cls.get(resource)
        resource.amount = amount_value

        action = ResourceAction(
            resource=resource,
            action_type=ResourceAction.ActionType.SET_AMOUNT.format(amount_value=amount_value),
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
        resource = cls.get(resource)
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
    def update_fields(cls, resource, resource_name=None, external_id=None, provider_name: str = None, user=None):

        resource = cls.get(resource)
        operator = Operators.get_operator(user)
        value_data = []

        if resource_name is not None:
            resource.name = resource_name
            value_data.append(f"name={resource_name}")
        if external_id is not None:
            resource.external_id = external_id
            value_data.append(f"external_id={external_id}")
        if provider_name is not None:
            resource.provider = ResourceProvider.objects.get_or_create(name=provider_name)[0]
            value_data.append(f"provider_name={provider_name}")

        ResourceAction.objects.create(
            resource=resource,
            action_type=ResourceAction.ActionType.UPDATE_FIELDS,
            operator=operator,
            value="|".join(value_data)
        )

        return cls.detail(resource)

    @classmethod
    def detail(cls, resource):

        resource = cls.get(resource)
        cost = ResourceCost.objects.filter(resource=resource).latest('time_stamp')

        resource.cost = cost.value
        resource.cost_time_stamp = cost.time_stamp
        resource.amount_time_stamp = ResourceAction.objects.filter(
            action_type__in=[ResourceAction.ActionType.SET_AMOUNT, ResourceAction.ActionType.CHANGE_AMOUNT],
            resource=resource
        ).latest('time_stamp').time_stamp
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
                    raise cls.UniqueField()

                operator = Operators.get_operator(user)

                ResourceAction(
                    resource=resource,
                    action_type=ResourceAction.ActionType.CREATE,
                    operator=operator
                ).save()

                cost, cost_action = cls.set_cost(resource, cost_value, operator, False, True)
                cost.verified = True
                cost.save()
                cost_action.save()
                amount, amount_action = cls.set_amount(resource, amount_value, operator)

                resource.cost = cost.value
                resource.cost_time_stamp = cost.time_stamp
                resource.amount_time_stamp = amount_action.time_stamp
                resource.verified = cost.verified

        except DatabaseError as ex:
            raise cls.CreateException(ex)

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
    def list(cls):
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
    def create_from_excel(cls, file, user=None):
        excel = pd.read_excel(file)

        errors = []

        with transaction.atomic():
            operator = Operators.get_operator(user)
            actions = []
            costs = []
            resources = []
            provider_dict = {}
            ext = []
            for x in range(excel.shape[0]):

                row = excel.iloc[x]

                if (not pd.isnull(row['Спецификация / Ресурс'])) and row['Спецификация / Ресурс'].lower() == 'resource':
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
                            provider = ResourceProvider.objects.get_or_create(name=provider_name)[0]
                            provider_dict[provider_name] = provider
                        else:
                            provider = provider_dict[provider_name]

                    obj['provider'] = provider
                    resource = Resource.objects.create(**obj)

                    if pd.isnull(row['Цена']):
                        cost_value = 0
                    else:
                        cost_value = row['Цена']

                    cost, cost_action = cls.set_cost(resource, cost_value, operator, verified=True, save=False)
                    amount, amount_action = cls.set_amount(resource, amount_value, operator, save=False)
                    create_action = ResourceAction(
                        resource=resource,
                        operator=operator,
                        action_type=ResourceAction.ActionType.CREATE)

                    costs.append(cost)
                    actions.append(cost_action)
                    actions.append(amount_action)
                    actions.append(create_action)
                    resources.append(resource)
            ResourceCost.objects.bulk_create(costs)
            ResourceAction.objects.bulk_create(actions)
            Resource.objects.bulk_update(resources, fields=['amount'])


class Specifications:
    class CreateException(Exception):
        pass

    class EditException(Exception):
        pass

    class SpecificationDoesNotExist(ObjectDoesNotExist):
        pass

    class UniqueField(APIException):
        status_code = 400
        default_detail = _('Не уникальное значение')
        default_code = 'bad_request'

    class CategoryDoesNotExist(ObjectDoesNotExist):
        pass

    class CantBuildSet(Exception):
        pass

    @classmethod
    def get(cls, specification):
        if not isinstance(specification, Specification):
            try:
                return Specification.objects.select_related('category').get(id=specification, is_active=True)
            except IntegrityError:
                raise cls.SpecificationDoesNotExist()
        else:
            return specification

    @classmethod
    def get_category(cls, category):
        if not isinstance(category, SpecificationCategory):
            try:
                return SpecificationCategory.objects.get(id=category)
            except IntegrityError:
                raise cls.CategoryDoesNotExist()
        else:
            return category

    @classmethod
    def set_coefficient(cls, specification, coefficient: float, user=None, save=True):
        specification = cls.get(specification)
        specification.coefficient = coefficient

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
    def set_price(cls, specification, price: float, user=None, save=True):
        specification = cls.get(specification)
        specification.price = price

        action = SpecificationAction(
            specification=specification,
            action_type=SpecificationAction.ActionType.SET_PRICE,
            operator=Operators.get_operator(user),
            value=str(price)
        )

        if save:
            specification.save()
            action.save()

        return price, action

    @classmethod
    def set_amount(cls, specification, amount: float, user=None, save=True):
        specification = cls.get(specification)
        specification.amount = amount

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

        SpecificationAction.objects.bulk_create(actions)
        return category, actions

    @classmethod
    def detail(cls, specification):
        specification = cls.get(specification)

        query_res_spec = ResourceSpecification.objects.filter(specification=specification, resource=OuterRef('pk'))
        cost_qr = ResourceCost.objects.filter(resource=OuterRef('pk')).order_by('-time_stamp')
        resources = Resource.objects.annotate(
            cost=Subquery(cost_qr.values('value')[:1]),
            res_spec_ex=Exists(query_res_spec.values('id')),
            needed_amount=Subquery(query_res_spec.values('amount')[:1]),
            verified=Subquery(cost_qr.values('verified')[:1])).filter(res_spec_ex=True)
        specification.verified = not resources.filter(verified=False).exists()

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
        specifications = Specification.objects.select_related('category').annotate(
            prime_cost=Subquery(query_res_spec.values('total_cost')),
            verified=Subquery(query_res_spec.values('verified')[:1]),
        )
        return specifications

    @classmethod
    def categories(cls):
        return SpecificationCategory.objects.all()

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
                    res_specs = []
                    resource_objects = Resource.objects.prefetch_related('resourcecost_set').filter(
                        id__in=map(lambda x: x['id'], resources))
                    res_specs_dict = resource_amounts(resource_objects, resources)
                    for resource in res_specs_dict:
                        res = resource['resource']
                        res.cost = res.resourcecost_set.last().value
                        res_specs.append(
                            ResourceSpecification(
                                resource=res,
                                amount=resource['amount'],
                                specification=specification
                            )
                        )

                        specification.resources = res_specs_dict
                        ResourceSpecification.objects.bulk_create(res_specs)

                SpecificationAction.objects.create(
                    specification=specification,
                    action_type=SpecificationAction.ActionType.CREATE,
                    operator=operator
                )

                specification.save()
                SpecificationAction.objects.bulk_create(actions)

        except DatabaseError as ex:
            raise cls.CreateException(ex)

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
                        category = None
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
                    ResourceSpecification.objects.filter(
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
                            ResourceSpecification(
                                resource_id=resource['id'],
                                amount=resource['amount'],
                                specification=specification
                            )
                        )
                        _resources.append({'resource': res, 'amount': resource['amount']})

                    ResourceSpecification.objects.bulk_create(res_specs)

                try:
                    res_specs = ResourceSpecification.objects.select_related('resource').filter(
                        specification=specification)
                    for res_spec in res_specs:
                        res = res_spec.resource
                        res_cost = ResourceCost.objects.filter(resource=res).latest('time_stamp')
                        res.cost = res_cost.value

                    specification.resources = res_specs

                except ResourceSpecification.DoesNotExist:
                    raise Resources.ResourceDoesNotExist()
        except DatabaseError as ex:
            raise cls.EditException(ex)

        return specification

    @classmethod
    def assemble_info(cls, specification):
        if not isinstance(specification, Specification):
            specification = Specification.objects.prefetch_related(
                'res_specs__resource',
            ).get(id=specification)

        min_amount = None

        for res_spec in specification.res_specs.all():
            if min_amount is None:
                min_amount = int(res_spec.resource.amount / res_spec.amount)
            min_amount = min(min_amount, int(res_spec.resource.amount / res_spec.amount))

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


class Orders:
    class CanNotAssembleOrder(Exception):
        pass

    class CanNotManageAction(Exception):
        pass

    class OrderDoesNotExist(ObjectDoesNotExist):
        pass

    class CreateException(Exception):
        pass

    @classmethod
    def get(cls, order):
        if not isinstance(order, Order):
            try:
                return Order.objects.select_related('source').get(id=order)
            except IntegrityError:
                raise cls.OrderDoesNotExist()
        else:
            return order

    @classmethod
    def sources(cls):
        return OrderSource.objects.all()

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
                'order_specification__specification__res_specs',
                'order_specification__specification__res_specs__resource'
            ).get(id=order)

        resources = {}
        miss_resources = set()
        miss_specification = set()

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

        return miss_specification, miss_resources

    @classmethod
    def detail(cls, order):
        order = Order.objects.prefetch_related(
            'order_specification',
            'order_specification__specification',
        ).get(id=order)

        return order

    @classmethod
    def assemble_specification(cls, order, specification, user=None):
        order = cls.get(order)
        specification = Specifications.get(specification)

        if not (order.status == Order.OrderStatus.ACTIVE or order.status == Order.OrderStatus.ASSEMBLING):
            raise cls.CanNotAssembleOrder()

        operator = Operators.get_operator(user)

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

    @classmethod
    def disassemble_specification(cls, order, specification, user=None):
        order = cls.get(order)
        specification = Specifications.get(specification)

        if not (order.status == Order.OrderStatus.READY or order.status == Order.OrderStatus.ASSEMBLING):
            raise cls.CanNotAssembleOrder()

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

    @classmethod
    def delete(cls, order, user):
        order = cls.get(order)
        order.delete()

    @classmethod
    def bulk_delete(cls, ids, user):
        Order.objects.filter(id__in=ids).delete()

    @classmethod
    def confirm(cls, order, user):
        order = Order.objects.get(id=order)
        if not order.status == Order.OrderStatus.READY:
            raise cls.CanNotManageAction()
        cls._confirm(order, Operators.get_operator(user))
        order.save()

    @classmethod
    def activate(cls, order, user):
        order = Order.objects.prefetch_related(
            'order_specification',
            'order_specification__specification',
            'order_specification__specification__res_specs',
            'order_specification__specification__res_specs__resource',
        ).get(id=order)

        order_specs = order.order_specification
        operator = Operators.get_operator(user)

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
                    Resources.change_amount(resource, - (res_spec.amount * (order_spec.amount - storage_amount)),
                                            operator)

                else:
                    raise cls.CanNotManageAction(f"resource {resource.name}, amount {amount}")

            specification.save()

        if not order.status == Order.OrderStatus.INACTIVE:
            raise cls.CanNotManageAction()
        cls._activate(order, Operators.get_operator(user))
        order.save()

    @classmethod
    def deactivate(cls, order, user):
        order = cls.get(order)
        operator = Operators.get_operator(user)

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
                Resources.change_amount(resource, res_spec.amount * order_spec.amount, operator)

        cls._deactivate(order, Operators.get_operator(user))
        order.save()

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
                    specifications_objects = Specification.objects.filter(
                        product_id__in=map(lambda x: x['product_id'], products), is_active=True)
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
            raise cls.CreateException(ex)
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
            operator=operator,
        )

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max, Q, Subquery, OuterRef, Exists

from .models import (Operator,
                     ResourceProvider,
                     Resource,
                     ResourceCost,
                     ResourceAmount,
                     ResourceAction)
from django.db import IntegrityError


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

    def actions(self, r_id):
        return ResourceAction.objects.filter(resource_id=r_id).order_by('-time_stamp')

    # def list(self, filtering=None, ordering=None, searching=None):
    #     # TODO: test
    #     query = Resource.objects.raw(
    #         f"""
    #             SELECT *
    #             FROM {Resource._meta.db_table} resource
    #             LEFT JOIN (
    #                 SELECT  {ResourceProvider._meta.db_table}.id AS provider_id,
    #                         {ResourceProvider._meta.db_table}.name AS provider_name
    #                 FROM {ResourceProvider._meta.db_table}
    #             ) provider
    #             ON resource.provider_id = provider.provider_id
    #             LEFT JOIN (
    #                 SELECT  o.value AS cost,
    #                         o.resource_id AS resource_id,
    #                         o.time_stamp AS cost_time_stamp
    #                 FROM {ResourceCost._meta.db_table} o
    #                 LEFT JOIN {ResourceCost._meta.db_table} b
    #                 ON o.resource_id = b.resource_id AND o.time_stamp < b.time_stamp
    #                 WHERE b.time_stamp IS NULL
    #             ) cost
    #             ON cost.resource_id = resource.id
    #             LEFT JOIN (
    #                 SELECT  o.value AS amount,
    #                         o.resource_id AS resource_id,
    #                         o.time_stamp AS amount_time_stamp
    #                 FROM {ResourceAmount._meta.db_table} o
    #                 LEFT JOIN {ResourceAmount._meta.db_table} b
    #                 ON o.resource_id = b.resource_id AND o.time_stamp < b.time_stamp
    #                 WHERE b.time_stamp IS NULL
    #             ) amount
    #             ON amount.resource_id = resource.id
    #             {f'WHERE {searching}' if searching is not None else ''}
    #             {f'ORDER BY {", ".join(ordering)}' if ordering is not None else ''}
    #             """
    #     )
    #
    #     return query

    # def unverified(self, filtering=None, ordering=None, searching=None):
    #     # TODO: test, optimize
    #     return Resource.objects.raw(
    #         f"""
    #             SELECT *
    #             FROM {Resource._meta.db_table} resource
    #             LEFT JOIN (
    #                 SELECT  {ResourceProvider._meta.db_table}.id AS provider_id,
    #                         {ResourceProvider._meta.db_table}.name AS provider_name
    #                 FROM {ResourceProvider._meta.db_table}
    #             ) provider
    #             ON resource.provider_id = provider.provider_id
    #             INNER JOIN (
    #                 SELECT  o.value AS new_cost,
    #                         o.resource_id AS resource_id
    #                 FROM {ResourceCost._meta.db_table} o
    #                 LEFT JOIN ( SELECT time_stamp, resource_id
    #                             FROM {ResourceCost._meta.db_table}
    #                             WHERE verified != TRUE) b
    #                 ON o.resource_id = b.resource_id AND o.time_stamp < b.time_stamp
    #                 WHERE b.time_stamp IS NULL AND o.verified != TRUE
    #             ) new_cost
    #             ON new_cost.resource_id = resource.id
    #             LEFT JOIN (
    #                 SELECT  o.value AS old_cost,
    #                         o.resource_id AS resource_id
    #                 FROM {ResourceCost._meta.db_table} o
    #                 LEFT JOIN {ResourceCost._meta.db_table} b
    #                 ON o.resource_id = b.resource_id AND o.time_stamp < b.time_stamp
    #                 WHERE b.time_stamp IS NULL AND o.verified = TRUE
    #             ) old_cost
    #             ON old_cost.resource_id = resource.id
    #             LEFT JOIN (
    #                 SELECT  o.value AS amount,
    #                         o.resource_id AS resource_id
    #                 FROM {ResourceAmount._meta.db_table} o
    #                 LEFT JOIN {ResourceAmount._meta.db_table} b
    #                 ON o.resource_id = b.resource_id AND o.time_stamp < b.time_stamp
    #                 WHERE b.time_stamp IS NULL
    #             ) amount
    #             ON amount.resource_id = resource.id
    #             {f'WHERE {searching}' if searching is not None else ''}
    #             {f'ORDER BY {", ".join(ordering)}' if ordering is not None else ''}
    #             """
    #     )

# @classmethod
#     def resource_list(cls):
#         a = Resource.objects.raw(f"""
#         SELECT *
#         FROM {Resource._meta.db_table}
#         LEFT JOIN (
#             SELECT o.value as storage_value, o.resource_id, o.action_datetime as storage_action_datetime
#             FROM  {ResourceStorageAction._meta.db_table} o
#             LEFT JOIN {ResourceStorageAction._meta.db_table} b
#             ON o.resource_id = b.resource_id AND o.action_datetime < b.action_datetime
#             WHERE b.action_datetime is NULL
#             ) storage_action
#         ON ({Resource._meta.db_table}.id = storage_action.resource_id)
#         LEFT JOIN (
#             SELECT o.value as price_value, o.resource_id, o.action_datetime as cost_action_datetime
#             FROM  {ResourceCostAction._meta.db_table} o
#             LEFT JOIN {ResourceCostAction._meta.db_table} b
#             ON o.resource_id = b.resource_id AND o.action_datetime < b.action_datetime
#             WHERE b.action_datetime is NULL
#             ) price_action
#         ON ({Resource._meta.db_table}.id = price_action.resource_id)
#         LEFT JOIN (
#             SELECT o.value as cost, o.resource_id, o.created_at
#             FROM {ResourceCost._meta.db_table} o
#             LEFT JOIN {ResourceCost._meta.db_table} b
#             ON o.resource_id = b.resource_id AND o.created_at < b.created_at
#             WHERE b.created_at is NULL
#             ) cost
#         ON ({Resource._meta.db_table}.id = cost.resource_id)
#         LEFT JOIN {ResourceProvider._meta.db_table}
#         ON ({ResourceProvider._meta.db_table}.id = {Resource._meta.db_table}.resource_provider_id)
#         """)
#         return a[:]
#
#     @classmethod
#     def set_new_costs(cls, external_resource_ids: list, new_costs: list, user):
#
#         format_external_ids = f"('{external_resource_ids[0]}')" if len(
#             external_resource_ids) == 1 else f"{tuple(external_resource_ids)}"
#         resources = Resource.objects.raw(f"""
#         SELECT *
#         FROM {Resource._meta.db_table}
#         LEFT JOIN (
#             SELECT o.value AS cost_value, o.resource_id, o.created_at, o.id AS cost_id
#             FROM {ResourceCost._meta.db_table} o
#             LEFT JOIN {ResourceCost._meta.db_table} b
#             ON o.resource_id = b.resource_id AND o.created_at < b.created_at
#             WHERE b.created_at IS NULL
#             ) cost
#         ON ({Resource._meta.db_table}.id = cost.resource_id)
#         LEFT JOIN (
#             SELECT o.id AS unv_cost_id, o.new_cost_id
#             FROM {UnverifiedCost._meta.db_table} o
#             ) unv_cost
#         ON (unv_cost.new_cost_id = cost.cost_id)
#         WHERE external_id IN {format_external_ids}
#         """)
#
#         operator = Operators.get_operator_by_user(user)
#
#         cost_actions = []
#         unverified_costs_create = []
#         unverified_costs_update = []
#         costs = []
#
#         for i, resource in enumerate(resources):
#             new_cost = ResourceCost(resource=resource, value=new_costs[i])
#             costs.append(new_cost)
#             new_cost.save()  # TODO: optimize
#
#             if resource.unv_cost_id is not None:
#                 unv_cost = UnverifiedCost.objects.get(id=resource.unv_cost_id)  # TODO: optimize
#                 unv_cost.new_cost = new_cost
#                 unverified_costs_update.append(unv_cost)
#             else:
#                 if resource.cost_id is not None:
#                     unv_cost = UnverifiedCost(last_verified_cost_id=resource.cost_id,
#                                               new_cost=new_cost)
#                     unverified_costs_create.append(unv_cost)
#
#             if resource.cost_id is not None:
#
#                 if new_costs[i] > resource.cost_value:
#                     action_type = ResourceCostAction.ActionType.RISE
#                 else:
#                     action_type = ResourceCostAction.ActionType.DROP
#                 value = new_costs[i] - resource.cost_value
#
#             else:
#                 action_type = ResourceCostAction.ActionType.SET
#                 value = new_costs[i]
#
#             cost_actions.append(ResourceCostAction(value=value,
#                                                    operator=operator,
#                                                    resource=resource,
#                                                    action_type=action_type))
#
#         ResourceCostAction.objects.bulk_create(cost_actions)
#         # ResourceCost.objects.bulk_create(costs)
#         if len(unverified_costs_create) != 0:
#             UnverifiedCost.objects.bulk_create(unverified_costs_create)
#         if len(unverified_costs_update) != 0:
#             UnverifiedCost.objects.bulk_update(unverified_costs_update, ['new_cost'])
#
#     @classmethod
#     def change_amount(cls, external_resource_id: list, delta_amount: list, user):
#
#         operator = Operators.get_operator_by_user(user)
#         resources = Resource.objects.filter(external_id__in=external_resource_id)
#
#         storage_actions = []
#         for i, resource in enumerate(resources):
#             resource.amount += delta_amount[i]
#             if delta_amount[i] > 0:
#                 action_type = ResourceStorageAction.ActionType.ADD
#             else:
#                 action_type = ResourceStorageAction.ActionType.REMOVE
#             storage_actions.append(ResourceStorageAction(value=delta_amount[i],
#                                                          operator=operator,
#                                                          resource=resource,
#                                                          action_type=action_type))
#
#         Resource.objects.bulk_update(resources, ['amount'])
#         ResourceStorageAction.objects.bulk_create(storage_actions)
#
#     @classmethod
#     def set_new_amounts(cls, external_resource_id: list, amounts: list, user):
#
#         operator = Operators.get_operator_by_user(user)
#         resources = Resource.objects.filter(external_id__in=external_resource_id)
#
#         storage_actions = []
#         for i, resource in enumerate(resources):
#             resource.amount = amounts[i]
#             action_type = ResourceStorageAction.ActionType.SET
#             storage_actions.append(ResourceStorageAction(value=amounts[i],
#                                                          operator=operator,
#                                                          resource=resource,
#                                                          action_type=action_type))
#
#         Resource.objects.bulk_update(resources, ['amount'])
#         ResourceStorageAction.objects.bulk_create(storage_actions)
#
#
# class Specifications:
#     Spec = namedtuple('Spec', 'name product_id name_category is_active coefficient prime_cost price')
#     SpecRes = namedtuple('SpecRes', 'name external_id provider_name amount cost_value total_cost')
#
#     @classmethod
#     def specification(cls, s_id: int):
#
#         specification = Specification.objects.select_related('category').annotate(
#             coef=Case(
#                 When(use_category_coefficient=True, then=F('category__coefficient')),
#                 default=F('coefficient')
#             )
#         ).get(id=s_id)
#
#         resources_query = ResourceSpecification.objects.raw(f"""
#         SELECT rs.amount AS amount,
#                 rp.provider_name AS provider_name,
#                 r.resource_name AS name,
#                 r.external_id AS external_id,
#                 cost.cost_value AS cost_value,
#                 rs.id
#         FROM {ResourceSpecification._meta.db_table} rs
#         INNER JOIN {Resource._meta.db_table} r
#         ON (rs.resource_id = r.id)
#         LEFT JOIN {ResourceProvider._meta.db_table} rp
#         ON (r.resource_provider_id = rp.id)
#         LEFT JOIN (
#             SELECT o.value AS cost_value, o.resource_id, o.created_at
#             FROM {ResourceCost._meta.db_table} o
#             LEFT JOIN {ResourceCost._meta.db_table} b
#             ON o.resource_id = b.resource_id AND o.created_at < b.created_at
#             WHERE b.created_at IS NULL
#             ) cost
#         ON (r.id = cost.resource_id)
#         WHERE rs.specification_id = {s_id}
#         """)
#
#         resources = list(cls.SpecRes(name=rs.name,
#                                      external_id=rs.external_id,
#                                      provider_name=rs.provider_name,
#                                      amount=rs.amount,
#                                      cost_value=rs.cost_value,
#                                      total_cost=float(rs.amount) * float(rs.cost_value)
#                                      ) for rs in resources_query)
#
#         prime_cost = sum(map(lambda x: x.total_cost, resources))
#         price = prime_cost * float(specification.coef)
#
#         if specification.category is not None:
#             category = specification.category.category_name
#         else:
#             category = 'Без категории'
#
#         spec = cls.Spec(
#             name=specification.specification_name,
#             product_id=specification.product_id,
#             name_category=category,
#             is_active=specification.is_active,
#             coefficient=specification.coef,
#             prime_cost=prime_cost,
#             price=price
#         )
#         return spec, list(resources)
#
#     @classmethod
#     def specification_create(cls,
#                              specification_name: str,
#                              product_id: str,
#                              category_name: str,
#                              coefficient: float = None,
#                              use_category_coefficient: bool = False,
#                              resources: list = None,
#                              is_active: bool = True,
#                              user=None):
#         # resources: [{id, amount}]
#         # TODO: check fields
#
#         operator = Operators.get_operator_by_user(user)
#
#         if category_name is not None:
#             category = SpecificationCategory.objects.get_or_create(category_name=category_name)[0]
#         else:
#             category = None
#         specification = Specification.objects.create(specification_name=specification_name,
#                                                      product_id=product_id,
#                                                      category=category,
#                                                      coefficient=coefficient,
#                                                      use_category_coefficient=use_category_coefficient,
#                                                      is_active=is_active)
#         res_spec = []
#
#         if resources is not None:
#             for res in resources:
#                 res_spec.append(ResourceSpecification(
#                     specification=specification,
#                     resource_id=res['id'],
#                     amount=res['amount']))
#
#         ResourceSpecification.objects.bulk_create(res_spec)
#
#         if use_category_coefficient:
#             coefficient_action_type = SpecificationCoefficientAction.ActionType.SET_BY_CATEGORY
#         else:
#             coefficient_action_type = SpecificationCoefficientAction.ActionType.SET
#
#         specification_coefficient_action = SpecificationCoefficientAction.objects.create(
#             specification=specification,
#             action_type=coefficient_action_type,
#             value=coefficient,
#             operator=operator
#         )
#
#         specification_service_action = SpecificationServiceAction.objects.create(
#             specification=specification,
#             action_type=SpecificationServiceAction.ActionType.CREATE,
#             operator=operator
#         )
#
#         specification = Specifications.specification(s_id=specification.id)
#
#         return specification, (specification_service_action, specification_coefficient_action)
#
#     @classmethod
#     def specification_edit(cls,
#                            s_id,
#                            specification_name: str,
#                            product_id: str,
#                            category_name: str,
#                            coefficient: float = None,
#                            use_category_coefficient: bool = False,
#                            resources: list = None,
#                            is_active: bool = True,
#                            user=None):
#         ...
#
#     @classmethod
#     def specification_delete(cls, s_id):
#         ...
#
#     @classmethod
#     def specification_deactivate(cls, s_id):
#         ...
#
#     @classmethod
#     def specification_list(cls):
#         return Specification.objects.raw(
#             f"""
#             SELECT s.id AS id,
#                     s.specification_name AS name,
#                     s.product_id AS product_id,
#                     CASE
#                         WHEN s.category_id is not NULL THEN sc.category_name
#                         ELSE 'Без категории'
#                     END AS name_category,
#                     s.is_active AS is_active,
#                     SUM(c.cost_value * rs.amount) as prime_cost,
#                     CASE
#                         WHEN s.use_category_coefficient = TRUE THEN sc.coefficient
#                         ELSE s.coefficient
#                     END AS coefficient,
#                     CASE
#                         WHEN s.use_category_coefficient = TRUE THEN sc.coefficient
#                         ELSE s.coefficient
#                     END * SUM(c.cost_value * rs.amount) as total_cost
#             FROM {Specification._meta.db_table} s
#             LEFT JOIN {SpecificationCategory._meta.db_table}  sc
#             ON (s.category_id = sc.id)
#             LEFT JOIN {ResourceSpecification._meta.db_table} rs
#             ON (rs.specification_id = s.id)
#             LEFT JOIN {Resource._meta.db_table} r
#             ON (r.id = rs.resource_id)
#             LEFT JOIN (
#                 SELECT o.value AS cost_value, o.resource_id, o.created_at
#                 FROM {ResourceCost._meta.db_table} o
#                 LEFT JOIN {ResourceCost._meta.db_table} b
#                 ON o.resource_id = b.resource_id AND o.created_at < b.created_at
#                 WHERE b.created_at IS NULL
#                 ) c
#             ON (r.id = c.resource_id)
#             GROUP BY s.id
#             """)[:]
#
#     @classmethod
#     def specification_capture(cls, s_id):
#         ...
#
#
# class Verify:
#
#     @classmethod
#     def unverified_resources(cls):
#         resources = Resource.objects.raw(f"""
#         SELECT *
#         FROM {UnverifiedCost._meta.db_table} uc
#         INNER JOIN (
#             SELECT rc.id AS old_cost_id, rc.value AS old_cost_value, rc.resource_id AS resource_id
#             FROM {ResourceCost._meta.db_table} rc
#             ) rc_old
#         ON (uc.last_verified_cost_id = rc_old.old_cost_id)
#         INNER JOIN (
#             SELECT rc.id as new_cost_id, rc.value AS new_cost_value
#             FROM {ResourceCost._meta.db_table} rc
#             ) rc_new
#         ON (uc.new_cost_id = rc_new.new_cost_id)
#         INNER JOIN {Resource._meta.db_table} r
#         ON (r.id = rc_old.resource_id)
#         """)
#         return resources
#
#     @classmethod
#     def unverified_specifications(cls):
#         # TODO: today
#         specifications = Specification.objects.raw(
#             f"""
#         SELECT  spec.id AS id,
#                 spec.specification_name as specification_name,
#                 spec.category_name as category_name,
#                 spec.coefficient as coefficient,
#                 spec.product_id as product_id,
#                 SUM(
#                     CASE
#                         WHEN res_spec.old_cost IS NOT NULL THEN res_spec.old_cost
#                         ELSE res_spec.new_cost
#                     END) as old_cost,
#                 SUM(res_spec.new_cost) as new_cost,
#                 SUM(CASE
#                         WHEN res_spec.old_cost IS NOT NULL THEN res_spec.old_cost
#                         ELSE res_spec.new_cost
#                     END) * spec.coefficient AS old_price,
#                 SUM(res_spec.new_cost) * spec.coefficient AS new_price
#         FROM (
#             SELECT  s.id as id,
#                     s.specification_name AS specification_name,
#                     s.product_id AS product_id,
#                     sc.category_name AS category_name,
#                     CASE
#                         WHEN s.use_category_coefficient = TRUE THEN sc.coefficient
#                         ELSE s.coefficient
#                     END AS coefficient
#             FROM {Specification._meta.db_table} s
#             LEFT JOIN {SpecificationCategory._meta.db_table} sc
#             ON (s.category_id = sc.id)
#             INNER JOIN {ResourceSpecification._meta.db_table} rs
#             ON (s.id = rs.specification_id)
#             INNER JOIN (
#                 SELECT r.id as res_id
#                 FROM {UnverifiedCost._meta.db_table} uc
#                 INNER JOIN (
#                     SELECT rc.id AS old_cost_id, rc.value AS old_cost_value, rc.resource_id AS resource_id
#                     FROM {ResourceCost._meta.db_table} rc
#                     ) rc_old
#                 ON (uc.last_verified_cost_id = rc_old.old_cost_id)
#                 INNER JOIN (
#                     SELECT rc.id as new_cost_id, rc.value AS new_cost_value
#                     FROM {ResourceCost._meta.db_table} rc
#                     ) rc_new
#                 ON (uc.new_cost_id = rc_new.new_cost_id)
#                 INNER JOIN {Resource._meta.db_table} r
#                 ON (r.id = rc_old.resource_id)
#             ) unv_res
#             ON (unv_res.res_id = rs.resource_id)
#             GROUP BY s.id
#         ) spec
#         LEFT JOIN (
#             SELECT  rs.specification_id AS specification_id,
#                     c.id as cost_id,
#                     uc.old_cost AS old_cost,
#                     c.cost_value AS new_cost
#             FROM {ResourceSpecification._meta.db_table} rs
#             LEFT JOIN {Resource._meta.db_table} r
#             ON (r.id = rs.resource_id)
#             LEFT JOIN (
#                 SELECT o.value AS cost_value, o.resource_id, o.created_at, o.id as id
#                 FROM {ResourceCost._meta.db_table} o
#                 LEFT JOIN {ResourceCost._meta.db_table} b
#                 ON o.resource_id = b.resource_id AND o.created_at < b.created_at
#                 WHERE b.created_at IS NULL
#                 ) c
#             ON (r.id = c.resource_id)
#             LEFT JOIN (
#                 SELECT  rc.value as old_cost,
#                         uc.new_cost_id AS new_cost_id
#                 FROM {UnverifiedCost._meta.db_table} uc
#                 INNER JOIN {ResourceCost._meta.db_table} rc
#                 ON (rc.id = uc.last_verified_cost_id)
#             ) uc
#             ON (uc.new_cost_id = c.id)
#         ) res_spec
#         ON (res_spec.specification_id = spec.id)
#         GROUP BY spec.id
#         """)
#         return specifications

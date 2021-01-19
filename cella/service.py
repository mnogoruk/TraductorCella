from .models import (
    Resource,
    ResourceStorageAction,
    ResourceCostAction,
    ResourceServiceAction,
    ResourceProvider,
    ResourceCost,
    UnverifiedCost,
    Operator,
    Specification,
    SpecificationCategory,
    SpecificationServiceAction,
    SpecificationCoefficientAction,
    SpecificationCaptureAction,
    ResourceSpecification,
)
from django.db.models import Q, FilteredRelation, Max, F, Case, When, Sum
from collections import namedtuple
from django.db import connection


class Operators:

    @classmethod
    def get_operator_by_user(cls, user):
        if user is None:
            operator = Operator.get_service_operator()
        elif user.is_anonymous:
            operator = Operator.get_anonymous_operator()
        else:
            operator = Operator.get_user_operator(user)
        return operator


class Resources:

    @classmethod
    def resource(cls, r_id):
        resource = Resource.objects.select_related('resource_provider').get(id=r_id)
        resource.cost = ResourceCost.objects.filter(resource=resource).latest('created_at').value
        with connection.cursor() as cursor:
            cursor.execute(f"""
             SELECT action_type, action_datetime, value, 'price' AS action
             FROM {ResourceCostAction._meta.db_table}
             WHERE resource_id = {resource.id}
            UNION
             SELECT action_type, action_datetime, value, 'storage' AS action
             FROM {ResourceStorageAction._meta.db_table}
             WHERE resource_id = {resource.id}
            UNION
             SELECT action_type, action_datetime, NULL AS value, 'service' AS action
             FROM {ResourceServiceAction._meta.db_table}
             WHERE resource_id = {resource.id}
            ORDER BY action_datetime
            """)
            return cursor.fetchall(), resource

    @classmethod
    def resource_create(cls,
                        resource_name: str,
                        external_id: str,
                        cost: float,
                        amount: float = 0,
                        provider_name: str = None,
                        user=None):

        if provider_name is not None:
            provider = ResourceProvider.objects.get_or_create(provider_name=provider_name)[0]
        else:
            provider = None

        # TODO: check fields

        operator = Operators.get_operator_by_user(user)

        resource = Resource.objects.create(resource_name=resource_name,
                                           external_id=external_id,
                                           amount=amount,
                                           resource_provider=provider)

        cost_value = ResourceCost.objects.create(resource=resource, value=cost).value

        resource_cost_action = ResourceCostAction.objects.create(
            resource=resource,
            action_type=ResourceCostAction.ActionType.SET,
            value=cost,
            operator=operator
        )
        resource_storage_action = ResourceStorageAction.objects.create(
            resource=resource,
            action_type=ResourceStorageAction.ActionType.SET,
            value=amount,
            operator=operator
        )
        resource_service_action = ResourceServiceAction.objects.create(
            resource=resource,
            action_type=ResourceServiceAction.ActionType.CREATE,
            operator=operator
        )

        resource.cost = cost_value
        return resource, (resource_cost_action, resource_storage_action, resource_service_action)

    @classmethod
    def resource_edit(cls,
                      r_id,
                      resource_name=None,
                      external_id=None,
                      cost: float = None,
                      amount: float = None,
                      provider_name: str = None,
                      user=None):
        # TODO: check fields
        data = dict()
        if resource_name is not None:
            data['resource_name'] = resource_name
        if external_id is not None:
            data['external_id'] = external_id
        if provider_name is not None:
            data['resource_provider'] = ResourceProvider.objects.get_or_create(provider_name=provider_name)[0]
        if amount is not None:
            data['amount'] = amount

        Resource.objects.filter(id=r_id).update(**data)

        if cost is not None:
            Resources.set_new_costs([external_id], [cost], user=user)

        if amount is not None:
            Resources.set_new_amounts([external_id], [cost], user=user)

    @classmethod
    def resource_delete(cls, r_id):
        Resource.objects.get(id=r_id).delete()

    @classmethod
    def resource_list(cls):
        a = Resource.objects.raw(f"""
        SELECT *  
        FROM {Resource._meta.db_table} 
        LEFT JOIN (
            SELECT o.value as storage_value, o.resource_id, o.action_datetime as storage_action_datetime
            FROM  {ResourceStorageAction._meta.db_table} o
            LEFT JOIN {ResourceStorageAction._meta.db_table} b
            ON o.resource_id = b.resource_id AND o.action_datetime < b.action_datetime
            WHERE b.action_datetime is NULL
            ) storage_action
        ON ({Resource._meta.db_table}.id = storage_action.resource_id)
        LEFT JOIN (
            SELECT o.value as price_value, o.resource_id, o.action_datetime as cost_action_datetime
            FROM  {ResourceCostAction._meta.db_table} o
            LEFT JOIN {ResourceCostAction._meta.db_table} b
            ON o.resource_id = b.resource_id AND o.action_datetime < b.action_datetime
            WHERE b.action_datetime is NULL
            ) price_action
        ON ({Resource._meta.db_table}.id = price_action.resource_id)
        LEFT JOIN (
            SELECT o.value as cost, o.resource_id, o.created_at
            FROM {ResourceCost._meta.db_table} o
            LEFT JOIN {ResourceCost._meta.db_table} b
            ON o.resource_id = b.resource_id AND o.created_at < b.created_at
            WHERE b.created_at is NULL
            ) cost
        ON ({Resource._meta.db_table}.id = cost.resource_id)
        LEFT JOIN {ResourceProvider._meta.db_table} 
        ON ({ResourceProvider._meta.db_table}.id = {Resource._meta.db_table}.resource_provider_id)
        """)
        return a[:]

    @classmethod
    def set_new_costs(cls, external_resource_ids: list, new_costs: list, user):

        format_external_ids = f"('{external_resource_ids[0]}')" if len(
            external_resource_ids) == 1 else f"{tuple(external_resource_ids)}"
        resources = Resource.objects.raw(f"""
        SELECT *  
        FROM {Resource._meta.db_table} 
        LEFT JOIN (
            SELECT o.value AS cost_value, o.resource_id, o.created_at, o.id AS cost_id
            FROM {ResourceCost._meta.db_table} o
            LEFT JOIN {ResourceCost._meta.db_table} b
            ON o.resource_id = b.resource_id AND o.created_at < b.created_at
            WHERE b.created_at IS NULL
            ) cost
        ON ({Resource._meta.db_table}.id = cost.resource_id)
        LEFT JOIN (
            SELECT o.id AS unv_cost_id, o.new_cost_id
            FROM {UnverifiedCost._meta.db_table} o
            ) unv_cost
        ON (unv_cost.new_cost_id = cost.cost_id)
        WHERE external_id IN {format_external_ids}
        """)

        operator = Operators.get_operator_by_user(user)

        cost_actions = []
        unverified_costs_create = []
        unverified_costs_update = []
        costs = []

        for i, resource in enumerate(resources):
            new_cost = ResourceCost(resource=resource, value=new_costs[i])
            costs.append(new_cost)
            new_cost.save()  # TODO: optimize

            if resource.unv_cost_id is not None:
                unv_cost = UnverifiedCost.objects.get(id=resource.unv_cost_id)  # TODO: optimize
                unv_cost.new_cost = new_cost
                unverified_costs_update.append(unv_cost)
            else:
                if resource.cost_id is not None:
                    unv_cost = UnverifiedCost(last_verified_cost_id=resource.cost_id,
                                              new_cost=new_cost)
                    unverified_costs_create.append(unv_cost)

            if resource.cost_id is not None:

                if new_costs[i] > resource.cost_value:
                    action_type = ResourceCostAction.ActionType.RISE
                else:
                    action_type = ResourceCostAction.ActionType.DROP
                value = new_costs[i] - resource.cost_value

            else:
                action_type = ResourceCostAction.ActionType.SET
                value = new_costs[i]

            cost_actions.append(ResourceCostAction(value=value,
                                                   operator=operator,
                                                   resource=resource,
                                                   action_type=action_type))

        ResourceCostAction.objects.bulk_create(cost_actions)
        # ResourceCost.objects.bulk_create(costs)
        if len(unverified_costs_create) != 0:
            UnverifiedCost.objects.bulk_create(unverified_costs_create)
        if len(unverified_costs_update) != 0:
            UnverifiedCost.objects.bulk_update(unverified_costs_update, ['new_cost'])

    @classmethod
    def change_amount(cls, external_resource_id: list, delta_amount: list, user):

        operator = Operators.get_operator_by_user(user)
        resources = Resource.objects.filter(external_id__in=external_resource_id)

        storage_actions = []
        for i, resource in enumerate(resources):
            resource.amount += delta_amount[i]
            if delta_amount[i] > 0:
                action_type = ResourceStorageAction.ActionType.ADD
            else:
                action_type = ResourceStorageAction.ActionType.REMOVE
            storage_actions.append(ResourceStorageAction(value=delta_amount[i],
                                                         operator=operator,
                                                         resource=resource,
                                                         action_type=action_type))

        Resource.objects.bulk_update(resources, ['amount'])
        ResourceStorageAction.objects.bulk_create(storage_actions)

    @classmethod
    def set_new_amounts(cls, external_resource_id: list, amounts: list, user):

        operator = Operators.get_operator_by_user(user)
        resources = Resource.objects.filter(external_id__in=external_resource_id)

        storage_actions = []
        for i, resource in enumerate(resources):
            resource.amount = amounts[i]
            action_type = ResourceStorageAction.ActionType.SET
            storage_actions.append(ResourceStorageAction(value=amounts[i],
                                                         operator=operator,
                                                         resource=resource,
                                                         action_type=action_type))

        Resource.objects.bulk_update(resources, ['amount'])
        ResourceStorageAction.objects.bulk_create(storage_actions)


class Specifications:
    Spec = namedtuple('Spec', 'name product_id name_category is_active coefficient prime_cost price')
    SpecRes = namedtuple('SpecRes', 'name external_id provider_name amount cost_value total_cost')

    @classmethod
    def specification(cls, s_id: int):

        specification = Specification.objects.select_related('category').annotate(
            coef=Case(
                When(use_category_coefficient=True, then=F('category__coefficient')),
                default=F('coefficient')
            )
        ).get(id=s_id)

        resources_query = ResourceSpecification.objects.raw(f"""
        SELECT rs.amount AS amount,
                rp.provider_name AS provider_name,
                r.resource_name AS name, 
                r.external_id AS external_id,
                cost.cost_value AS cost_value,
                rs.id
        FROM {ResourceSpecification._meta.db_table} rs
        INNER JOIN {Resource._meta.db_table} r
        ON (rs.resource_id = r.id)
        LEFT JOIN {ResourceProvider._meta.db_table} rp
        ON (r.resource_provider_id = rp.id)
        LEFT JOIN (
            SELECT o.value AS cost_value, o.resource_id, o.created_at
            FROM {ResourceCost._meta.db_table} o
            LEFT JOIN {ResourceCost._meta.db_table} b
            ON o.resource_id = b.resource_id AND o.created_at < b.created_at
            WHERE b.created_at IS NULL
            ) cost
        ON (r.id = cost.resource_id)
        WHERE rs.specification_id = {s_id}
        """)

        resources = list(cls.SpecRes(name=rs.name,
                                     external_id=rs.external_id,
                                     provider_name=rs.provider_name,
                                     amount=rs.amount,
                                     cost_value=rs.cost_value,
                                     total_cost=float(rs.amount) * float(rs.cost_value)
                                     ) for rs in resources_query)

        prime_cost = sum(map(lambda x: x.total_cost, resources))
        price = prime_cost * float(specification.coef)

        if specification.category is not None:
            category = specification.category.category_name
        else:
            category = 'Без категории'

        spec = cls.Spec(
            name=specification.specification_name,
            product_id=specification.product_id,
            name_category=category,
            is_active=specification.is_active,
            coefficient=specification.coef,
            prime_cost=prime_cost,
            price=price
        )
        return spec, list(resources)

    @classmethod
    def specification_create(cls,
                             specification_name: str,
                             product_id: str,
                             category_name: str,
                             coefficient: float = None,
                             use_category_coefficient: bool = False,
                             resources: list = None,
                             is_active: bool = True,
                             user=None):
        # resources: [{id, amount}]
        # TODO: check fields

        operator = Operators.get_operator_by_user(user)

        if category_name is not None:
            category = SpecificationCategory.objects.get_or_create(category_name=category_name)
        else:
            category = None
        specification = Specification.objects.create(specification_name=specification_name,
                                                     product_id=product_id,
                                                     category=category,
                                                     coefficient=coefficient,
                                                     use_category_coefficient=use_category_coefficient,
                                                     is_active=is_active)
        res_spec = []

        if resources is not None:
            for res in resources:
                res_spec.append(ResourceSpecification(
                    specification=specification,
                    resource_id=res['id'],
                    amount=res['amount']))

        ResourceSpecification.objects.bulk_create(res_spec)

        if use_category_coefficient:
            coefficient_action_type = SpecificationCoefficientAction.ActionType.SET_BY_CATEGORY
        else:
            coefficient_action_type = SpecificationCoefficientAction.ActionType.SET

        specification_coefficient_action = SpecificationCoefficientAction.objects.create(
            specification=specification,
            action_type=coefficient_action_type,
            value=coefficient,
            operator=operator
        )

        specification_service_action = SpecificationServiceAction.objects.create(
            specification=specification,
            action_type=SpecificationServiceAction.ActionType.CREATE,
            operator=operator
        )

        specification = Specifications.specification(s_id=specification.id)

        return specification, (specification_service_action, specification_coefficient_action)

    @classmethod
    def specification_edit(cls,
                           s_id,
                           specification_name: str,
                           product_id: str,
                           category_name: str,
                           coefficient: float = None,
                           use_category_coefficient: bool = False,
                           resources: list = None,
                           is_active: bool = True,
                           user=None):
        ...

    @classmethod
    def specification_delete(cls, s_id):
        ...

    @classmethod
    def specification_deactivate(cls, s_id):
        ...

    @classmethod
    def specification_list(cls):
        return Specification.objects.raw(
            f"""
            SELECT s.id AS id,
                    s.specification_name AS name, 
                    s.product_id AS product_id,
                    CASE 
                        WHEN s.category_id is not NULL THEN sc.category_name
                        ELSE 'Без категории'
                    END AS name_category,
                    s.is_active AS is_active,
                    SUM(c.cost_value * rs.amount) as prime_cost,
                    CASE
                        WHEN s.use_category_coefficient = TRUE THEN sc.coefficient
                        ELSE s.coefficient
                    END AS coefficient,
                    CASE
                        WHEN s.use_category_coefficient = TRUE THEN sc.coefficient
                        ELSE s.coefficient
                    END * SUM(c.cost_value * rs.amount) as total_cost
            FROM {Specification._meta.db_table} s
            LEFT JOIN {SpecificationCategory._meta.db_table}  sc
            ON (s.category_id = sc.id)
            LEFT JOIN {ResourceSpecification._meta.db_table} rs
            ON (rs.specification_id = s.id)
            LEFT JOIN {Resource._meta.db_table} r
            ON (r.id = rs.resource_id)
            LEFT JOIN (
                SELECT o.value AS cost_value, o.resource_id, o.created_at
                FROM {ResourceCost._meta.db_table} o
                LEFT JOIN {ResourceCost._meta.db_table} b
                ON o.resource_id = b.resource_id AND o.created_at < b.created_at
                WHERE b.created_at IS NULL
                ) c
            ON (r.id = c.resource_id)
            GROUP BY s.id
            """)[:]

    @classmethod
    def specification_capture(cls, s_id):
        ...


class Verify:

    @classmethod
    def unverified_resources(cls):
        resources = Resource.objects.raw(f"""
        SELECT * 
        FROM {UnverifiedCost._meta.db_table} uc
        INNER JOIN (
            SELECT rc.id AS old_cost_id, rc.value AS old_cost_value, rc.resource_id AS resource_id
            FROM {ResourceCost._meta.db_table} rc
            ) rc_old
        ON (uc.last_verified_cost_id = rc_old.old_cost_id)
        INNER JOIN (
            SELECT rc.id as new_cost_id, rc.value AS new_cost_value
            FROM {ResourceCost._meta.db_table} rc
            ) rc_new
        ON (uc.new_cost_id = rc_new.new_cost_id)
        INNER JOIN {Resource._meta.db_table} r
        ON (r.id = rc_old.resource_id)
        """)
        return resources

    @classmethod
    def unverified_specifications(cls):
        # TODO: today
        return Specification.objects.raw(
            f"""
        SELECT *
        FROM {Specification._meta.db_table} s
        INNER JOIN {ResourceSpecification._meta.db_table} rs
        ON (s.id = rs.specifiaction_id)
        INNER JOIN ({cls.unverified_resources()}) unv_res
        ON (unv_res.id = rs.resource_id)"""
        )

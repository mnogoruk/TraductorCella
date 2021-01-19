from .models import (
    Resource,
    StorageAction,
    CostAction,
    ServiceAction,
    ResourceProvider,
    ResourceCost,
    UnverifiedCost,
    Operator,
    Specification,
    SpecificationCategory,
    ResourceSpecification,
    SpecificationAction,
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
             FROM {CostAction._meta.db_table}
             WHERE resource_id = {resource.id}
            UNION
             SELECT action_type, action_datetime, value, 'storage' AS action
             FROM {StorageAction._meta.db_table}
             WHERE resource_id = {resource.id}
            UNION
             SELECT action_type, action_datetime, NULL AS value, 'service' AS action
             FROM {ServiceAction._meta.db_table}
             WHERE resource_id = {resource.id}
            ORDER BY action_datetime
            """)
            return cursor.fetchall(), resource

    @classmethod
    def resource_create(cls, data):
        ...

    @classmethod
    def resource_edit(cls, r_id, data):
        ...

    @classmethod
    def resource_list(cls):
        a = Resource.objects.raw(f"""
        SELECT *  
        FROM {Resource._meta.db_table} 
        LEFT JOIN (
            SELECT o.value as storage_value, o.resource_id, o.action_datetime as storage_action_datetime
            FROM  {StorageAction._meta.db_table} o
            LEFT JOIN {StorageAction._meta.db_table} b
            ON o.resource_id = b.resource_id AND o.action_datetime < b.action_datetime
            WHERE b.action_datetime is NULL
            ) storage_action
        ON ({Resource._meta.db_table}.id = storage_action.resource_id)
        LEFT JOIN (
            SELECT o.value as price_value, o.resource_id, o.action_datetime as cost_action_datetime
            FROM  {CostAction._meta.db_table} o
            LEFT JOIN {CostAction._meta.db_table} b
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
    def set_new_costs(cls, external_resource_ids: list, new_prices: list, user):

        format_external_ids = f"({external_resource_ids[0]})" if len(
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
            new_cost = ResourceCost(resource=resource, value=new_prices[i])
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

                if new_prices[i] > resource.cost_value:
                    action_type = CostAction.ActionType.RISE
                else:
                    action_type = CostAction.ActionType.DROP
                value = new_prices[i] - resource.cost_value

            else:
                action_type = CostAction.ActionType.SET
                value = new_prices[i]

            cost_actions.append(CostAction(value=value,
                                           operator=operator,
                                           resource=resource,
                                           action_type=action_type))

        CostAction.objects.bulk_create(cost_actions)
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
                action_type = StorageAction.ActionType.ADD
            else:
                action_type = StorageAction.ActionType.REMOVE
            storage_actions.append(StorageAction(value=delta_amount[i],
                                                 operator=operator,
                                                 resource=resource,
                                                 action_type=action_type))

        Resource.objects.bulk_update(resources, ['amount'])
        StorageAction.objects.bulk_create(storage_actions)


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
    def specification_create(cls, data):
        ...

    @classmethod
    def specification_edit(cls, s_id, data):
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

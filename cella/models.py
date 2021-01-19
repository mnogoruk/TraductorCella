from django.contrib.auth import get_user_model
from django.db import models


# Create your models here.

class CreateGenericModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    # created_by = models.ForeignKey("Operator", on_delete=models.SET_NULL, null=True)

    class Meta:
        abstract = True


class UpdateGenericModel(models.Model):
    updated_at = models.DateTimeField(auto_now=True)

    # updated_by = models.ForeignKey("Operator", on_delete=models.SET_NULL, null=True)

    class Meta:
        abstract = True


class Operator(models.Model):
    is_service = models.BooleanField(default=False)
    user = models.OneToOneField(get_user_model(), on_delete=models.SET_NULL, null=True, related_name='operator',
                                blank=True)
    is_anonymous = models.BooleanField(default=False)

    def __str__(self):
        if self.is_service:
            return 'service'
        else:
            return getattr(self.user, 'username', 'anonymous')

    @classmethod
    def get_service_operator(cls):
        return Operator.objects.get_or_create(is_service=True)[0]

    @classmethod
    def get_anonymous_operator(cls):
        return Operator.objects.get_or_create(is_anonymous=True)[0]

    @classmethod
    def get_user_operator(cls, user):
        return Operator.objects.get_or_create(user=user)[0]


class ResourceProvider(models.Model):
    provider_name = models.CharField(max_length=100)

    def __str__(self):
        return self.provider_name


class Resource(CreateGenericModel, UpdateGenericModel):
    resource_provider = models.ForeignKey(ResourceProvider, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='resources')
    resource_name = models.CharField(max_length=100)
    external_id = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.resource_name} - {self.external_id}"


class ResourceCost(CreateGenericModel):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f'{self.resource.resource_name} - {self.value}'


class UnverifiedCost(models.Model):
    last_verified_cost = models.ForeignKey(ResourceCost, on_delete=models.CASCADE,
                                           related_name='unverified_cost_as_old')
    new_cost = models.ForeignKey(ResourceCost, on_delete=models.CASCADE, related_name='unverified_cost_as_new')

    def __str__(self):
        return f"{self.last_verified_cost.resource.resource_name} from {self.last_verified_cost.value} to {self.new_cost.value}"


class StorageAction(models.Model):
    class ActionType(models.TextChoices):
        ADD = 'ADD', 'Add'
        REMOVE = 'RMV', 'Remove'

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='storage_actions')
    action_type = models.CharField(max_length=3, choices=ActionType.choices)
    action_datetime = models.DateTimeField(auto_now_add=True)
    value = models.DecimalField(max_digits=8, decimal_places=2)
    operator = models.ForeignKey(Operator, on_delete=models.SET_NULL, null=True, related_name='storage_actions')

    def __str__(self):
        return f"{self.action_type} for {self.resource}"


class CostAction(models.Model):
    class ActionType(models.TextChoices):
        RISE = 'RSE', 'Rise'
        DROP = 'DRP', 'Drop'
        SET = 'SET', 'Set'

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='price_actions')
    action_type = models.CharField(max_length=3, choices=ActionType.choices)
    action_datetime = models.DateTimeField(auto_now_add=True)
    value = models.DecimalField(max_digits=8, decimal_places=2)
    operator = models.ForeignKey(Operator, on_delete=models.SET_NULL, null=True, related_name='price_actions')

    def __str__(self):
        return f"{self.action_type} for {self.resource}"


class ServiceAction(models.Model):
    class ActionType(models.TextChoices):
        CREATE = 'CRT', 'Create'
        DEACTIVATE = 'DCT', 'Deactivate'

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='service_actions')
    action_type = models.CharField(max_length=3, choices=ActionType.choices)
    action_datetime = models.DateTimeField(auto_now_add=True)
    operator = models.ForeignKey(Operator, on_delete=models.SET_NULL, null=True, related_name='service_actions')

    def __str__(self):
        return f"{self.action_type} for {self.resource}"


class SpecificationCategory(CreateGenericModel, UpdateGenericModel):
    category_name = models.CharField(max_length=100)
    coefficient = models.DecimalField(max_digits=8, decimal_places=3)

    def __str__(self):
        return self.category_name


class Specification(CreateGenericModel, UpdateGenericModel):
    specification_name = models.CharField(max_length=100)
    product_id = models.CharField(max_length=50)
    category = models.ForeignKey(SpecificationCategory, on_delete=models.SET_NULL, null=True,
                                 related_name='specifications', blank=True)
    coefficient = models.DecimalField(max_digits=8, decimal_places=3, blank=True, null=True)
    use_category_coefficient = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.specification_name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['product_id'],
                condition=models.Q(is_active=True),
                name='%(app_label)s_%(class)s_unique_active_product'
            ),
            models.CheckConstraint(
                check=(
                        (models.Q(use_category_coefficient=True) &
                         models.Q(category__isnull=False) &
                         models.Q(coefficient__isnull=True)) |
                        (models.Q(use_category_coefficient=False) &
                         models.Q(category__isnull=True) &
                         models.Q(coefficient__isnull=False))
                ),
                name='%(app_label)s_%(class)s_check_coefficient'
            ),
        ]


class ResourceSpecification(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.SET_NULL, null=True)
    specification = models.ForeignKey(Specification, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=8, decimal_places=3)

    def __str__(self):
        return f"{self.resource.resource_name} - {self.specification.specification_name}"


class SpecificationAction(models.Model):
    specification = models.ForeignKey(Specification, on_delete=models.CASCADE, related_name='specification_actions')
    old_price = models.DecimalField(max_digits=8, decimal_places=2)
    new_price = models.DecimalField(max_digits=8, decimal_places=2, null=True)

    @property
    def delta_price(self):
        if self.old_price is not None:
            return self.new_price - self.old_price
        else:
            return 0

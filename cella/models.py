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
    user = models.OneToOneField(get_user_model(),
                                on_delete=models.SET_NULL,
                                related_name='operator',
                                null=True,
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
    resource_provider = models.ForeignKey(ResourceProvider,
                                          on_delete=models.SET_NULL,
                                          related_name='resources',
                                          null=True,
                                          blank=True)
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


class ResourceStorageAction(models.Model):
    class ActionType(models.TextChoices):
        ADD = 'ADD', 'Add'
        REMOVE = 'RMV', 'Remove'
        SET = 'SET', 'Set'

    resource = models.ForeignKey(Resource,
                                 on_delete=models.CASCADE,
                                 related_name='resource_storage_actions')
    action_type = models.CharField(max_length=3, choices=ActionType.choices)
    action_datetime = models.DateTimeField(auto_now_add=True)
    value = models.DecimalField(max_digits=8, decimal_places=2)
    operator = models.ForeignKey(Operator,
                                 on_delete=models.SET_NULL,
                                 related_name='resource_storage_actions',
                                 null=True)

    def __str__(self):
        return f"{self.action_type} for {self.resource}"


class ResourceCostAction(models.Model):
    class ActionType(models.TextChoices):
        RISE = 'RSE', 'Rise'
        DROP = 'DRP', 'Drop'
        SET = 'SET', 'Set'

    resource = models.ForeignKey(Resource,
                                 on_delete=models.CASCADE,
                                 related_name='resource_cost_actions')
    action_type = models.CharField(max_length=3, choices=ActionType.choices)
    action_datetime = models.DateTimeField(auto_now_add=True)
    value = models.DecimalField(max_digits=8, decimal_places=2)
    operator = models.ForeignKey(Operator,
                                 on_delete=models.SET_NULL,
                                 related_name='resource_cost_actions',
                                 null=True)

    def __str__(self):
        return f"{self.action_type} for {self.resource}"


class ResourceServiceAction(models.Model):
    class ActionType(models.TextChoices):
        CREATE = 'CRT', 'Create'
        DEACTIVATE = 'DCT', 'Deactivate'

    resource = models.ForeignKey(Resource,
                                 on_delete=models.CASCADE,
                                 related_name='resource_service_actions')
    action_type = models.CharField(max_length=3, choices=ActionType.choices)
    action_datetime = models.DateTimeField(auto_now_add=True)
    operator = models.ForeignKey(Operator,
                                 on_delete=models.SET_NULL,
                                 related_name='resource_service_actions',
                                 null=True)

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
    category = models.ForeignKey(SpecificationCategory,
                                 on_delete=models.SET_NULL,
                                 related_name='specifications',
                                 null=True,
                                 blank=True)
    coefficient = models.DecimalField(max_digits=8,
                                      decimal_places=3,
                                      null=True,
                                      blank=True)
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
                         models.Q(category_id__isnull=False) &
                         models.Q(coefficient__isnull=True)) |
                        (models.Q(use_category_coefficient=False) &
                         models.Q(category_id__isnull=True) &
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


class SpecificationCoefficientAction(models.Model):
    class ActionType(models.TextChoices):
        RISE = 'RSE', 'Rise'
        DROP = 'DRP', 'Drop'
        SET = 'SET', 'Set'
        SET_BY_CATEGORY = 'SBC', 'Set by category'

    specification = models.ForeignKey(Specification,
                                      on_delete=models.SET_NULL,
                                      related_name='specification_coefficient_actions',
                                      null=True)
    action_type = models.CharField(max_length=3,
                                   choices=ActionType.choices)
    value = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    action_datetime = models.DateTimeField(auto_now_add=True)
    operator = models.ForeignKey(Operator,
                                 on_delete=models.SET_NULL,
                                 related_name='specification_coefficient_actions',
                                 null=True, )

    def __str__(self):
        return f"{self.action_type} for {self.specification}"


class SpecificationCaptureAction(models.Model):
    class ActionType(models.TextChoices):
        CAPTURE = 'CPT', 'Capture'
        RETURN = 'RTN', 'Return'

    specification = models.ForeignKey(Specification,
                                      on_delete=models.SET_NULL,
                                      related_name='specification_capture_actions',
                                      null=True)
    action_type = models.CharField(max_length=3, choices=ActionType.choices)
    value = models.DecimalField(max_digits=8, decimal_places=2)
    action_datetime = models.DateTimeField(auto_now_add=True)
    operator = models.ForeignKey(Operator,
                                 on_delete=models.SET_NULL,
                                 related_name='specification_capture_actions',
                                 null=True)

    def __str__(self):
        return f"{self.action_type} for {self.specification}"


class SpecificationServiceAction(models.Model):
    class ActionType(models.TextChoices):
        CREATE = 'CRT', 'Create'
        DEACTIVATE = 'DCT', 'Deactivate'
        ACTIVATE = 'ACT', 'Activate'
        DELETE = 'DLT', 'Delete'

    specification = models.ForeignKey(Specification,
                                      on_delete=models.SET_NULL,
                                      related_name='specification_service_actions',
                                      null=True)
    action_type = models.CharField(max_length=3, choices=ActionType.choices)
    action_datetime = models.DateTimeField(auto_now_add=True)
    operator = models.ForeignKey(Operator,
                                 on_delete=models.SET_NULL,
                                 related_name='specification_service_actions',
                                 null=True)

    def __str__(self):
        return f"{self.action_type} for {self.specification}"


class UnverifiedCost(models.Model):
    last_verified_cost = models.ForeignKey(ResourceCost,
                                           on_delete=models.CASCADE,
                                           related_name='unverified_cost_as_old')
    new_cost = models.ForeignKey(ResourceCost,
                                 on_delete=models.CASCADE,
                                 related_name='unverified_cost_as_new')

    def __str__(self):
        return f"{self.last_verified_cost.resource.resource_name} from {self.last_verified_cost.value} to {self.new_cost.value}"


class UnresolvedProduct(CreateGenericModel):
    product_id = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.product_id}"

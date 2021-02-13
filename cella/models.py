from django.contrib.auth import get_user_model
from django.db import models


class Operator(models.Model):
    user = models.OneToOneField(get_user_model(),
                                on_delete=models.SET_NULL,
                                related_name='operator',
                                null=True,
                                blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name if self.name is not None else getattr(self.user, 'username')

    @classmethod
    def get_system_operator(cls):
        return Operator.objects.get_or_create(name='system')[0]

    @classmethod
    def get_anonymous_operator(cls):
        return Operator.objects.get_or_create(name='anonymous')[0]

    @classmethod
    def get_user_operator(cls, user):
        return Operator.objects.get_or_create(user=user)[0]


class ResourceProvider(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Resource(models.Model):
    provider = models.ForeignKey(ResourceProvider,
                                 on_delete=models.SET_NULL,
                                 related_name='resources',
                                 null=True,
                                 blank=True)
    name = models.CharField(max_length=100)
    external_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=.0)

    def __str__(self):
        return f"{self.name} - {self.external_id}"


class ResourceCost(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=8, decimal_places=2)
    time_stamp = models.DateTimeField(auto_now=True)
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.resource.name} - {self.value}'

    class Meta:
        ordering = ['time_stamp']


class ResourceAction(models.Model):
    class ActionType(models.TextChoices):
        CREATE = 'CRT', 'Create'
        UPDATE_FIELDS = 'UPF', 'Update fields'
        SET_COST = 'STC', 'Set cost'
        SET_AMOUNT = 'STA', 'Set amount'
        VERIFY_COST = 'VYC', 'Verify cost'
        CHANGE_AMOUNT = 'CMT', 'Change amount'

    resource = models.ForeignKey(Resource,
                                 on_delete=models.CASCADE,
                                 related_name='resource_actions')
    action_type = models.CharField(max_length=3, choices=ActionType.choices)
    value = models.CharField(max_length=100, null=True)
    time_stamp = models.DateTimeField(auto_now_add=True)
    operator = models.ForeignKey(Operator,
                                 on_delete=models.SET_NULL,
                                 related_name='resource_actions',
                                 null=True)

    def __str__(self):
        return f"{self.action_type} for {self.resource}"


class SpecificationCategory(models.Model):
    name = models.CharField(max_length=100)
    coefficient = models.DecimalField(max_digits=8, decimal_places=2, null=True)

    def __str__(self):
        return self.name


class Specification(models.Model):
    name = models.CharField(max_length=100)
    product_id = models.CharField(max_length=50)
    category = models.ForeignKey(SpecificationCategory,
                                 on_delete=models.SET_NULL,
                                 related_name='specifications',
                                 null=True,
                                 blank=True)
    is_active = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=.0)
    amount = models.IntegerField(default=0)
    coefficient = models.DecimalField(max_digits=12, decimal_places=2, default=None, null=True)

    def __str__(self):
        return f"{self.name}"


class SpecificationAction(models.Model):
    class ActionType(models.TextChoices):
        CREATE = 'CRT', 'Create'
        DEACTIVATE = 'DCT', 'Deactivate'
        ACTIVATE = 'ACT', 'Activate'
        SET_PRICE = 'STP', 'Set price'
        SET_AMOUNT = 'STA', 'Set amount'
        UPDATE_FIELDS = 'UPF', 'Update fields'
        SET_COEFFICIENT = 'SCT', 'Set coefficient'
        SET_CATEGORY = 'SCY', 'Set category'
        BUILD_SET = 'BLS', 'Build set'

    specification = models.ForeignKey(Specification,
                                      on_delete=models.SET_NULL,
                                      related_name='specification_actions',
                                      null=True)
    action_type = models.CharField(max_length=3, choices=ActionType.choices)
    time_stamp = models.DateTimeField(auto_now_add=True)
    value = models.CharField(max_length=100, null=True)
    operator = models.ForeignKey(Operator,
                                 on_delete=models.SET_NULL,
                                 related_name='specification_actions',
                                 null=True)

    def __str__(self):
        return f"{self.action_type} for {self.specification}"


class ResourceSpecification(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.SET_NULL, null=True, related_name='res_specs')
    specification = models.ForeignKey(Specification, on_delete=models.SET_NULL, null=True, related_name='res_specs')
    amount = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.resource} - {self.specification}"


class Order(models.Model):
    class OrderStatus(models.TextChoices):
        INACTIVE = 'INC', 'Inactive'
        ACTIVE = 'ACT', 'Active'
        ASSEMBLING = 'ASS', 'Assembling'
        READY = 'RDY', 'Ready'
        ARCHIVED = 'ARC', 'Archived'
        CONFIRMED = 'CNF', 'Confirmed'
        CANCELED = 'CND', 'Canceled'

    external_id = models.CharField(max_length=100)
    status = models.CharField(max_length=3, choices=OrderStatus.choices, default=OrderStatus.INACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=100, default='Amazon')

    def __str__(self):
        return f"{self.external_id}"


class OrderSpecification(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_specification')
    specification = models.ForeignKey(Specification, on_delete=models.CASCADE, related_name='order_specification')
    amount = models.IntegerField()
    assembled = models.BooleanField(default=False)


class OrderAction(models.Model):
    class ActionType(models.TextChoices):
        CREATE = 'CRT', 'Create'
        CONFIRM = 'CFM', 'Confirm'
        CANCEL = 'CNL', 'Cancel'
        ACTIVATE = 'ACT', 'Activate'
        DEACTIVATE = 'DCT', 'Deactivate'
        ASSEMBLING = 'ASS', 'Assembling'
        PREPARING = 'PRP', 'Preparing'
        ARCHIVATION = 'ARC', 'Archivation'
        ASSEMBLING_SPECIFICATION = 'ASP', 'Assembling specification'
        DISASSEMBLING_SPECIFICATION = 'DSS', 'Disassembling specification'

    order = models.ForeignKey(Order,
                              on_delete=models.CASCADE,
                              related_name='order_actions',
                              null=True)
    action_type = models.CharField(max_length=3, choices=ActionType.choices)
    time_stamp = models.DateTimeField(auto_now_add=True)
    value = models.CharField(max_length=100, null=True, default=None)
    operator = models.ForeignKey(Operator,
                                 on_delete=models.SET_NULL,
                                 related_name='order_actions',
                                 null=True)

    def __str__(self):
        return f"{self.action_type} for {self.order}"


class Test1(models.Model):
    test = models.CharField(max_length=100)
    var = models.IntegerField()


class Test2(models.Model):
    tt = models.CharField(max_length=100, unique=True)
    bb = models.FloatField()
    v = models.ForeignKey(Test1, on_delete=models.CASCADE, null=True)


class File(
    models.Model):
    class Direction(models.TextChoices):
        RESOURCE_ADD = 'RAD', 'Resource add'

    file = models.FileField(blank=False, null=False)
    direction = models.CharField(choices=Direction.choices, max_length=3, default=Direction.RESOURCE_ADD)
    operator = models.ForeignKey(Operator, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

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

    def __str__(self):
        return f"{self.name} - {self.external_id}"


class ResourceCost(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=8, decimal_places=2)
    time_stamp = models.DateTimeField(auto_now=True)
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.resource.name} - {self.value}'


class ResourceAmount(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='amounts')
    value = models.DecimalField(max_digits=8, decimal_places=2)
    time_stamp = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.resource.name} - {self.value}'


class ResourceAction(models.Model):
    class ActionType(models.TextChoices):
        CREATE = 'CRT', 'Create'
        UPDATE_FIELDS = 'UPF', 'Update fields'
        SET_COST = 'STC', 'Set cost'
        SET_AMOUNT = 'STA', 'Set amount'
        RISE_AMOUNT = 'RSA', 'Rise amount'
        DROP_AMOUNT = 'DRA', 'Drop amount'

    class ActionMessage:
        CREATE = "Ресурс создан"
        SET_COST = "Установлена новая цена: {cost_value}"
        SET_AMOUNT = "Установлена новое количество: {amount_value}"
        RISE_AMOUNT = "Добавлено {delta_amount} ресуров"
        DROP_AMOUNT = "Ушло {delta_amount} ресурсов"

    resource = models.ForeignKey(Resource,
                                 on_delete=models.CASCADE,
                                 related_name='resource_actions')
    action_type = models.CharField(max_length=3, choices=ActionType.choices)
    message = models.CharField(max_length=200, null=True, blank=True)
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

    # resources = models.ManyToManyField(Resource, through='ResourceSpecification')

    def __str__(self):
        return f"{self.name}"


class SpecificationPrice(models.Model):
    specification = models.ForeignKey(Specification, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=8, decimal_places=2)
    time_stamp = models.DateTimeField(auto_now=True)
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.specification.name} - {self.value}'


class SpecificationAction(models.Model):
    class ActionType(models.TextChoices):
        CREATE = 'CRT', 'Create'
        DEACTIVATE = 'DCT', 'Deactivate'
        ACTIVATE = 'ACT', 'Activate'
        SET_PRICE = 'STP', 'Set price'
        UPDATE_FIELDS = 'UPF', 'Update fields'

    specification = models.ForeignKey(Specification,
                                      on_delete=models.SET_NULL,
                                      related_name='specification_actions',
                                      null=True)
    action_type = models.CharField(max_length=3, choices=ActionType.choices)
    time_stamp = models.DateTimeField(auto_now_add=True)
    operator = models.ForeignKey(Operator,
                                 on_delete=models.SET_NULL,
                                 related_name='specification_actions',
                                 null=True)

    def __str__(self):
        return f"{self.action_type} for {self.specification}"


class ResourceSpecification(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.SET_NULL, null=True, related_name='res_spec')
    specification = models.ForeignKey(Specification, on_delete=models.SET_NULL, null=True, related_name='res_spec')
    amount = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.resource} - {self.specification}"


class ResourceSpecificationAssembled(models.Model):
    res_spec = models.ForeignKey(ResourceSpecification, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.res_spec}: {self.amount}"


class Order(models.Model):
    external_id = models.CharField(max_length=100)
    active = models.BooleanField(default=False)
    archived = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.external_id}"


class OrderSpecification(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    specification = models.ForeignKey(Specification, on_delete=models.CASCADE)
    amount = models.IntegerField()


class OrderAction(models.Model):
    class ActionType(models.TextChoices):
        CREATE = 'CRT', 'Create'
        CONFIRM = 'CFM', 'Confirm'
        CANCEL = 'CNL', 'Cancel'
        CONFIRM_SPECIFICATION = 'CSN', 'Confirm specification'

    order = models.ForeignKey(Specification,
                              on_delete=models.CASCADE,
                              related_name='order_actions',
                              null=True)
    action_type = models.CharField(max_length=3, choices=ActionType.choices)
    time_stamp = models.DateTimeField(auto_now_add=True)
    operator = models.ForeignKey(Operator,
                                 on_delete=models.SET_NULL,
                                 related_name='order_actions',
                                 null=True)

    def __str__(self):
        return f"{self.action_type} for {self.order}"

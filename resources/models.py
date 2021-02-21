from django.db import models

from cella.models import Operator


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
    name = models.CharField(max_length=400)
    external_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=.0)
    amount_limit = models.DecimalField(max_digits=12, decimal_places=2, default=10)

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
    value = models.CharField(max_length=300, null=True)
    time_stamp = models.DateTimeField(auto_now_add=True)
    operator = models.ForeignKey(Operator,
                                 on_delete=models.SET_NULL,
                                 related_name='resource_actions',
                                 null=True)

    def __str__(self):
        return f"{self.action_type} for {self.resource}"
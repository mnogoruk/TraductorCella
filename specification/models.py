from django.db import models

from cella.models import Operator
from resources.models import Resource


class SpecificationCategory(models.Model):
    name = models.CharField(max_length=150)
    coefficient = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Specification(models.Model):
    name = models.CharField(max_length=400, null=True)
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
    verified = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    storage_place = models.CharField(max_length=100, null=True)

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
    value = models.CharField(max_length=300, null=True)
    operator = models.ForeignKey(Operator,
                                 on_delete=models.SET_NULL,
                                 related_name='specification_actions',
                                 null=True)

    def __str__(self):
        return f"{self.action_type} for {self.specification}"


class SpecificationResource(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, null=True, related_name='res_specs')
    specification = models.ForeignKey(Specification, on_delete=models.CASCADE, null=True, related_name='res_specs')
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.resource} - {self.specification}"

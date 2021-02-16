from django.db import models

from cella.models import Operator
from specification.models import Specification


class OrderSource(models.Model):
    name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.name}"


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
    source = models.ForeignKey(OrderSource, on_delete=models.SET_NULL, null=True)

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
    value = models.CharField(max_length=300, null=True, default=None)
    operator = models.ForeignKey(Operator,
                                 on_delete=models.SET_NULL,
                                 related_name='order_actions',
                                 null=True)

    def __str__(self):
        return f"{self.action_type} for {self.order}"

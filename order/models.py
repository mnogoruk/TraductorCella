from django.db import models

from cella.models import Operator
from specification.models import Specification


class OrderSource(models.Model):
    name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)

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

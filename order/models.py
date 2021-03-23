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
        ARCHIVED = 'ARC', 'Archived'
        CONFIRMED = 'CNF', 'Confirmed'
        CANCELED = 'CND', 'Canceled'

    external_id = models.CharField(max_length=100)
    status = models.CharField(max_length=3, choices=OrderStatus.choices, default=OrderStatus.INACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    source = models.ForeignKey(OrderSource, on_delete=models.SET_NULL, null=True)

    def canceled(self):
        return self.status == Order.OrderStatus.CANCELED

    def archived(self):
        return self.status == Order.OrderStatus.ARCHIVED

    def confirmed(self):
        return self.status == Order.OrderStatus.CONFIRMED

    def confirm(self):
        self.status = Order.OrderStatus.CONFIRMED

    def archive(self):
        self.status = Order.OrderStatus.ARCHIVED

    def cancel(self):
        self.status = Order.OrderStatus.CANCELED

    def __str__(self):
        return f"{self.external_id}"


class OrderSpecification(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_specifications')
    specification = models.ForeignKey(Specification, on_delete=models.CASCADE, related_name='order_specifications')
    amount = models.IntegerField()
    assembled = models.BooleanField(default=False)

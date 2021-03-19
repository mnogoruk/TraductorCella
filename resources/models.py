from django.db import models
from django.utils import timezone

from cella.models import Operator
from .manager import ResourceProviderManager


class ResourceProvider(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ResourceProviderManager()

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
    amount_limit = models.DecimalField(max_digits=12, decimal_places=2, default=10.0)
    created_at = models.DateTimeField(auto_now_add=True)
    storage_place = models.CharField(max_length=100, null=True)
    comment = models.CharField(max_length=400, null=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.name} - {self.external_id}"


class ResourceDelivery(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    provider = models.ForeignKey(ResourceProvider, on_delete=models.CASCADE, null=True)

    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    comment = models.CharField(max_length=400, null=True)
    time_stamp = models.DateField(null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def set_resource(self, resource):
        self.resource = resource

    def set_provider(self, provider):
        self.provider = provider

    def set_cost(self, cost):
        self.cost = cost

    def set_amount(self, amount):
        self.amount = amount

    def set_comment(self, comment):
        self.comment = comment

    def set_time_stamp(self, time_stamp):
        self.time_stamp = time_stamp

    @property
    def provider_name(self):
        return self.provider.name

    def __str__(self):
        return f"Delivery for {self.resource.id} - {self.amount}"

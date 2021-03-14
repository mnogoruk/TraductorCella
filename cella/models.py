from django.contrib.auth import get_user_model
from django.db import models

from utils.db.query import GetOrCreateQuery


class Operator(models.Model):
    user = models.OneToOneField(get_user_model(),
                                on_delete=models.SET_NULL,
                                related_name='operator',
                                null=True,
                                blank=True)
    name = models.CharField(max_length=150, null=True, blank=True)

    def __str__(self):
        return self.name if self.name is not None else getattr(self.user, 'username')

    @classmethod
    def get_system_operator(cls):
        return GetOrCreateQuery(Operator).get_or_create(name='system').object()

    @classmethod
    def get_anonymous_operator(cls):
        return GetOrCreateQuery(Operator).get_or_create(name='anonymous').object()

    @classmethod
    def get_user_operator(cls, user):
        return GetOrCreateQuery(Operator).get_or_create(user=user).object()


class File(models.Model):
    file = models.FileField(blank=False, null=False)
    operator = models.ForeignKey(Operator, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

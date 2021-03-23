from django.db import models

from authentication.models import Operator


class File(models.Model):
    file = models.FileField(blank=False, null=False)
    operator = models.ForeignKey(Operator, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)


class Recoding(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    operator = models.ForeignKey(Operator, on_delete=models.SET_NULL, null=True)
    message = models.TextField()

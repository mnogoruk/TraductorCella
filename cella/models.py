from django.contrib.auth import get_user_model
from django.db import models


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
        return Operator.objects.get_or_create(name='system')[0]

    @classmethod
    def get_anonymous_operator(cls):
        return Operator.objects.get_or_create(name='anonymous')[0]

    @classmethod
    def get_user_operator(cls, user):
        return Operator.objects.get_or_create(user=user)[0]


class Test1(models.Model):
    test = models.CharField(max_length=100)
    var = models.IntegerField()


class Test2(models.Model):
    tt = models.CharField(max_length=100, unique=True)
    bb = models.FloatField()
    v = models.ForeignKey(Test1, on_delete=models.CASCADE, null=True)


class File(models.Model):
    class Direction(models.TextChoices):
        RESOURCE_ADD = 'RAD', 'Resource add'

    file = models.FileField(blank=False, null=False)
    direction = models.CharField(choices=Direction.choices, max_length=3, default=Direction.RESOURCE_ADD)
    operator = models.ForeignKey(Operator, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

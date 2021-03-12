from django.db.models import QuerySet


class ObjectExisting:

    def __init__(self, obj, existed):
        self._object = obj
        self._existed = existed

    def object(self):
        return self._object

    def existed(self):
        return self._existed


class GetOrCreateQuery(QuerySet):

    def get_or_create(self, defaults=None, **kwargs):
        return ObjectExisting(*super(GetOrCreateQuery, self).get_or_create(defaults, **kwargs))

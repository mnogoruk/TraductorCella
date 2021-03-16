from django.db.models import Manager

from utils.db.query import GetOrCreateQuery, ObjectExisting


class ResourceProviderManager(Manager):

    def get_or_create_by_name(self, name):
        if name is None:
            return ObjectExisting(None, False)
        return GetOrCreateQuery(self.model).get_or_create(name=name)

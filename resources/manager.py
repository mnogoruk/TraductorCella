from django.db.models import Manager

from utils.db.query import GetOrCreateQuery


class ResourceProviderManager(Manager):

    def get_or_create_by_name(self, name):
        return GetOrCreateQuery(self.model).get_or_create(name=name)

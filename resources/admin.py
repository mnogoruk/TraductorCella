from django.contrib import admin

from .models import Resource, ResourceProvider, ResourceDelivery

admin.site.register(ResourceProvider)
admin.site.register(Resource)
admin.site.register(ResourceDelivery)

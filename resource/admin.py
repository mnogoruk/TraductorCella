from django.contrib import admin

from .models import Resource, ResourceProvider, ResourceCost, ResourceAction

admin.site.register(ResourceProvider)
admin.site.register(Resource)
admin.site.register(ResourceCost)
admin.site.register(ResourceAction)

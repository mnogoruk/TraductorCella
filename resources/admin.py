from django.contrib import admin

from .models import Resource, ResourceProvider

admin.site.register(ResourceProvider)
admin.site.register(Resource)


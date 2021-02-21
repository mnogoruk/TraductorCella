from django.contrib import admin

from .models import Specification, SpecificationCategory, SpecificationAction, SpecificationResource

admin.site.register(SpecificationCategory)
admin.site.register(Specification)
admin.site.register(SpecificationAction)
admin.site.register(SpecificationResource)

from django.contrib import admin

from .models import Specification, SpecificationCategory, SpecificationResource

admin.site.register(SpecificationCategory)
admin.site.register(Specification)
admin.site.register(SpecificationResource)

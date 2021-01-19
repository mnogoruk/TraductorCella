from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(Operator)
admin.site.register(ResourceProvider)
admin.site.register(Resource)
admin.site.register(StorageAction)
admin.site.register(CostAction)
admin.site.register(ServiceAction)
admin.site.register(SpecificationCategory)
admin.site.register(Specification)
admin.site.register(ResourceSpecification)
admin.site.register(SpecificationAction)
admin.site.register(ResourceCost)
admin.site.register(UnverifiedCost)

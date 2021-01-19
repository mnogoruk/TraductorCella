from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(Operator)

admin.site.register(ResourceProvider)
admin.site.register(Resource)
admin.site.register(ResourceCost)

admin.site.register(ResourceStorageAction)
admin.site.register(ResourceCostAction)
admin.site.register(ResourceServiceAction)

admin.site.register(SpecificationCategory)
admin.site.register(Specification)
admin.site.register(ResourceSpecification)

admin.site.register(SpecificationCaptureAction)
admin.site.register(SpecificationCoefficientAction)
admin.site.register(SpecificationServiceAction)


admin.site.register(UnverifiedCost)
admin.site.register(UnresolvedProduct)

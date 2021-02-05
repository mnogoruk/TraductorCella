from django.contrib import admin

# Register your models here.
from .models import (Operator,
                     ResourceProvider,
                     Resource,
                     ResourceCost,
                     ResourceAmount,
                     ResourceAction,
                     SpecificationCategory,
                     Specification,
                     SpecificationPrice,
                     SpecificationAction,
                     ResourceSpecification,
                     ResourceSpecificationAssembled,
                     Order,
                     OrderSpecification,
                     OrderAction,
                     SpecificationCoefficient,
                     File)

admin.site.register(Operator)

admin.site.register(ResourceProvider)
admin.site.register(Resource)
admin.site.register(ResourceCost)
admin.site.register(ResourceAmount)
admin.site.register(ResourceAction)

admin.site.register(SpecificationCategory)
admin.site.register(Specification)
admin.site.register(SpecificationPrice)
admin.site.register(SpecificationCoefficient)
admin.site.register(SpecificationAction)

admin.site.register(ResourceSpecification)
admin.site.register(ResourceSpecificationAssembled)

admin.site.register(Order)
admin.site.register(OrderSpecification)
admin.site.register(OrderAction)

admin.site.register(File)

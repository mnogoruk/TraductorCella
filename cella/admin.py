from django.contrib import admin

# Register your models here.
from .models import (Operator,
                     ResourceProvider,
                     Resource,
                     ResourceCost,
                     ResourceAction,
                     SpecificationCategory,
                     Specification,
                     SpecificationAction,
                     ResourceSpecification,
                     Order,
                     OrderSpecification,
                     OrderAction,
                     File, Test2, Test1)

admin.site.register(Operator)

admin.site.register(ResourceProvider)
admin.site.register(Resource)
admin.site.register(ResourceCost)
admin.site.register(ResourceAction)

admin.site.register(SpecificationCategory)
admin.site.register(Specification)
admin.site.register(SpecificationAction)

admin.site.register(ResourceSpecification)

admin.site.register(Order)
admin.site.register(OrderSpecification)
admin.site.register(OrderAction)

admin.site.register(File)

admin.site.register(Test1)
admin.site.register(Test2)

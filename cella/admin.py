from django.contrib import admin

# Register your models here.
from .models import Operator, File, Test2, Test1

admin.site.register(Operator)




admin.site.register(Order)
admin.site.register(OrderSource)
admin.site.register(OrderSpecification)
admin.site.register(OrderAction)

admin.site.register(File)

admin.site.register(Test1)
admin.site.register(Test2)

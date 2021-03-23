from django.contrib import admin

from .models import Order, OrderSource, OrderSpecification

admin.site.register(Order)
admin.site.register(OrderSource)
admin.site.register(OrderSpecification)

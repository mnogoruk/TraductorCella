from django.urls import path
from .views import resources, specification, specifications, resource_detail

urlpatterns = [
    path('resources', resources),
    path('resource/<int:r_id>', resource_detail),
    path('spec/<int:spec_id>', specification),
    path('specs', specifications),
]

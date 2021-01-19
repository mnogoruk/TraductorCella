from django.urls import path
from .views import resources, specification, specifications, resource_detail, resource_create

urlpatterns = [
    path('resources', resources, name='resource_list'),
    path('resource/<int:r_id>', resource_detail),
    path('resource/create', resource_create),
    path('spec/<int:spec_id>', specification),
    path('specs', specifications),
]

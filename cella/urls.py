from django.urls import path
from .views import resources, specification, specifications, resource_detail, resource_create, resource_edit, \
    resource_unverified, specification_create, specification_unverified

urlpatterns = [
    path('resources', resources, name='resource_list'),
    path('resource/<int:r_id>', resource_detail),
    path('resource/create', resource_create),
    path('verify/resources', resource_unverified),
    path('verify/specifications', specification_unverified),
    path('resource/edit/<int:r_id>', resource_edit),
    path('spec/<int:spec_id>', specification),
    path('specs', specifications, name='specification_list'),
    path('specification/create', specification_create)
]

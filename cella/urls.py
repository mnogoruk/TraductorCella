from django.urls import path
from .views import ResourceDetailView, ResourceCreateView, ResourceUpdateView

urlpatterns = [
    #     path('resources', resources, name='resource_list'),
    path('resource/<int:r_id>', ResourceDetailView.as_view()),
    path('resource/create', ResourceCreateView.as_view()),
    path('resource/edit/<int:r_id>', ResourceUpdateView.as_view())
    #     path('verify/resources', resource_unverified),
    #     path('verify/specifications', specification_unverified),
    #     path('resource/edit/<int:r_id>', resource_edit),
    #     path('spec/<int:spec_id>', specification),
    #     path('specs', specifications, name='specification_list'),
    #     path('specification/create', specification_create)
]

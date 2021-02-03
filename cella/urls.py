from django.urls import path
from .views import ResourceDetailView, ResourceCreateView, ResourceUpdateView, ResourceListView, ResourceActionsView, \
    ResourceWithUnverifiedCostsView, SpecificationDetailView, SpecificationListView, ResourceSetCost, \
    ResourceVerifyCost, ResourceShortListView, ProviderListView, SpecificationCategoryListView

urlpatterns = [

    path('resource/<int:r_id>/', ResourceDetailView.as_view()),
    path('resource/create/', ResourceCreateView.as_view()),
    path('resource/edit/<int:r_id>/', ResourceUpdateView.as_view()),
    path('resource/list/', ResourceListView.as_view()),
    path('resource/actions/<int:r_id>/', ResourceActionsView.as_view()),
    path('resource/unverified/', ResourceWithUnverifiedCostsView.as_view()),
    path('resource/set-cost/<int:r_id>/', ResourceSetCost.as_view()),
    path('resource/verify-cost/<int:r_id>/', ResourceVerifyCost.as_view()),
    path('resource/shortlist/', ResourceShortListView.as_view()),
    path('resource/providers/', ProviderListView.as_view()),

    path('specification/<int:s_id>/', SpecificationDetailView.as_view()),
    path('specification/list/', SpecificationListView.as_view()),
    path('specification/categories/', SpecificationCategoryListView.as_view())

]

from django.urls import path
from .views import ResourceDetailView, ResourceCreateView, ResourceUpdateView, ResourceListView, ResourceActionsView, \
    ResourceWithUnverifiedCostsView, SpecificationDetailView, SpecificationListView, ResourceSetCost, \
    ResourceVerifyCost, ResourceShortListView, ProviderListView, SpecificationCategoryListView, SpecificationCreateView, \
    SpecificationEditView, ResourceAddAmount, ResourceExelUpload

urlpatterns = [

    path('resource/<int:r_id>/', ResourceDetailView.as_view()),
    path('resource/create/', ResourceCreateView.as_view()),
    path('resource/edit/<int:r_id>/', ResourceUpdateView.as_view()),
    path('resource/list/', ResourceListView.as_view()),
    path('resource/actions/<int:r_id>/', ResourceActionsView.as_view()),
    path('resource/unverified/', ResourceWithUnverifiedCostsView.as_view()),
    path('resource/set-cost/', ResourceSetCost.as_view()),
    path('resource/verify-cost/', ResourceVerifyCost.as_view()),
    path('resource/shortlist/', ResourceShortListView.as_view()),
    path('resource/providers/', ProviderListView.as_view()),
    path('resource/add-amount/', ResourceAddAmount.as_view()),
    path('resource/upload/', ResourceExelUpload.as_view()),

    path('specification/<int:s_id>/', SpecificationDetailView.as_view()),
    path('specification/list/', SpecificationListView.as_view()),
    path('specification/categories/', SpecificationCategoryListView.as_view()),
    path('specification/create/', SpecificationCreateView.as_view()),
    path('specification/edit/<int:s_id>/',SpecificationEditView.as_view()),


]

from django.urls import path

from resources.views import ResourceListView, ResourceActionsView, ResourceUpdateView, ResourceCreateView, \
    ResourceDetailView, ResourceWithUnverifiedCostsView, ResourceSetCostView, ResourceVerifyCostView, \
    ResourceShortListView, ProviderListView, ResourceAddAmountView, ResourceExelUploadView, ResourceBulkDeleteView, \
    ExpiredResourceCount, ResourceSetAmount

urlpatterns = [
    path('<int:r_id>/', ResourceDetailView.as_view()),
    path('create/', ResourceCreateView.as_view()),
    path('edit/<int:r_id>/', ResourceUpdateView.as_view()),
    path('list/', ResourceListView.as_view()),
    path('actions/<int:r_id>/', ResourceActionsView.as_view()),
    path('unverified/', ResourceWithUnverifiedCostsView.as_view()),
    path('set-cost/', ResourceSetCostView.as_view()),
    path('verify-cost/', ResourceVerifyCostView.as_view()),
    path('shortlist/', ResourceShortListView.as_view()),
    path('providers/', ProviderListView.as_view()),
    path('set-amount/', ResourceSetAmount.as_view()),
    path('add-amount/', ResourceAddAmountView.as_view()),
    path('upload/', ResourceExelUploadView.as_view()),
    path('delete/', ResourceBulkDeleteView.as_view()),
    path('expired-count/', ExpiredResourceCount.as_view())
]

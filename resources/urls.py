from django.urls import path

from resources.views import ResourceListView, ResourceUpdateView, ResourceCreateView, \
    ResourceDetailView, \
    ResourceShortListView, ProviderListView, ResourceExelUploadView, ResourceBulkDeleteView, \
    ExpiredResourceCount, MakeDeliveryView


urlpatterns = [
    path('<int:r_id>/', ResourceDetailView.as_view()),
    path('create/', ResourceCreateView.as_view()),
    path('edit/<int:r_id>/', ResourceUpdateView.as_view()),
    path('list/', ResourceListView.as_view()),
    path('shortlist/', ResourceShortListView.as_view()),
    path('providers/', ProviderListView.as_view()),
    path('upload/', ResourceExelUploadView.as_view()),
    path('delete/', ResourceBulkDeleteView.as_view()),
    path('expired-count/', ExpiredResourceCount.as_view()),
    path('delivery/', MakeDeliveryView.as_view())
]

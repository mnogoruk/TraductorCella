from django.urls import path
from .views import ResourceDetailView, ResourceCreateView, ResourceUpdateView, ResourceListView, ResourceActionsView, ResourceWithUnverifiedCostsView

urlpatterns = [
    path('resource/<int:r_id>/', ResourceDetailView.as_view()),
    path('resource/create/', ResourceCreateView.as_view()),
    path('resource/edit/<int:r_id>/', ResourceUpdateView.as_view()),
    path('resource/list/', ResourceListView.as_view()),
    path('resource/actions/<int:r_id>/', ResourceActionsView.as_view()),
    path('resource/unverified/', ResourceWithUnverifiedCostsView.as_view())
]

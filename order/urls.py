from django.urls import path

from order.views import OrderDetailView, OrderCreateView, OrderListView,\
    OrderManageActionView, OrderAssemblingInfoView, OrderBulkDeleteView, \
    OrderStatusCount, ReceiveOrderView

urlpatterns = [
    path('<int:o_id>/', OrderDetailView.as_view()),
    path('create/', OrderCreateView.as_view()),
    path('list/', OrderListView.as_view()),
    path('action/', OrderManageActionView.as_view()),
    path('assemble-info/<int:o_id>/', OrderAssemblingInfoView.as_view()),
    path('delete/', OrderBulkDeleteView.as_view()),
    path('status-count/', OrderStatusCount.as_view()),
    path('receive/', ReceiveOrderView.as_view()),
]

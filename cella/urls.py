from django.urls import path
from .views import ResourceDetailView, ResourceCreateView, ResourceUpdateView, ResourceListView, ResourceActionsView, \
    ResourceWithUnverifiedCostsView, SpecificationDetailView, SpecificationListView, ResourceSetCostView, \
    ResourceVerifyCostView, ResourceShortListView, ProviderListView, SpecificationCategoryListView, \
    SpecificationCreateView, \
    SpecificationEditView, ResourceAddAmountView, ResourceExelUploadView, SpecificationSetPriceView, \
    SpecificationSetCoefficientView, OrderDetailView, OrderListView, OrderDisAssembleSpecificationView, \
    OrderAssembleSpecificationView, OrderManageActionView, SpecificationAssembleInfoView, SpecificationBuildSetView, \
    OrderAssemblingInfoView, OrderBulkDeleteView, SpecificationSetCategoryView, ResourceBulkDeleteView, \
    SpecificationBulkDeleteView, SpecificationCreateCategoryView, OrderCreateView

urlpatterns = [

    path('resource/<int:r_id>/', ResourceDetailView.as_view()),
    path('resource/create/', ResourceCreateView.as_view()),
    path('resource/edit/<int:r_id>/', ResourceUpdateView.as_view()),
    path('resource/list/', ResourceListView.as_view()),
    path('resource/actions/<int:r_id>/', ResourceActionsView.as_view()),
    path('resource/unverified/', ResourceWithUnverifiedCostsView.as_view()),
    path('resource/set-cost/', ResourceSetCostView.as_view()),
    path('resource/verify-cost/', ResourceVerifyCostView.as_view()),
    path('resource/shortlist/', ResourceShortListView.as_view()),
    path('resource/providers/', ProviderListView.as_view()),
    path('resource/add-amount/', ResourceAddAmountView.as_view()),
    path('resource/upload/', ResourceExelUploadView.as_view()),
    path('resource/delete/', ResourceBulkDeleteView.as_view()),

    path('specification/<int:s_id>/', SpecificationDetailView.as_view()),
    path('specification/list/', SpecificationListView.as_view()),
    path('specification/categories/', SpecificationCategoryListView.as_view()),
    path('specification/create/', SpecificationCreateView.as_view()),
    path('specification/create-category/', SpecificationCreateCategoryView.as_view()),
    path('specification/edit/<int:s_id>/', SpecificationEditView.as_view()),
    path('specification/set-price/', SpecificationSetPriceView.as_view()),
    path('specification/set-coefficient/', SpecificationSetCoefficientView.as_view()),
    path('specification/assemble-info/<int:s_id>/', SpecificationAssembleInfoView.as_view()),
    path('specification/build-set/', SpecificationBuildSetView.as_view()),
    path('specification/set-category/', SpecificationSetCategoryView.as_view()),
    path('specification/delete/', SpecificationBulkDeleteView.as_view()),

    path('order/<int:o_id>/', OrderDetailView.as_view()),
    path('order/create/', OrderCreateView.as_view()),
    path('order/list/', OrderListView.as_view()),
    path('order/assemble-specification/', OrderAssembleSpecificationView.as_view()),
    path('order/disassemble-specification/', OrderDisAssembleSpecificationView.as_view()),
    path('order/action/', OrderManageActionView.as_view()),
    path('order/assemble-info/<int:o_id>/', OrderAssemblingInfoView.as_view()),
    path('order/delete/', OrderBulkDeleteView.as_view())
]

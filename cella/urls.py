from django.urls import path
from .views import ResourceDetailView, ResourceCreateView, ResourceUpdateView, ResourceListView, ResourceActionsView, \
    ResourceWithUnverifiedCostsView, SpecificationDetailView, SpecificationListView, ResourceSetCost, \
    ResourceVerifyCost, ResourceShortListView, ProviderListView, SpecificationCategoryListView, SpecificationCreateView, \
    SpecificationEditView, ResourceAddAmount, ResourceExelUpload, SpecificationSetPriceView, \
    SpecificationSetCoefficientView, OrderDetailView, OrderListView, OrderDisAssembleSpecificationView, \
    OrderAssembleSpecificationView, OrderManageAction

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
    path('specification/edit/<int:s_id>/', SpecificationEditView.as_view()),
    path('specification/set-price/', SpecificationSetPriceView.as_view()),
    path('specification/set-coefficient/', SpecificationSetCoefficientView.as_view()),

    path('order/<int:o_id>/', OrderDetailView.as_view()),
    path('order/list/', OrderListView.as_view()),
    path('order/assemble-specification/', OrderAssembleSpecificationView.as_view()),
    path('order/disassemble-specification/', OrderDisAssembleSpecificationView.as_view()),
    path('order/action/', OrderManageAction.as_view())
]

from django.urls import path
from specification.views import SpecificationDetailView, SpecificationListView, SpecificationCategoryListView, \
    SpecificationCreateView, SpecificationCreateCategoryView, SpecificationEditView, SpecificationSetPriceView, \
    SpecificationSetCoefficientView, SpecificationAssembleInfoView, SpecificationBuildSetView, \
    SpecificationSetCategoryView, SpecificationBulkDeleteView, SpecificationListShortView, SpecifiedVerifyPriceCount, \
    SpecificationXMLUploadView, SpecificationSetAmountView, ManageBuild


urlpatterns = [
    path('<int:s_id>/', SpecificationDetailView.as_view()),
    path('list/', SpecificationListView.as_view()),
    path('categories/', SpecificationCategoryListView.as_view()),
    path('create/', SpecificationCreateView.as_view()),
    path('create-category/', SpecificationCreateCategoryView.as_view()),
    path('edit/<int:s_id>/', SpecificationEditView.as_view()),
    path('set-price/', SpecificationSetPriceView.as_view()),
    path('set-coefficient/', SpecificationSetCoefficientView.as_view()),
    path('assemble-info/<int:s_id>/', SpecificationAssembleInfoView.as_view()),
    path('set-amount/', SpecificationSetAmountView.as_view()),
    path('build-set/', SpecificationBuildSetView.as_view()),
    path('set-category/', SpecificationSetCategoryView.as_view()),
    path('delete/', SpecificationBulkDeleteView.as_view()),
    path('shortlist/', SpecificationListShortView.as_view()),
    path('verify-price-amount/', SpecifiedVerifyPriceCount.as_view()),
    path('upload/', SpecificationXMLUploadView.as_view()),
    path('manage-build/', ManageBuild.as_view())
]

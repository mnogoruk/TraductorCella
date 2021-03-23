from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from .views import UserCreateView, UserListView, UserEditView, UserChangePasswordView, UserDeleteView, \
    CheckVerifyingView, CheckView, AccountDetailView, TokenObtainPairWithRoleView

urlpatterns = [
    path('token/', TokenObtainPairWithRoleView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('applicant/create/', UserCreateView.as_view(), name='user_create'),
    path('account/', AccountDetailView.as_view(), name='user_detail'),
    path('applicant/list/', UserListView.as_view(), name='user_list'),
    path('applicant/edit/', UserEditView.as_view(), name='user_edit'),
    path('applicant/delete/', UserDeleteView.as_view(), name='user_delete'),
    path('applicant/verify-info/<slug:verifying_slug>/', CheckVerifyingView, name='user_verify_info'),
    path('applicant/change-password/', UserChangePasswordView.as_view(), name='user_change_password'),
    path('applicant/check/', CheckView.as_view(), name='user_check')
]

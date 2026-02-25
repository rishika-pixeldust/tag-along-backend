"""
URL configuration for the Users app.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import (
    ChangePasswordView,
    FirebaseTokenExchangeView,
    LoginView,
    RegisterView,
    UserProfileView,
    UserSearchView,
)

app_name = 'users'

urlpatterns = [
    # Authentication
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/firebase/', FirebaseTokenExchangeView.as_view(), name='firebase-auth'),

    # User profile
    path('users/me/', UserProfileView.as_view(), name='user-profile'),
    path('users/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('users/search/', UserSearchView.as_view(), name='user-search'),
]

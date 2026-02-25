"""
URL configuration for the Users app.
"""
from django.urls import path

from apps.users.views import (
    ChangePasswordView,
    CustomTokenRefreshView,
    FirebaseTokenExchangeView,
    LoginView,
    LogoutView,
    RegisterView,
    UserProfileView,
    UserSearchView,
)

app_name = 'users'

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('firebase/', FirebaseTokenExchangeView.as_view(), name='firebase-auth'),

    # User profile & account
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('search/', UserSearchView.as_view(), name='user-search'),
]

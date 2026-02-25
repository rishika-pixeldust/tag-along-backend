from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/stats', views.dashboard_stats, name='admin-dashboard-stats'),
    path('users', views.admin_users_list, name='admin-users-list'),
    path('users/<str:user_id>', views.admin_user_detail, name='admin-user-detail'),
    path('groups', views.admin_groups_list, name='admin-groups-list'),
    path('groups/<str:group_id>', views.admin_group_detail, name='admin-group-detail'),
    path('trips', views.admin_trips_list, name='admin-trips-list'),
    path('trips/<str:trip_id>', views.admin_trip_detail, name='admin-trip-detail'),
    path('expenses', views.admin_expenses_list, name='admin-expenses-list'),
    path('expenses/<str:expense_id>', views.admin_expense_detail, name='admin-expense-detail'),
]

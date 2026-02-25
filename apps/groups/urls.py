"""
URL configuration for the Groups app.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.groups.views import (
    GroupMemberViewSet,
    GroupViewSet,
    JoinGroupView,
    LeaveGroupView,
)

app_name = 'groups'

router = DefaultRouter()
router.register(r'', GroupViewSet, basename='group')

# Nested router for members
member_list = GroupMemberViewSet.as_view({
    'get': 'list',
})
member_detail = GroupMemberViewSet.as_view({
    'patch': 'partial_update',
    'delete': 'destroy',
})

urlpatterns = [
    path('', include(router.urls)),
    path('join/', JoinGroupView.as_view(), name='group-join'),
    path(
        '<uuid:group_pk>/members/',
        member_list,
        name='group-member-list',
    ),
    path(
        '<uuid:group_pk>/members/<uuid:pk>/',
        member_detail,
        name='group-member-detail',
    ),
    path(
        '<uuid:group_pk>/leave/',
        LeaveGroupView.as_view(),
        name='group-leave',
    ),
]

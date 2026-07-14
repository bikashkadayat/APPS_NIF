from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from rest_framework.routers import DefaultRouter

from leaves.views import LeaveViewSet, LeaveBalanceView, LeaveCalendarView
from users.views import CurrentUserView, UserListView, ChangePasswordView, ProfileMeView, ProfilePhotoView
from users.token_serializers import EmailLoginView, LogoutView, SafeTokenRefreshView
from users.admin_views import AdminUserViewSet, AdminLeaveViewSet, AdminBalanceViewSet, AdminStatsView
from config.health_views import HealthView, DetailedHealthView

# Automated routing for ViewSets
router = DefaultRouter()
router.register(r'leaves', LeaveViewSet, basename='leave')

# Admin ViewSets
admin_router = DefaultRouter()
admin_router.register(r'admin/users', AdminUserViewSet, basename='admin-user')
admin_router.register(r'admin/leaves', AdminLeaveViewSet, basename='admin-leave')
admin_router.register(r'admin/balances', AdminBalanceViewSet, basename='admin-balance')
# Phase 2.5: spec path for admin User Management.
admin_router.register(r'users/admin/users', AdminUserViewSet, basename='usermgmt-user')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Auth APIs (JWT Authentication)
    path('api/v1/auth/login/', EmailLoginView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/refresh/', SafeTokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/logout/', LogoutView.as_view(), name='token_logout'),
    # Registration removed in Phase 2.5 (admin-created accounts only).
    path('api/v1/auth/user/', CurrentUserView.as_view(), name='token_user'),
    path('api/v1/auth/change-password/', ChangePasswordView.as_view(), name='change-password'),

    # Self-service profile (read + edit own editable fields + photo)
    path('api/v1/profile/me/', ProfileMeView.as_view(), name='profile-me'),
    path('api/v1/profile/me/photo/', ProfilePhotoView.as_view(), name='profile-me-photo'),

    # User list API
    path('api/v1/users/', UserListView.as_view(), name='user-list'),
    
    # Phase 4 Enterprise Leave Records (must precede the /leaves/<pk>/ router
    # below so the custom /leaves/my-history/ etc. paths resolve first)
    path('api/v1/', include('leaves.urls')),

    # Workflow & Leaves APIs
    path('api/v1/', include(router.urls)),
    
    # Admin APIs
    path('api/v1/', include(admin_router.urls)),
    path('api/v1/admin/stats/', AdminStatsView.as_view(), name='admin-stats'),
    
    # Custom Leave Read API routes
    path('api/v1/leaves/balance', LeaveBalanceView.as_view(), name='leave-balance'),
    path('api/v1/leaves/calendar', LeaveCalendarView.as_view(), name='leave-calendar'),

    # Memos APIs (router mounts /api/v1/memos/ and /api/v1/memo-templates/)
    path('api/v1/', include('memos.urls')),

    # Audit Log APIs (admin-only, read-only)
    path('api/v1/audit/', include('audit.urls')),

    # Reports & Analytics (Phase 8, admin-only)
    path('api/v1/', include('reports.urls')),

    # Notifications (Phase 9)
    path('api/v1/', include('notifications.urls')),

    # Public document verification (Phase 10)
    path('api/v1/', include('documents.urls')),

    # Attendance (check-in/out, calendar, HR management)
    path('api/v1/', include('attendance.urls')),

    # Inventory (items, assignments, take-out workflow)
    path('api/v1/', include('inventory.urls')),

    # Health checks (Phase 5)
    path('api/v1/health/', HealthView.as_view(), name='health'),
    path('api/v1/health/detailed/', DetailedHealthView.as_view(), name='health-detailed'),
]

# Media files (uploaded memo attachments, profile photos, generated PDFs).
# When USE_S3 is set the storage backend serves them from the bucket directly,
# so no local route is registered. Otherwise Django serves them from the
# MEDIA_ROOT persistent disk in both development and production.
if not settings.USE_S3:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

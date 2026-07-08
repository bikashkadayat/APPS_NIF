from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from leaves.views import LeaveViewSet, LeaveBalanceView, LeaveCalendarView
from users.views import CurrentUserView, UserListView, ChangePasswordView
from users.token_serializers import EmailLoginView, SafeTokenRefreshView
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
    # Registration removed in Phase 2.5 (admin-created accounts only).
    path('api/v1/auth/user/', CurrentUserView.as_view(), name='token_user'),
    path('api/v1/auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    
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

    # Health checks (Phase 5)
    path('api/v1/health/', HealthView.as_view(), name='health'),
    path('api/v1/health/detailed/', DetailedHealthView.as_view(), name='health-detailed'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

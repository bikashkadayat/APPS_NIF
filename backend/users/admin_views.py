from rest_framework import generics, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime
from audit.models import AuditLog
from audit.services import log_action
from .models import User
from leaves.models import Leave, LeaveBalance
from leaves.serializers import LeaveSerializer, LeaveBalanceSerializer
from leaves.filters import LeaveFilter
from .serializers import UserSerializer, AdminUserCreateSerializer


class IsAdminOrSuperuser(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (request.user.is_staff or request.user.is_superuser or request.user.role == 'admin')


class AdminUserViewSet(viewsets.ModelViewSet):
    """
    Admin-only user management (Phase 2.5). Mounted at both
    /api/v1/admin/users/ (legacy) and /api/v1/users/admin/users/ (spec).
    Every mutating action is transactional and audit-logged.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrSuperuser]
    search_fields = ['username', 'email', 'first_name', 'last_name', 'employee_id']
    filterset_fields = ['role', 'is_active']

    def get_queryset(self):
        return User.objects.select_related('department_ref').all().order_by('username')

    def get_serializer_class(self):
        # Create + edit go through the category-aware serializer so employment
        # type / joining date / gender changes re-resolve the category and rebuild
        # balances. List/retrieve use the read serializer.
        if self.action in ('create', 'update', 'partial_update'):
            return AdminUserCreateSerializer
        return UserSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(request.user, AuditLog.Action.CREATE, instance=serializer.instance,
                   changes={'event': 'USER_CREATED', 'role': serializer.instance.role}, request=request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def perform_update(self, serializer):
        serializer.save()
        log_action(self.request.user, AuditLog.Action.UPDATE, instance=serializer.instance, request=self.request)

    @transaction.atomic
    def perform_destroy(self, instance):
        log_action(self.request.user, AuditLog.Action.DELETE, instance=instance, request=self.request)
        instance.delete()

    @action(detail=True, methods=['post'], url_path='reset-password')
    @transaction.atomic
    def reset_password(self, request, pk=None):
        import secrets
        user = self.get_object()
        new_password = request.data.get('password') or secrets.token_urlsafe(9)
        user.set_password(new_password)
        user.must_change_password = True  # force change on next login
        user.save(update_fields=['password', 'must_change_password'])
        log_action(request.user, AuditLog.Action.UPDATE, instance=user,
                   changes={'event': 'PASSWORD_RESET'}, request=request)
        return Response({'detail': 'Password reset.', 'generated_password': new_password})

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if user.id == request.user.id:
            return Response({'detail': 'You cannot deactivate your own account.'}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = False
        user.save(update_fields=['is_active'])
        log_action(request.user, AuditLog.Action.UPDATE, instance=user,
                   changes={'event': 'USER_DEACTIVATED'}, request=request)
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])
        log_action(request.user, AuditLog.Action.UPDATE, instance=user,
                   changes={'event': 'USER_ACTIVATED'}, request=request)
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['post'], url_path='change-role')
    @transaction.atomic
    def change_role(self, request, pk=None):
        user = self.get_object()
        new_role = request.data.get('role')
        if new_role not in User.Roles.values:
            return Response({'detail': 'Invalid role.'}, status=status.HTTP_400_BAD_REQUEST)
        old_role = user.role
        user.role = new_role
        user.save(update_fields=['role'])
        log_action(request.user, AuditLog.Action.UPDATE, instance=user,
                   changes={'event': 'ROLE_CHANGED', 'from': old_role, 'to': new_role}, request=request)
        return Response(UserSerializer(user).data)


class AdminStatsView(generics.GenericAPIView):
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        now = timezone.now()
        current_year = now.year

        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        total_leaves = Leave.objects.count()
        pending_leaves = Leave.objects.filter(status__in=['pending', 'pending_hr']).count()
        approved_leaves = Leave.objects.filter(status='approved').count()
        rejected_leaves = Leave.objects.filter(status='rejected').count()

        # Per-department breakdown (Phase 2.6 dashboard). Only a handful of
        # departments, so a few small counts each is fine.
        from leaves.models import Department
        by_department = []
        for d in Department.objects.filter(is_active=True).order_by('name'):
            members = User.objects.filter(department_ref=d)
            dept_leaves = Leave.objects.filter(user__department_ref=d, is_deleted=False)
            by_department.append({
                'id': str(d.id),
                'department': d.name,
                'code': d.code,
                'employee_count': members.count(),
                'active_employees': members.filter(is_active=True).count(),
                'leave_requests': dept_leaves.count(),
                'pending_reviews': dept_leaves.filter(status__in=['pending', 'pending_hr']).count(),
            })

        recent_leaves = Leave.objects.order_by('-created_at')[:10]
        recent_leaves_data = []
        for leave in recent_leaves:
            recent_leaves_data.append({
                'id': str(leave.id),
                'user_name': leave.user.get_full_name() or leave.user.username,
                'leave_type': leave.get_leave_type_display(),
                'start_date': str(leave.start_date),
                'end_date': str(leave.end_date),
                'status': leave.status,
                'created_at': leave.created_at.isoformat(),
            })

        return Response({
            'total_users': total_users,
            'active_users': active_users,
            'total_leaves': total_leaves,
            'pending_leaves': pending_leaves,
            'approved_leaves': approved_leaves,
            'rejected_leaves': rejected_leaves,
            'by_department': by_department,
            'recent_leaves': recent_leaves_data,
        })


class AdminLeaveViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveSerializer
    permission_classes = [IsAdminOrSuperuser]
    filterset_class = LeaveFilter
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'reason']
    ordering_fields = ['created_at', 'start_date', 'end_date', 'status']

    def get_queryset(self):
        return Leave.objects.select_related('user', 'approver').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save()
        log_action(self.request.user, AuditLog.Action.CREATE, instance=serializer.instance, request=self.request)

    def perform_update(self, serializer):
        serializer.save()
        log_action(self.request.user, AuditLog.Action.UPDATE, instance=serializer.instance, request=self.request)

    def perform_destroy(self, instance):
        log_action(self.request.user, AuditLog.Action.DELETE, instance=instance, request=self.request)
        instance.delete()


class AdminBalanceViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAdminOrSuperuser]

    def get_queryset(self):
        return LeaveBalance.objects.select_related('user').order_by('user__username')

    def perform_create(self, serializer):
        serializer.save()
        log_action(self.request.user, AuditLog.Action.CREATE, instance=serializer.instance, request=self.request)

    def perform_update(self, serializer):
        serializer.save()
        log_action(self.request.user, AuditLog.Action.UPDATE, instance=serializer.instance, request=self.request)

    def perform_destroy(self, instance):
        log_action(self.request.user, AuditLog.Action.DELETE, instance=instance, request=self.request)
        instance.delete()
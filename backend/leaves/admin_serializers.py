"""Serializers used only by the HR/Admin endpoints (leaves/admin_views.py)."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import (
    Department, EnterpriseLeaveBalance, Holiday, LeavePolicy, LeaveType,
    MonthlyLeaveSummary,
)

User = get_user_model()


class EmployeeSummarySerializer(serializers.ModelSerializer):
    """Row for the admin employee list: identity plus this-year leave stats."""
    full_name = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    used_days = serializers.SerializerMethodField()
    available_days = serializers.SerializerMethodField()
    attendance_percentage = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'email', 'role', 'department', 'is_active',
            'used_days', 'available_days', 'attendance_percentage',
        ]

    def _year(self):
        return self.context.get('year') or timezone.now().year

    def _stats(self, obj):
        cached = getattr(obj, '_lr_stats', None)
        if cached is not None:
            return cached
        year = self._year()
        balances = list(EnterpriseLeaveBalance.objects.filter(user=obj, year=year))
        used = sum((b.used_days for b in balances), Decimal('0'))
        available = sum((b.available_days for b in balances), Decimal('0'))
        atts = [m.attendance_percentage for m in MonthlyLeaveSummary.objects.filter(user=obj, year=year)]
        attendance = (sum(atts, Decimal('0')) / len(atts)) if atts else Decimal('100')
        stats = {'used': used, 'available': available, 'attendance': attendance}
        obj._lr_stats = stats
        return stats

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_department(self, obj):
        if getattr(obj, 'department_ref', None):
            return obj.department_ref.code
        return obj.department or None

    def get_used_days(self, obj):
        return str(self._stats(obj)['used'])

    def get_available_days(self, obj):
        return str(self._stats(obj)['available'])

    def get_attendance_percentage(self, obj):
        return str(round(self._stats(obj)['attendance'], 2))


class BalanceAdjustmentSerializer(serializers.Serializer):
    """Payload for POST .../employees/{id}/adjust-balance/."""
    leave_type = serializers.CharField(help_text="LeaveType code, e.g. ANNUAL")
    year = serializers.IntegerField()
    delta = serializers.DecimalField(max_digits=6, decimal_places=2)
    reason = serializers.CharField(min_length=5)

    def validate_leave_type(self, value):
        if not LeaveType.objects.filter(code__iexact=value).exists():
            raise serializers.ValidationError(f"Unknown leave type code '{value}'.")
        return value.upper()


class AdminLeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = [
            'id', 'code', 'name', 'default_days_per_year', 'is_paid',
            'allow_half_day', 'allow_carry_forward', 'max_carry_forward_days',
            'requires_document', 'min_notice_days', 'is_active', 'display_color',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AdminDepartmentSerializer(serializers.ModelSerializer):
    head_name = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'head', 'head_name', 'parent', 'is_active', 'member_count']

    def get_head_name(self, obj):
        return obj.head.get_full_name() if obj.head else None

    def get_member_count(self, obj):
        return obj.members.count()


class AdminLeavePolicySerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)
    department_code = serializers.CharField(source='department.code', read_only=True, default=None)
    is_effective_now = serializers.SerializerMethodField()

    class Meta:
        model = LeavePolicy
        fields = [
            'id', 'leave_type', 'leave_type_code', 'department', 'department_code',
            'role', 'days_per_year', 'effective_from', 'effective_until',
            'created_by', 'created_at', 'is_effective_now',
        ]
        read_only_fields = ['id', 'created_by', 'created_at']

    def validate_role(self, value):
        # Treat empty string as "all roles" (NULL) so scope comparisons and the
        # unique constraint behave consistently.
        return value or None

    def get_is_effective_now(self, obj):
        from django.utils import timezone
        today = timezone.now().date()
        if obj.effective_from > today:
            return False
        return obj.effective_until is None or obj.effective_until >= today


class AdminHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ['id', 'date', 'name', 'holiday_type', 'description', 'is_active']


class BulkLeaveActionSerializer(serializers.Serializer):
    """Payload for POST .../leaves/bulk-action/."""
    leave_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    comment = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        if attrs['action'] == 'reject' and len(attrs.get('comment', '').strip()) < 5:
            raise serializers.ValidationError(
                {'comment': 'A reason (>= 5 chars) is required when rejecting.'}
            )
        return attrs

from rest_framework import serializers

from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.get_full_name", read_only=True)
    employee_id = serializers.CharField(source="employee.employee_id", read_only=True)
    department_name = serializers.CharField(source="employee.department_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    date_bs = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = [
            "id", "employee", "employee_name", "employee_id", "department_name",
            "date", "date_bs", "check_in", "check_out", "status", "status_display",
            "working_hours", "remarks", "marked_by", "created_at",
        ]
        read_only_fields = fields

    def get_date_bs(self, obj):
        from config.nepali_dates import to_bs
        return to_bs(obj.date)


class ManualAttendanceSerializer(serializers.Serializer):
    """HR/Admin manual entry or correction."""
    employee = serializers.UUIDField()
    date = serializers.DateField()
    status = serializers.ChoiceField(choices=Attendance.Status.choices)
    check_in = serializers.DateTimeField(required=False, allow_null=True)
    check_out = serializers.DateTimeField(required=False, allow_null=True)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")

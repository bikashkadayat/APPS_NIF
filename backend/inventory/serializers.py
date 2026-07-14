from rest_framework import serializers

from config.nepali_dates import to_bs
from .models import InventoryCategory, InventoryItem, ItemAssignment, TakeOutRequest


class InventoryCategorySerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(source="items.count", read_only=True)

    class Meta:
        model = InventoryCategory
        fields = ["id", "name", "description", "item_count", "created_at"]
        read_only_fields = ["id", "created_at"]


class ItemAssignmentSerializer(serializers.ModelSerializer):
    assigned_date_bs = serializers.SerializerMethodField()
    handover_condition_display = serializers.CharField(source="get_handover_condition_display", read_only=True, default="")
    return_condition_display = serializers.CharField(source="get_return_condition_display", read_only=True, default="")

    class Meta:
        model = ItemAssignment
        fields = [
            "id", "item", "assigned_to", "assigned_to_name", "assigned_by",
            "assigned_by_name", "note", "assigned_date", "assigned_date_bs",
            "handover_condition", "handover_condition_display", "accessories",
            "is_handover", "return_condition", "return_condition_display",
            "return_remarks", "assigned_at", "returned_at", "is_active",
        ]
        read_only_fields = fields

    def get_assigned_date_bs(self, obj):
        return to_bs(obj.assigned_date) if obj.assigned_date else None


class AssignmentBoardSerializer(serializers.ModelSerializer):
    """Row for the 'who has what' board / My Assigned Assets — one active
    assignment enriched with the item + holder details needed at a glance."""
    item_code = serializers.CharField(source="item.asset_code", read_only=True, default="")
    item_name = serializers.CharField(source="item.name", read_only=True, default="")
    item_status = serializers.CharField(source="item.status", read_only=True, default="")
    item_status_display = serializers.CharField(source="item.get_status_display", read_only=True, default="")
    asset_type = serializers.CharField(source="item.get_asset_type_display", read_only=True, default="")
    category = serializers.CharField(source="item.category_id", read_only=True, default=None)
    category_name = serializers.CharField(source="item.category.name", read_only=True, default=None)
    spec = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    assigned_date_bs = serializers.SerializerMethodField()
    handover_condition_display = serializers.CharField(source="get_handover_condition_display", read_only=True, default="")

    class Meta:
        model = ItemAssignment
        fields = [
            "id", "item", "item_code", "item_name", "item_status", "item_status_display",
            "asset_type", "category", "category_name", "spec",
            "assigned_to", "assigned_to_name", "department_name",
            "assigned_by_name", "assigned_date", "assigned_date_bs",
            "handover_condition", "handover_condition_display", "accessories",
            "note", "is_handover", "is_active",
        ]
        read_only_fields = fields

    def get_spec(self, obj):
        it = obj.item
        if not it:
            return ""
        bits = [it.brand, it.model, it.cpu, it.ram]
        return " · ".join(b for b in bits if b) or (it.serial_number or "")

    def get_department_name(self, obj):
        u = obj.assigned_to
        dep = getattr(u, "department_ref", None) if u else None
        return dep.name if dep else (getattr(u, "department", None) or None)

    def get_assigned_date_bs(self, obj):
        return to_bs(obj.assigned_date) if obj.assigned_date else None


class InventoryItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    condition_display = serializers.CharField(source="get_condition_display", read_only=True)
    asset_type_display = serializers.CharField(source="get_asset_type_display", read_only=True)
    is_it_asset = serializers.BooleanField(read_only=True)
    current_holder = serializers.SerializerMethodField()
    current_holder_id = serializers.SerializerMethodField()
    assigned_date = serializers.SerializerMethodField()
    assigned_date_bs = serializers.SerializerMethodField()
    purchase_date_bs = serializers.SerializerMethodField()
    warranty_expiry_bs = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = [
            "id", "asset_code", "name", "asset_type", "asset_type_display", "is_it_asset",
            "category", "category_name", "serial_number", "department", "department_name",
            "status", "status_display", "condition", "condition_display",
            "purchase_date", "purchase_date_bs", "notes",
            # device specifications
            "brand", "model", "cpu", "ram", "storage_type", "storage_size", "gpu",
            "screen_size", "os", "mac_address", "ip_address", "warranty_expiry",
            "warranty_expiry_bs", "purchase_cost", "vendor", "accessories", "specifications",
            # holder-at-a-glance
            "current_holder", "current_holder_id", "assigned_date", "assigned_date_bs",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "asset_code", "created_at", "updated_at"]

    def get_current_holder(self, obj):
        a = obj.active_assignment
        return a.assigned_to_name if a else None

    def get_current_holder_id(self, obj):
        a = obj.active_assignment
        return str(a.assigned_to_id) if a and a.assigned_to_id else None

    def get_assigned_date(self, obj):
        a = obj.active_assignment
        return str(a.assigned_date) if a and a.assigned_date else None

    def get_assigned_date_bs(self, obj):
        a = obj.active_assignment
        return to_bs(a.assigned_date) if a and a.assigned_date else None

    def get_purchase_date_bs(self, obj):
        return to_bs(obj.purchase_date) if obj.purchase_date else None

    def get_warranty_expiry_bs(self, obj):
        return to_bs(obj.warranty_expiry) if obj.warranty_expiry else None


class TakeOutRequestSerializer(serializers.ModelSerializer):
    item_code = serializers.CharField(read_only=True)
    item_name = serializers.CharField(read_only=True)
    requested_by_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    purpose_display = serializers.CharField(source="get_purpose_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    expected_out_date_bs = serializers.SerializerMethodField()
    expected_return_date_bs = serializers.SerializerMethodField()
    actual_return_date_bs = serializers.SerializerMethodField()
    created_at_bs = serializers.SerializerMethodField()

    class Meta:
        model = TakeOutRequest
        fields = [
            "id", "reference", "item", "item_code", "item_name",
            "requested_by", "requested_by_name", "department", "department_name",
            "purpose", "purpose_display", "reason",
            "expected_out_date", "expected_out_date_bs",
            "expected_return_date", "expected_return_date_bs",
            "status", "status_display", "approver", "approver_name",
            "approver_remarks", "action_date",
            "actual_return_date", "actual_return_date_bs", "created_at_bs",
            "created_at", "updated_at",
        ]
        # Server-set fields the client can never write directly.
        read_only_fields = [
            "id", "reference", "item_code", "item_name", "requested_by",
            "requested_by_name", "department", "status", "approver", "approver_name",
            "approver_remarks", "action_date", "actual_return_date",
            "created_at", "updated_at",
        ]

    def _bs(self, d):
        return to_bs(d) if d else None

    def get_expected_out_date_bs(self, obj):
        return self._bs(obj.expected_out_date)

    def get_expected_return_date_bs(self, obj):
        return self._bs(obj.expected_return_date)

    def get_actual_return_date_bs(self, obj):
        return self._bs(obj.actual_return_date)

    def get_created_at_bs(self, obj):
        return self._bs(obj.created_at)

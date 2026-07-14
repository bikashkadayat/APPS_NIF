from django.contrib import admin

from .models import (
    InventoryCategory, InventoryItem, ItemAssignment, TakeOutRequest, InventorySequence)


@admin.register(InventoryCategory)
class InventoryCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("asset_code", "name", "category", "status", "condition", "department")
    list_filter = ("status", "condition", "category")
    search_fields = ("asset_code", "name", "serial_number")


@admin.register(ItemAssignment)
class ItemAssignmentAdmin(admin.ModelAdmin):
    list_display = ("item", "assigned_to_name", "assigned_by_name", "is_active", "assigned_at", "returned_at")
    list_filter = ("is_active",)


@admin.register(TakeOutRequest)
class TakeOutRequestAdmin(admin.ModelAdmin):
    list_display = ("reference", "item_code", "requested_by_name", "purpose", "status", "created_at")
    list_filter = ("status", "purpose")
    search_fields = ("reference", "item_code", "requested_by_name")


admin.site.register(InventorySequence)

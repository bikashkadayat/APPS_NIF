from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AssignmentViewSet, InventoryCategoryViewSet, InventoryItemViewSet,
    ManagerEmployeeListView, TakeOutRequestViewSet)

router = DefaultRouter()
router.register(r"inventory/categories", InventoryCategoryViewSet, basename="inventory-category")
router.register(r"inventory/items", InventoryItemViewSet, basename="inventory-item")
router.register(r"inventory/assignments", AssignmentViewSet, basename="inventory-assignment")
router.register(r"inventory/takeouts", TakeOutRequestViewSet, basename="inventory-takeout")

urlpatterns = router.urls + [
    path("inventory/employees/", ManagerEmployeeListView.as_view(), name="inventory-employees"),
]

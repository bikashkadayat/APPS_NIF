"""User-related helpers (employee id generation)."""
from django.db import transaction
from django.utils import timezone

from .models import User


@transaction.atomic
def generate_employee_id():
    """Return the next employee id: NIFN-EMP-YYYY-XXXX (sequential per year)."""
    year = timezone.now().year
    prefix = f"NIFN-EMP-{year}-"
    last = (
        User.objects.select_for_update()
        .filter(employee_id__startswith=prefix)
        .order_by("-employee_id").first()
    )
    seq = int(last.employee_id.rsplit("-", 1)[-1]) + 1 if last and last.employee_id else 1
    return f"{prefix}{seq:04d}"

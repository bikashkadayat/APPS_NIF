"""
Phase 4 backfill: resolve a leave category for every existing user and generate
their category-driven LeaveBalance rows for the current year. Flagged/fallback
cases are left with user.category_flag set so the HR review list surfaces them.

Idempotent (re-resolves + refreshes allocations), non-destructive (never lowers
used_so_far, which is derived), reverse is a no-op.
"""
from django.db import migrations


def backfill(apps, schema_editor):
    # Import live helpers: this runs at migration head, so the model layer matches.
    from django.utils import timezone
    from leaves import category_engine
    from django.contrib.auth import get_user_model

    User = get_user_model()
    year = timezone.localdate().year
    flagged = []

    for user in User.objects.all():
        try:
            # Default maternity/paternity eligibility from gender if still at the
            # zero-default (existing rows: gender undisclosed => both stay False).
            mat, pat = category_engine.default_eligibility(user.gender)
            update_fields = []
            if user.gender == User.Gender.FEMALE and not user.maternity_eligible:
                user.maternity_eligible = True; update_fields.append("maternity_eligible")
            if user.gender == User.Gender.MALE and not user.paternity_eligible:
                user.paternity_eligible = True; update_fields.append("paternity_eligible")
            if update_fields:
                user.save(update_fields=update_fields)

            category, flag = category_engine.resolve_and_cache(user)
            category_engine.ensure_category_balances(user, year)
            if flag:
                flagged.append((user.get_username(), category, flag))
        except Exception:
            # Never block the deploy on one bad row; the HR review list + nightly
            # integrity audit will surface anything left unresolved.
            continue

    if flagged:
        print(f"\n[category backfill] {len(flagged)} user(s) flagged for HR review:")
        for username, category, flag in flagged:
            print(f"  - {username} [{category}]: {flag}")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("leaves", "0013_seed_entitlement_matrix"),
        # Depend on the LATEST users migration that adds columns: this backfill
        # calls live model code (User.objects.all()), so every User column the
        # current model declares must already exist. Without this, a fresh
        # `migrate` can run this before users.0008 and fail on `address`.
        ("users", "0008_user_address_user_bio_user_date_of_birth_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]

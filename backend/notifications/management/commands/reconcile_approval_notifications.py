from django.core.management.base import BaseCommand

from notifications.reconcile import reconcile_stale_approvals


class Command(BaseCommand):
    help = "Mark stale 'awaiting your review' notifications read (reconcile bell with the actionable queue)."

    def handle(self, *args, **options):
        n = reconcile_stale_approvals()
        self.stdout.write(self.style.SUCCESS(f"Reconciled {n} stale approval notification(s)."))

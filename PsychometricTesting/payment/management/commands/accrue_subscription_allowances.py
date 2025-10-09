from django.core.management.base import BaseCommand
from django.utils import timezone

from payment.subscription_service import record_monthly_accruals


class Command(BaseCommand):
    help = "Record monthly test allowance accruals for active subscriptions."

    def handle(self, *args, **options):
        processed = record_monthly_accruals(reference_time=timezone.now())
        self.stdout.write(self.style.SUCCESS(f"Processed {processed} subscription(s)."))

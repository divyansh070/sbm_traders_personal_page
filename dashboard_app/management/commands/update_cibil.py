from django.core.management.base import BaseCommand
from dashboard_app.models import Customer

class Command(BaseCommand):
    help = 'Recalculate all customer CIBIL scores'

    def handle(self, *args, **options):
        self.stdout.write('Updating CIBIL scores for all customers...')
        customers = Customer.objects.all()
        for customer in customers:
            customer.calculate_cibil_v1()
            customer.calculate_cibil_v2()
        self.stdout.write(self.style.SUCCESS(f'Successfully updated CIBIL scores (V1 & V2) for {customers.count()} customers.'))

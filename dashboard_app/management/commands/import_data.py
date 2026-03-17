import pandas as pd
from django.core.management.base import BaseCommand
from dashboard_app.models import Customer, Payment
from django.db.models import Max
from utils import get_processed_data
import os

class Command(BaseCommand):
    help = 'Import data from Customer_Payment.xlsx'

    def handle(self, *args, **options):
        file_path = 'Customer_Payment.xlsx'
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File "{file_path}" not found.'))
            return

        self.stdout.write('Processing data...')
        df = get_processed_data(file_path)

        if df is None:
            self.stdout.write(self.style.ERROR('Failed to process data.'))
            return

        # Clear existing data (optional, but good for a full sync)
        Payment.objects.all().delete()
        Customer.objects.all().delete()

        customers_created = 0
        payments_created = 0

        for _, row in df.iterrows():
            customer_id_str = str(row['CustomerID'])
            customer_name = str(row['Customer Name'])
            
            customer, created = Customer.objects.get_or_create(
                customer_id_str=customer_id_str,
                defaults={'name': customer_name}
            )
            if created:
                customers_created += 1

            # Convert NaT/NaN to None for Django
            date = row['Date'] if pd.notnull(row['Date']) else None
            inv_date = row['Invoice Date'] if pd.notnull(row['Invoice Date']) else None

            Payment.objects.create(
                customer=customer,
                date=date,
                invoice_date=inv_date,
                amount=row['Amount'],
                unused_amount=row['Unused Amount'],
                payment_status=row['Payment_Status'],
                delay=int(row['Delay']),
                late_only_delay=int(row['Late_Only_Delay'])
            )
            payments_created += 1

        # Recalculate CIBIL for all customers after import
        self.stdout.write('Recalculating CIBIL scores (V1 & V2)...')
        for customer in Customer.objects.all():
            # Update last_order_date
            latest_payment = customer.payments.aggregate(Max('date'))['date__max']
            if latest_payment:
                customer.last_order_date = latest_payment
            customer.calculate_cibil_v1()
            customer.calculate_cibil_v2()

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {customers_created} customers and {payments_created} payments. Both CIBIL scores updated.'))

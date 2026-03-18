import pandas as pd
from django.core.management.base import BaseCommand
from dashboard_app.models import Customer, Payment
from django.db.models import Max
from utils import get_processed_data, import_from_dataframe
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

        customers_created, payments_created = import_from_dataframe(df)

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {customers_created} customers and {payments_created} payments. Both CIBIL scores updated.'))

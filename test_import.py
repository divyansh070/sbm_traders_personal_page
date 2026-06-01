import os
import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sbm_website.settings')
django.setup()

from utils import load_data, clean_data, calculate_features, import_from_dataframe
from dashboard_app.models import Customer, Payment

print("Testing AR Aging + Payments Received Upsert Logic...")

print("\n--- 1. Importing Payments Received ---")
df1 = load_data('Payments Received.xlsx')
df1 = clean_data(df1)
df1 = calculate_features(df1)
import_from_dataframe(df1)
print(f"Customers: {Customer.objects.count()}, Payments: {Payment.objects.count()}")

print("\n--- 2. Importing AR Aging Details ---")
df2 = load_data('AR Aging Details By Invoice Due Date.xls')
df2 = clean_data(df2)
df2 = calculate_features(df2)
import_from_dataframe(df2)
print(f"Customers: {Customer.objects.count()}, Payments: {Payment.objects.count()}")

# Print a customer to see if their payments combine
customer = Customer.objects.filter(payments__isnull=False).first()
if customer:
    print(f"\n--- Checking Customer: {customer.name} ---")
    for p in customer.payments.all():
        print(f"  Payment ID: {p.external_id}, Amount: {p.amount}, Date: {p.date}, Inv Date: {p.invoice_date}")

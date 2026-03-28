import pandas as pd
import numpy as np
from datetime import datetime

def load_data(filepath):
    """
    Loads the Excel file and drops completely empty columns.
    """
    try:
        df = pd.read_excel(filepath)
        # Drop columns that are completely empty
        df_cleaned = df.dropna(axis=1, how='all')
        return df_cleaned
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def clean_data(df):
    """
    Drops specific unwanted columns from the DataFrame.
    """
    columns_to_drop = [
        'Description', 'Exchange Rate', 'Bank Charges', 'Currency Code', 
        'Branch ID', 'Payment Type', 'Location Name', 'Withholding Tax Amount',
        'Payment Number', 'CustomerPayment ID', 'Mode', 'Payment Type.1', 
        'Deposit To', 'Payment Status'
    ]
    
    # Drop columns if they exist
    df_cleaned = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors='ignore')
    return df_cleaned

def calculate_payment_fraction(row):
    """
    Calculates the ratio of Unused Amount to Amount.
    """
    try:
        if row['Amount'] == 0:
            return 0
        return row['Unused Amount'] / row['Amount']
    except Exception:
        return 0

def calculate_features(df, credit_terms=0):
    """
    Adds calculated features: Payment_Fraction, Days_Delayed, Late_Only_Delay.
    Handles missing Invoice Date by assuming payment on the same day.
    Handles missing Payment Date (Unpaid) by calculating delay relative to Today.
    """
    # Create copy to avoid SettingWithCopyWarning
    df = df.copy()

    # Apply Payment Fraction
    df['Payment_Fraction'] = df.apply(calculate_payment_fraction, axis=1)
    
    # Ensure datetime format
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Invoice Date'] = pd.to_datetime(df['Invoice Date'], errors='coerce')
    df['Invoice Date'] = df['Invoice Date'].fillna(df['Date'])

    current_date = pd.Timestamp.now().normalize()
    
    # Status Logic:
    # 1. Unused Amount > 1 -> Pending Payment 
    # 2. Unused Amount <= 1 -> Paid
    df['Payment_Status'] = np.where(df['Unused Amount'] > 1, 'Pending', 'Paid')
    
    # Calculate Delay
    def get_delay(row):
        unused = row.get('Unused Amount', 0)
        p_date = row.get('Date')
        inv_date = row.get('Invoice Date')
        
        if unused > 1:
            # Partially Paid or Unpaid: Delay is dynamic up to today
            start_date = p_date if pd.notnull(p_date) else inv_date
            return (current_date - start_date).days if pd.notnull(start_date) else 0
        else:
            # Fully Paid: Delay is frozen at exactly when they paid
            if pd.notnull(p_date) and pd.notnull(inv_date):
                return (p_date - inv_date).days
            return 0
            
    df['Days_to_Pay'] = df.apply(get_delay, axis=1)
    df['Delay'] = df['Days_to_Pay'] - credit_terms
    df['Late_Only_Delay'] = df['Delay'].apply(lambda x: x if x > 0 else 0)
    
    return df

def get_processed_data(filepath_or_buffer):
    """
    Orchestrates the loading, cleaning, and feature engineering.
    Can accept a string filepath or a file-like object (like Django's UploadedFile).
    """
    df = load_data(filepath_or_buffer)
    if df is not None:
        df = clean_data(df)
        df = calculate_features(df)
    return df

def import_from_dataframe(df):
    """
    Takes a processed DataFrame and performs the optimized bulk import
    and CIBIL logic. Returns the number of customers and payments created.
    """
    from dashboard_app.models import Customer, Payment
    from django.db.models import Max
    
    # 1. Clear existing data
    # Deleting customers automatically deletes associated payments due to CASCADE
    Customer.objects.all().delete()

    # 2. Bulk create Customers
    unique_customers_df = df.drop_duplicates(subset=['CustomerID'])
    customers_to_create = [
        Customer(
            customer_id_str=str(row['CustomerID']), 
            name=str(row['Customer Name'])
        )
        for _, row in unique_customers_df.iterrows()
    ]
    Customer.objects.bulk_create(customers_to_create, batch_size=500)

    # Build mapping of customer_id_str -> Customer instance for quick lookup
    customer_map = {c.customer_id_str: c for c in Customer.objects.all()}

    # 3. Bulk create Payments
    payments_to_create = []
    for _, row in df.iterrows():
        customer_id_str = str(row['CustomerID'])
        customer = customer_map.get(customer_id_str)
        if not customer:
            continue
            
        date = row['Date'] if pd.notnull(row['Date']) else None
        inv_date = row['Invoice Date'] if pd.notnull(row['Invoice Date']) else None

        payments_to_create.append(
            Payment(
                customer=customer,
                date=date,
                invoice_date=inv_date,
                amount=row['Amount'],
                unused_amount=row['Unused Amount'],
                payment_status=row['Payment_Status'],
                delay=int(row['Delay']),
                late_only_delay=int(row['Late_Only_Delay'])
            )
        )
        
    Payment.objects.bulk_create(payments_to_create, batch_size=2000)

    # 4. Recalculate CIBIL for all customers footprint-efficiently
    customers_to_update = []
    
    customers_with_max_date = Customer.objects.annotate(
        latest_payment_date=Max('payments__date')
    )
    
    # Pre-load all payments into memory (1 Query total for 900-50,000 rows, fast)
    from collections import defaultdict
    all_payments = Payment.objects.all()
    payments_by_customer = defaultdict(list)
    for p in all_payments:
        payments_by_customer[p.customer_id].append(p)
    
    for customer in customers_with_max_date:
        if customer.latest_payment_date:
            customer.last_order_date = customer.latest_payment_date
        
        # Calculate scores completely in-memory (0 database roundtrips)
        cust_payments = payments_by_customer.get(customer.id, [])
        customer.calculate_cibil_v1(save=False, payments_list=cust_payments)
        customer.calculate_cibil_v2(save=False, payments_list=cust_payments)
        customers_to_update.append(customer)

    # Bulk update computed fields
    Customer.objects.bulk_update(
        customers_to_update, 
        ['last_order_date', 'cibil_score_v1', 'cibil_score_v2'],
        batch_size=500
    )
    
    return len(customers_to_create), len(payments_to_create)

import pandas as pd
import numpy as np
from datetime import datetime
import os
import json
import re
import requests
import io

def agentic_map_columns(excel_columns):
    """
    Asks the AI to match the uploaded Excel columns to our required database columns.
    Uses fallback deterministic logic if API key isn't provided or call fails.
    """
    required_columns = ["Date", "Invoice Date", "CustomerID", "Customer Name", "Amount", "Unused Amount", "External ID"]
    excel_cols_list = list(excel_columns)
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            You are a data pipeline assistant. 
            Match the following uploaded Excel columns to our system's required columns.
            
            Uploaded Columns: {excel_cols_list}
            Required System Columns: {required_columns}
            
            Return ONLY a valid JSON dictionary where the keys are the Uploaded Columns and the values are the Required System Columns. 
            If an uploaded column doesn't match any required column, DO NOT include it in the dictionary.
            """
            response = model.generate_content(prompt)
            # Find JSON block if hidden in markdown
            text = response.text.strip()
            if "```" in text:
                text = text.split("```")[1].strip()
                if text.startswith("json"):
                    text = text[4:].strip()
            return json.loads(text)
        except Exception as e:
            print(f"Agentic mapping failed: {e}. Falling back to heuristic mapping.")
            
    # Fallback heuristic mapping
    rename_map = {}
    
    # Check if this is likely an AR Aging report (has balance)
    has_balance = any('balance' in str(c).lower().strip() for c in excel_cols_list)
    
    for col in excel_cols_list:
        lower_col = str(col).lower().strip()
        if lower_col in ['payment date', 'receipt date', 'payment_date', 'date', 'last payment date']:
            rename_map[col] = 'Date'
        elif lower_col in ['customer id', 'customer_id']:
            rename_map[col] = 'CustomerID'
        elif lower_col in ['customer name', 'customer_name']:
            rename_map[col] = 'Customer Name'
        elif lower_col in ['amount', 'payment amount']:
            # If it's an AR aging report, ignore the total 'amount' and use 'balance' instead
            if not has_balance:
                rename_map[col] = 'Amount'
        elif lower_col in ['unused amount', 'unused_amount']:
            rename_map[col] = 'Unused Amount'
        elif lower_col in ['invoice date', 'invoice_date', 'due_date', 'due date']:
            rename_map[col] = 'Invoice Date'
        elif lower_col in ['customerpayment id', 'entity_id', 'transaction_number', 'payment number']:
            rename_map[col] = 'External ID'
        elif lower_col in ['balance']:
            rename_map[col] = 'Amount'
    return rename_map

def load_data(filepath):
    """
    Loads the Excel file and drops completely empty columns.
    Handles Zoho/Tally export format with title in first row.
    """
    try:
        df = pd.read_excel(filepath)
        
        # Check if the headers are actually in the first row (Zoho export format)
        if any('Unnamed:' in str(c) for c in df.columns):
            # The real headers are in the first row of data
            new_headers = df.iloc[0]
            df = df[1:]
            df.columns = new_headers
            df.reset_index(drop=True, inplace=True)
            
        # Drop columns that are completely empty
        df_cleaned = df.dropna(axis=1, how='all')
        
        # Ensure column names are strings before stripping
        df_cleaned.columns = df_cleaned.columns.astype(str).str.strip()
        
        # Map common alternatives to expected Capitalized names
        rename_map = {}
        # for col in df_cleaned.columns:
        #     lower_col = col.lower()
        #     if lower_col in ['payment date', 'receipt date', 'payment_date', 'date']:
        #         rename_map[col] = 'Date'
        #     elif lower_col in ['customer id', 'customer_id']:
        #         rename_map[col] = 'CustomerID'
        #     elif lower_col in ['customer name', 'customer_name']:
        #         rename_map[col] = 'Customer Name'
        #     elif lower_col in ['amount', 'payment amount']:
        #         rename_map[col] = 'Amount'
        #     elif lower_col in ['unused amount', 'unused_amount']:
        #         rename_map[col] = 'Unused Amount'
        #     elif lower_col in ['invoice date', 'invoice_date']:
        #         rename_map[col] = 'Invoice Date'
        rename_map = agentic_map_columns(df_cleaned.columns)
        
        if rename_map:
            df_cleaned = df_cleaned.rename(columns=rename_map)
            df_cleaned = df_cleaned.loc[:, ~df_cleaned.columns.duplicated()]
            
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
    Given a raw, cleaned dataframe, calculates the required CIBIL features
    like Delays, Penalties, Payment Fractions, etc.
    Handles missing Invoice Date by assuming payment on the same day.
    Handles missing Payment Date (Unpaid) by calculating delay relative to Today.
    """
    
    # FIX: In 'Payments Received' exports, a single payment clearing multiple invoices 
    # repeats the total Payment Amount on every row, massively inflating totals.
    # We must use the 'Amount Applied to Invoice' if it exists.
    applied_col = None
    for col in df.columns:
        if 'applied' in col.lower() and 'amount' in col.lower():
            applied_col = col
            break
            
    if applied_col:
        # Replace the 'Amount' with the specific amount applied to this invoice row.
        # If it's an unapplied advance (NaN), fall back to the total Amount.
        df['Effective_Amount'] = df[applied_col].fillna(df.get('Amount', 0))
        df['Amount'] = df['Effective_Amount']

    if 'Amount' not in df.columns:
        df['Amount'] = 0
        
    if 'Unused Amount' not in df.columns:
        df['Unused Amount'] = 0
        
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    
    # Check if this dataframe natively has 'External ID' before we synthesize it.
    # Native External ID implies it's a Payments file.
    has_external_id = 'External ID' in df.columns
    
    if has_external_id:
        # It's a payment file. Keep everything except maybe nulls, but we already filled na with 0.
        # We keep 0 (e.g. CUST-016) and negative (Refunds, e.g. CUST-011).
        pass
    else:
        # It's an invoice file. Drop Amount == 0 to prevent double counting fully paid invoices, 
        # and to ignore dummy zero-dollar invoices (e.g. CUST-015).
        # We KEEP negative amounts (Refunds).
        df = df[df['Amount'] != 0]
        
    if 'External ID' not in df.columns:
        # Generate a synthetic external ID based on unique attributes to prevent total duplication
        df['External ID'] = df.apply(lambda row: f"{row.get('CustomerID', 'unknown')}_{row.get('Invoice Date', 'unknown')}_{row.get('Amount', 0)}_{hash(str(row))}", axis=1)

    # Create copy to avoid SettingWithCopyWarning
    df = df.copy()

    # Apply Payment Fraction
    df['Payment_Fraction'] = df.apply(calculate_payment_fraction, axis=1)
    
    # Ensure datetime format
    if 'Date' not in df.columns:
        df['Date'] = pd.Timestamp.now().normalize()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    if 'Invoice Date' not in df.columns:
        df['Invoice Date'] = df['Date']
    else:
        df['Invoice Date'] = pd.to_datetime(df['Invoice Date'], errors='coerce')
        df['Invoice Date'] = df['Invoice Date'].fillna(df['Date'])

    current_date = pd.Timestamp.now().normalize()
    
    # Status Logic:
    # If the payment date is missing, it's an unpaid AR Aging invoice.
    # In a Payments Received report, Unused Amount represents unapplied Advance Credit.
    df['Payment_Status'] = np.where(
        df['Date'].isnull(), 
        'Pending',
        np.where(df['Unused Amount'] > 1, 'Advance', 'Paid')
    )
    
    # Calculate Delay
    def get_delay(row):
        p_date = row.get('Date')
        inv_date = row.get('Invoice Date')
        
        if pd.notnull(p_date) and pd.notnull(inv_date):
            # Payment was made. Delay is frozen at the payment date.
            return (p_date - inv_date).days
        elif pd.isnull(p_date) and pd.notnull(inv_date):
            # Invoice exists but no payment date (Unpaid Invoice).
            # Delay grows dynamically up to today.
            return (current_date - inv_date).days
        
        # Pure advance or missing dates
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

def get_processed_data_from_google_sheet(url):
    """
    Downloads a Google Sheet via its public share URL, processes it, and returns the dataframe.
    """
    try:
        # Extract the Document ID from the URL
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if not match:
            print("Invalid Google Sheet URL format.")
            return None
        
        sheet_id = match.group(1)
        # Construct the CSV export URL
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        
        # Download the CSV
        response = requests.get(export_url)
        response.raise_for_status()
        
        # Load it into pandas
        csv_data = io.BytesIO(response.content)
        # We use pd.read_csv instead of pd.read_excel since we requested a CSV export
        df = pd.read_csv(csv_data)
        
        # Check if the headers are actually in the first row (Zoho export format)
        if any('Unnamed:' in str(c) for c in df.columns):
            new_headers = df.iloc[0]
            df = df[1:]
            df.columns = new_headers
            df.reset_index(drop=True, inplace=True)
            
        df_cleaned = df.dropna(axis=1, how='all')
        df_cleaned.columns = df_cleaned.columns.astype(str).str.strip()
        
        rename_map = agentic_map_columns(df_cleaned.columns)
        if rename_map:
            df_cleaned = df_cleaned.rename(columns=rename_map)
            df_cleaned = df_cleaned.loc[:, ~df_cleaned.columns.duplicated()]
            
        if df_cleaned is not None:
            df_cleaned = clean_data(df_cleaned)
            df_cleaned = calculate_features(df_cleaned)
        return df_cleaned
    except Exception as e:
        print(f"Error loading from Google Sheet: {e}")
        return None

def import_from_dataframe(df):
    """
    Takes a processed DataFrame and performs the optimized bulk import
    and CIBIL logic. Returns the number of customers and payments created.
    """
    from dashboard_app.models import Customer, Payment
    from django.db.models import Max
    
    # 1. UPSERT Customers
    unique_customers_df = df.drop_duplicates(subset=['CustomerID'])
    customer_ids = unique_customers_df['CustomerID'].astype(str).tolist()
    
    # Pre-fetch existing customers
    existing_customers = {c.customer_id_str: c for c in Customer.objects.filter(customer_id_str__in=customer_ids)}
    
    customers_to_create = []
    customers_to_update = []
    
    for _, row in unique_customers_df.iterrows():
        cid = str(row['CustomerID'])
        name = str(row['Customer Name'])
        if cid in existing_customers:
            c = existing_customers[cid]
            if c.name != name:
                c.name = name
                customers_to_update.append(c)
        else:
            customers_to_create.append(Customer(customer_id_str=cid, name=name))
            
    if customers_to_create:
        Customer.objects.bulk_create(customers_to_create, batch_size=500)
    if customers_to_update:
        Customer.objects.bulk_update(customers_to_update, ['name'], batch_size=500)
        
    # Build mapping of customer_id_str -> Customer instance for quick lookup
    customer_map = {c.customer_id_str: c for c in Customer.objects.filter(customer_id_str__in=customer_ids)}

    # 2. UPSERT Payments
    payments_to_create = []
    for _, row in df.iterrows():
        customer_id_str = str(row['CustomerID'])
        customer = customer_map.get(customer_id_str)
        if not customer:
            continue
            
        date = row['Date'] if pd.notnull(row['Date']) else None
        inv_date = row['Invoice Date'] if pd.notnull(row['Invoice Date']) else None
        external_id = str(row.get('External ID', ''))

        amount = row['Amount'] if pd.notnull(row['Amount']) else 0
        unused_amount = row['Unused Amount'] if pd.notnull(row['Unused Amount']) else 0

        payments_to_create.append(
            Payment(
                customer=customer,
                date=date,
                invoice_date=inv_date,
                amount=amount,
                unused_amount=unused_amount,
                payment_status=row['Payment_Status'],
                delay=int(row['Delay']),
                late_only_delay=int(row['Late_Only_Delay']),
                external_id=external_id
            )
        )
        
    if payments_to_create:
        Payment.objects.bulk_create(
            payments_to_create, 
            batch_size=2000,
            update_conflicts=True,
            unique_fields=['external_id'],
            update_fields=['date', 'invoice_date', 'amount', 'unused_amount', 'payment_status', 'delay', 'late_only_delay']
        )

    # 4. Recalculate CIBIL for all customers footprint-efficiently
    customers_to_update = []
    
    # Pre-load all payments into memory (1 Query total for 900-50,000 rows, fast)
    from collections import defaultdict
    all_payments = Payment.objects.all()
    payments_by_customer = defaultdict(list)
    for p in all_payments:
        payments_by_customer[p.customer_id].append(p)
    
    for customer in Customer.objects.filter(customer_id_str__in=customer_ids):
        # Calculate scores completely in-memory (0 database roundtrips)
        cust_payments = payments_by_customer.get(customer.id, [])
        
        # Calculate last order date ignoring errors (amount <= 0)
        valid_dates = [p.invoice_date for p in cust_payments if p.amount and float(p.amount) > 0 and p.invoice_date]
        if valid_dates:
            customer.last_order_date = max(valid_dates)
        else:
            customer.last_order_date = None
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

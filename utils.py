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

    # Status Logic:
    # 1. Date is NaT -> Pending Payment
    # 2. Date is present -> Paid
    
    # If Date is present but Invoice Date is missing -> Assumed Invoice Date = Payment Date (Delay 0)
    df['Invoice Date'] = df['Invoice Date'].fillna(df['Date'])
    
    # Calculate Delay
    # If Date (Paid Date) exists, use it. If not, use Today to calculate "Pending Delay"
    current_date = pd.Timestamp.now().normalize()
    
    # Create a column for calculation
    # If Date is NaT, use current_date
    df['Calculation_Date'] = df['Date'].fillna(current_date)
    
    df['Days_to_Pay'] = (df['Calculation_Date'] - df['Invoice Date']).dt.days
    df['Delay'] = df['Days_to_Pay'] - credit_terms
    
    # Clean Delay (Negative delay set to 0)
    df['Late_Only_Delay'] = df['Delay'].apply(lambda x: x if x > 0 else 0)
    
    # Explicit Payment Status Column
    df['Payment_Status'] = np.where(df['Date'].isna(), 'Pending', 'Paid')
    
    return df

def get_processed_data(filepath):
    """
    Orchestrates the loading, cleaning, and feature engineering.
    """
    df = load_data(filepath)
    if df is not None:
        df = clean_data(df)
        df = calculate_features(df)
    return df

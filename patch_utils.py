import pandas as pd
import numpy as np
from datetime import datetime

def calculate_payment_fraction(row):
    try:
        if row['Amount'] == 0:
            return 0
        return row['Unused Amount'] / row['Amount']
    except Exception:
        return 0

def calculate_features(df, credit_terms=0):
    df = df.copy()
    df['Payment_Fraction'] = df.apply(calculate_payment_fraction, axis=1)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Invoice Date'] = pd.to_datetime(df['Invoice Date'], errors='coerce')
    df['Invoice Date'] = df['Invoice Date'].fillna(df['Date'])
    
    current_date = pd.Timestamp.now().normalize()
    
    # 1. FIX PAYMENT STATUS
    # If Unused Amount > 1, they still owe money, so it's Pending.
    df['Payment_Status'] = np.where(df['Unused Amount'] > 1, 'Pending', 'Paid')
    
    # 2. FIX DELAY CALCULATION
    def get_delay(row):
        unused = row.get('Unused Amount', 0)
        p_date = row.get('Date')
        inv_date = row.get('Invoice Date')
        
        if unused > 1:
            # Partially Paid or Unpaid: Delay is dynamically ongoing to today
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

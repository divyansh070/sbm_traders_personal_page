import os, django
import pandas as pd
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sbm_website.settings")
django.setup()
from utils import load_data, clean_data, calculate_features

df = load_data('Customer_Payment.xlsx')
df = clean_data(df)
df = calculate_features(df)
chandi = df[df['Customer Name'].str.contains('NEW CHANDIGARH', na=False)]
print(chandi[['Customer Name', 'Date', 'Invoice Date', 'Amount', 'Unused Amount', 'Payment_Status', 'Delay']])

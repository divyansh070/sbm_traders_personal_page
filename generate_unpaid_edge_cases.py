import pandas as pd
from datetime import datetime, timedelta

today = datetime.now()

data = []

# 1. The Ghost Debtor (Massive unpaid amount from 300 days ago)
# V1: Massive penalty because today is 300 days later.
# V2: Score will tank because the median delay is dragged down heavily.
data.append({"Date": None, "Invoice Date": today - timedelta(days=300), "CustomerID": "CUST_GHOST_DEBTOR", "Customer Name": "The Ghost Debtor", "Amount": 500000, "Unused Amount": 0, "External ID": "GHOST_1"})

# 2. The Active Delinquent (Pays some small invoices, but has a massive chunk of money left unpaid from 90 days ago)
# They pay 10k on time, but 500k is unpaid for 90 days.
data.append({"Date": today, "Invoice Date": today, "CustomerID": "CUST_ACTIVE_DELINQUENT", "Customer Name": "Active Delinquent", "Amount": 10000, "Unused Amount": 0, "External ID": "AD_1"})
data.append({"Date": today - timedelta(days=5), "Invoice Date": today - timedelta(days=5), "CustomerID": "CUST_ACTIVE_DELINQUENT", "Customer Name": "Active Delinquent", "Amount": 10000, "Unused Amount": 0, "External ID": "AD_2"})
data.append({"Date": None, "Invoice Date": today - timedelta(days=90), "CustomerID": "CUST_ACTIVE_DELINQUENT", "Customer Name": "Active Delinquent", "Amount": 500000, "Unused Amount": 0, "External ID": "AD_UNPAID_1"})

# 3. The Recent Unpaid (Just missed the deadline 5 days ago)
# V1: Because the weight is now 20, a 5-day delay instantly burns 100 points! (1000 -> 900)
# V2: Should be completely safe in Gold tier because 5 days < 15 days average limit.
data.append({"Date": None, "Invoice Date": today - timedelta(days=5), "CustomerID": "CUST_RECENT_UNPAID", "Customer Name": "Recent Unpaid", "Amount": 50000, "Unused Amount": 0, "External ID": "RU_1"})

# 4. The Fractional Ghost (Paid half on time, left the rest unpaid for 120 days)
# Invoice was 100k. 50k paid. 50k unpaid for 120 days.
data.append({"Date": today - timedelta(days=120), "Invoice Date": today - timedelta(days=120), "CustomerID": "CUST_FRAC_GHOST", "Customer Name": "Fractional Ghost", "Amount": 50000, "Unused Amount": 0, "External ID": "FG_PAID"})
data.append({"Date": None, "Invoice Date": today - timedelta(days=120), "CustomerID": "CUST_FRAC_GHOST", "Customer Name": "Fractional Ghost", "Amount": 50000, "Unused Amount": 0, "External ID": "FG_UNPAID"})

df = pd.DataFrame(data)
# Convert None to empty values for the Excel file
df['Date'] = pd.to_datetime(df['Date'])
df.to_excel("CIBIL_Unpaid_Edge_Cases.xlsx", index=False)
print("Generated CIBIL_Unpaid_Edge_Cases.xlsx!")

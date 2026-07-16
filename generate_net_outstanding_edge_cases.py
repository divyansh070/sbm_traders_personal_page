import pandas as pd
from datetime import datetime, timedelta

today = datetime.now()

data = []

# 1. The Straight Debtor (Net Outstanding: 50k)
data.append({"Date": None, "Invoice Date": today - timedelta(days=30), "CustomerID": "CUST_STRAIGHT", "Customer Name": "Straight Debtor", "Amount": 50000, "Unused Amount": 0, "External ID": "SD_1"})

# 2. The Over-Payer (Net Outstanding: -5k. Should NOT appear on pending collections)
# They owe 10k, but have an unapplied advance of 15k.
data.append({"Date": None, "Invoice Date": today - timedelta(days=10), "CustomerID": "CUST_OVERPAY", "Customer Name": "Over Payer", "Amount": 10000, "Unused Amount": 0, "External ID": "OP_UNPAID"})
data.append({"Date": today, "Invoice Date": today, "CustomerID": "CUST_OVERPAY", "Customer Name": "Over Payer", "Amount": 15000, "Unused Amount": 15000, "External ID": "OP_ADVANCE"})

# 3. The Offset Debtor (Net Outstanding: 30k. Should appear with 30k)
# They owe 50k, but have an unapplied advance of 20k.
data.append({"Date": None, "Invoice Date": today - timedelta(days=60), "CustomerID": "CUST_OFFSET", "Customer Name": "Offset Debtor", "Amount": 50000, "Unused Amount": 0, "External ID": "OFF_UNPAID"})
data.append({"Date": today - timedelta(days=5), "Invoice Date": today - timedelta(days=5), "CustomerID": "CUST_OFFSET", "Customer Name": "Offset Debtor", "Amount": 20000, "Unused Amount": 20000, "External ID": "OFF_ADVANCE"})

# 4. The Fractional Paid Ghost (Net Outstanding: 50k. Should appear with 50k)
data.append({"Date": today - timedelta(days=120), "Invoice Date": today - timedelta(days=120), "CustomerID": "CUST_FRAC_GHOST", "Customer Name": "Fractional Ghost", "Amount": 50000, "Unused Amount": 0, "External ID": "FG_PAID"})
data.append({"Date": None, "Invoice Date": today - timedelta(days=120), "CustomerID": "CUST_FRAC_GHOST", "Customer Name": "Fractional Ghost", "Amount": 50000, "Unused Amount": 0, "External ID": "FG_UNPAID"})

# 5. Advance Credit Only (Net Outstanding: -50k. Should NOT appear on pending collections)
data.append({"Date": today, "Invoice Date": today, "CustomerID": "CUST_ADVANCE", "Customer Name": "Advance Credit Only", "Amount": 50000, "Unused Amount": 50000, "External ID": "ADV_1"})

df = pd.DataFrame(data)
df['Date'] = pd.to_datetime(df['Date'])
df.to_excel("CIBIL_Net_Outstanding_Test.xlsx", index=False)
print("Generated CIBIL_Net_Outstanding_Test.xlsx!")

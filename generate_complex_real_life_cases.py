import pandas as pd
from datetime import datetime, timedelta

today = datetime.now()

data = []

# 1. The Seasonal Buyer (Massive volume in 2 months, 0 volume rest of year, slightly late due to cash flow)
for i in range(10):
    data.append({"Date": today - timedelta(days=180 + i), "Invoice Date": today - timedelta(days=190 + i), "CustomerID": "CUST_SEASONAL", "Customer Name": "Seasonal Buyer", "Amount": 200000, "Unused Amount": 0, "External ID": f"S{i}"}) # 10 days late consistently in season

# 2. The Chronic Disputer (Pays 95% of invoices perfectly, but holds 5% of invoices ransom for 180 days due to 'quality disputes')
for i in range(19):
    data.append({"Date": today - timedelta(days=20+i), "Invoice Date": today - timedelta(days=20+i), "CustomerID": "CUST_DISPUTE", "Customer Name": "Chronic Disputer", "Amount": 50000, "Unused Amount": 0, "External ID": f"D_GOOD_{i}"})
# The disputed invoice
data.append({"Date": today, "Invoice Date": today - timedelta(days=180), "CustomerID": "CUST_DISPUTE", "Customer Name": "Chronic Disputer", "Amount": 50000, "Unused Amount": 0, "External ID": "D_BAD_1"})

# 3. The 50/50 Pre-Payer (Pays 50% advance, 50% on delivery 15 days later)
for i in range(5):
    inv_date = today - timedelta(days=i*30)
    data.append({"Date": inv_date - timedelta(days=10), "Invoice Date": inv_date, "CustomerID": "CUST_PREPAY", "Customer Name": "50-50 Pre-Payer", "Amount": 25000, "Unused Amount": 0, "External ID": f"PRE_{i}_A"}) # 10 days early
    data.append({"Date": inv_date + timedelta(days=15), "Invoice Date": inv_date, "CustomerID": "CUST_PREPAY", "Customer Name": "50-50 Pre-Payer", "Amount": 25000, "Unused Amount": 0, "External ID": f"PRE_{i}_B"}) # 15 days late

# 4. The Snowballing Defaulter (Starting to go bankrupt: 0 days late -> 5 days -> 15 days -> 45 days -> 90 days)
delays = [0, 5, 15, 45, 90]
for i, delay in enumerate(delays):
    inv_date = today - timedelta(days=150 - (i*30))
    data.append({"Date": inv_date + timedelta(days=delay), "Invoice Date": inv_date, "CustomerID": "CUST_SNOWBALL", "Customer Name": "Snowballing Defaulter", "Amount": 10000, "Unused Amount": 0, "External ID": f"SNOW_{i}"})

# 5. The Multiple Invoice Aggregator (Pays 10 tiny invoices with 1 single payment record, varying delays)
# Our AR system exports this as 10 separate rows with the same Payment Date, but different invoice dates.
for i in range(10):
    inv_date = today - timedelta(days=30 + i*5)
    data.append({"Date": today, "Invoice Date": inv_date, "CustomerID": "CUST_AGGREGATOR", "Customer Name": "Invoice Aggregator", "Amount": 2000, "Unused Amount": 0, "External ID": f"AGG_{i}"})

df = pd.DataFrame(data)
df.to_excel("CIBIL_Complex_Real_Life_Cases.xlsx", index=False)
print("Generated CIBIL_Complex_Real_Life_Cases.xlsx!")

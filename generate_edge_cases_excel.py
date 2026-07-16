import pandas as pd
from datetime import datetime, timedelta

today = datetime.now()

data = [
    # 1. The Perfect Whale (Should have 1000 V1 and High V2)
    {"Date": today, "Invoice Date": today, "CustomerID": "CUST_WHALE", "Customer Name": "Perfect Whale", "Amount": 1000000, "Unused Amount": 0, "External ID": "W1"},
    {"Date": today, "Invoice Date": today, "CustomerID": "CUST_WHALE", "Customer Name": "Perfect Whale", "Amount": 1000000, "Unused Amount": 0, "External ID": "W2"},
    {"Date": today, "Invoice Date": today, "CustomerID": "CUST_WHALE", "Customer Name": "Perfect Whale", "Amount": 1000000, "Unused Amount": 0, "External ID": "W3"},

    # 2. Reformed Defaulter (Should have 1000 V1 because last 5 payments are on time)
    {"Date": today - timedelta(days=300), "Invoice Date": today - timedelta(days=400), "CustomerID": "CUST_REFORM", "Customer Name": "Reformed Defaulter", "Amount": 50000, "Unused Amount": 0, "External ID": "R1"}, # 100 days late
    {"Date": today - timedelta(days=300), "Invoice Date": today - timedelta(days=400), "CustomerID": "CUST_REFORM", "Customer Name": "Reformed Defaulter", "Amount": 50000, "Unused Amount": 0, "External ID": "R2"}, # 100 days late
    {"Date": today - timedelta(days=4), "Invoice Date": today - timedelta(days=4), "CustomerID": "CUST_REFORM", "Customer Name": "Reformed Defaulter", "Amount": 1000, "Unused Amount": 0, "External ID": "R3"},
    {"Date": today - timedelta(days=3), "Invoice Date": today - timedelta(days=3), "CustomerID": "CUST_REFORM", "Customer Name": "Reformed Defaulter", "Amount": 1000, "Unused Amount": 0, "External ID": "R4"},
    {"Date": today - timedelta(days=2), "Invoice Date": today - timedelta(days=2), "CustomerID": "CUST_REFORM", "Customer Name": "Reformed Defaulter", "Amount": 1000, "Unused Amount": 0, "External ID": "R5"},
    {"Date": today - timedelta(days=1), "Invoice Date": today - timedelta(days=1), "CustomerID": "CUST_REFORM", "Customer Name": "Reformed Defaulter", "Amount": 1000, "Unused Amount": 0, "External ID": "R6"},
    {"Date": today, "Invoice Date": today, "CustomerID": "CUST_REFORM", "Customer Name": "Reformed Defaulter", "Amount": 1000, "Unused Amount": 0, "External ID": "R7"},

    # 3. Forgotten Invoice (V2 should ignore the tiny 40rs delay, V1 should also ignore it if there are 5 recent payments)
    {"Date": today - timedelta(days=1), "Invoice Date": today - timedelta(days=500), "CustomerID": "CUST_FORGET", "Customer Name": "Forgotten Invoice VIP", "Amount": 40, "Unused Amount": 0, "External ID": "F1"}, # 499 days late, tiny amount
    {"Date": today, "Invoice Date": today, "CustomerID": "CUST_FORGET", "Customer Name": "Forgotten Invoice VIP", "Amount": 500000, "Unused Amount": 0, "External ID": "F2"},
    {"Date": today, "Invoice Date": today, "CustomerID": "CUST_FORGET", "Customer Name": "Forgotten Invoice VIP", "Amount": 500000, "Unused Amount": 0, "External ID": "F3"},

    # 4. Math Breakers (0 Amount, Null amounts, Negative Amounts - Should not crash the server)
    {"Date": today, "Invoice Date": today - timedelta(days=50), "CustomerID": "CUST_MATH", "Customer Name": "Math Breaker", "Amount": 0, "Unused Amount": 0, "External ID": "M1"},
    {"Date": today, "Invoice Date": today - timedelta(days=50), "CustomerID": "CUST_MATH", "Customer Name": "Math Breaker", "Amount": -500, "Unused Amount": 0, "External ID": "M2"},

    # 5. The Partial Payer (Fractional weights)
    # Total invoice 10k. 5k paid on time. 5k paid 30 days late. Average delay should be exactly 15 days.
    {"Date": today - timedelta(days=30), "Invoice Date": today - timedelta(days=30), "CustomerID": "CUST_PARTIAL", "Customer Name": "Fractional Payer", "Amount": 5000, "Unused Amount": 0, "External ID": "P1"},
    {"Date": today, "Invoice Date": today - timedelta(days=30), "CustomerID": "CUST_PARTIAL", "Customer Name": "Fractional Payer", "Amount": 5000, "Unused Amount": 0, "External ID": "P2"},
]

df = pd.DataFrame(data)
df.to_excel("CIBIL_Actual_Edge_Cases.xlsx", index=False)
print("Generated CIBIL_Actual_Edge_Cases.xlsx!")

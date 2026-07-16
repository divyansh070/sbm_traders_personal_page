import pandas as pd
from datetime import datetime, timedelta

today = datetime.now().date()
def d(days_offset):
    return today + timedelta(days=days_offset)

data = [
    # Customer 1: Paid 10k in one go, 30 days late
    {"Customer Name": "One-Time Payer (30d late)", "CustomerID": "C001", "Invoice Date": d(-60), "Date": d(-30), "Amount": 10000, "Unused Amount": 0},
    
    # Customer 2: Paid 10k in installments (5k on time, 5k 30 days late)
    # Because Unused Amount = 0 for applied payments in Zoho, we put 0.
    {"Customer Name": "Installment Payer (Half Late)", "CustomerID": "C002", "Invoice Date": d(-60), "Date": d(-60), "Amount": 5000, "Unused Amount": 0},
    {"Customer Name": "Installment Payer (Half Late)", "CustomerID": "C002", "Invoice Date": d(-60), "Date": d(-30), "Amount": 5000, "Unused Amount": 0},
    
    # Customer 3: Paid an ADVANCE of 10k. 
    # Current broken logic thinks Unused Amount > 1 means they are a DEFAULTER!
    {"Customer Name": "Advance Payer (Punished by Bug)", "CustomerID": "C003", "Invoice Date": d(-60), "Date": d(-60), "Amount": 10000, "Unused Amount": 10000},
]

df = pd.DataFrame(data)
df.to_excel("cibil_test_installments.xlsx", index=False)
print("Test file created!")

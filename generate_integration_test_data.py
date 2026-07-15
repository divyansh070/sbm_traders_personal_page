import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Current date reference
today = datetime.now()

# ---------------------------------------------------------
# Extended Test Cases Setup (19 Distinct Scenarios)
# ---------------------------------------------------------
invoices = []
payments = []

def get_inv_id(num): return f"INV-2026-{1000+num}"
def get_pay_id(num): return f"PAY-2026-{2000+num}"

# 1. Fully Paid on time (Standard Case)
inv_date_1 = today - timedelta(days=50)
pay_date_1 = today - timedelta(days=48)
invoices.append({
    'Invoice Date': inv_date_1, 'Due Date': inv_date_1 + timedelta(days=30), 'Invoice ID': get_inv_id(1), 'Customer ID': 'CUST-001', 'Customer Name': 'Alpha Co',
    'Total': 5000.0, 'Balance': 0.0, 'Last Payment Date': pay_date_1, 'Invoice Status': 'Closed'
})
payments.append({
    'Payment Date': pay_date_1, 'Customer ID': 'CUST-001', 'Customer Name': 'Alpha Co',
    'Payment Amount': 5000.0, 'Amount Applied to Invoice': 5000.0, 'Unused Amount': 0.0,
    'Invoice Date': inv_date_1, 'Payment Number': get_pay_id(1)
})

# 2. Fully Paid late (Penalty Case)
inv_date_2 = today - timedelta(days=90)
pay_date_2 = today - timedelta(days=20) # 70 days delay!
invoices.append({
    'Invoice Date': inv_date_2, 'Due Date': inv_date_2 + timedelta(days=30), 'Invoice ID': get_inv_id(2), 'Customer ID': 'CUST-002', 'Customer Name': 'Beta Ltd',
    'Total': 10000.0, 'Balance': 0.0, 'Last Payment Date': pay_date_2, 'Invoice Status': 'Closed'
})
payments.append({
    'Payment Date': pay_date_2, 'Customer ID': 'CUST-002', 'Customer Name': 'Beta Ltd',
    'Payment Amount': 10000.0, 'Amount Applied to Invoice': 10000.0, 'Unused Amount': 0.0,
    'Invoice Date': inv_date_2, 'Payment Number': get_pay_id(2)
})

# 3. Partially Paid - Remaining balance
inv_date_3 = today - timedelta(days=30)
pay_date_3 = today - timedelta(days=25)
invoices.append({
    'Invoice Date': inv_date_3, 'Due Date': inv_date_3 + timedelta(days=30), 'Invoice ID': get_inv_id(3), 'Customer ID': 'CUST-003', 'Customer Name': 'Gamma Inc',
    'Total': 8000.0, 'Balance': 3000.0, 'Last Payment Date': pay_date_3, 'Invoice Status': 'Partially Paid'
})
payments.append({
    'Payment Date': pay_date_3, 'Customer ID': 'CUST-003', 'Customer Name': 'Gamma Inc',
    'Payment Amount': 5000.0, 'Amount Applied to Invoice': 5000.0, 'Unused Amount': 0.0,
    'Invoice Date': inv_date_3, 'Payment Number': get_pay_id(3)
})

# 4. Completely Unpaid (Ongoing penalty)
inv_date_4 = today - timedelta(days=45)
invoices.append({
    'Invoice Date': inv_date_4, 'Due Date': inv_date_4 + timedelta(days=30), 'Invoice ID': get_inv_id(4), 'Customer ID': 'CUST-004', 'Customer Name': 'Delta LLC',
    'Total': 15000.0, 'Balance': 15000.0, 'Last Payment Date': pd.NaT, 'Invoice Status': 'Overdue'
})

# 5. Advance Payment (Creates unused credit)
inv_date_5 = today - timedelta(days=10)
pay_date_5 = today - timedelta(days=8)
invoices.append({
    'Invoice Date': inv_date_5, 'Due Date': inv_date_5 + timedelta(days=30), 'Invoice ID': get_inv_id(5), 'Customer ID': 'CUST-005', 'Customer Name': 'Epsilon Corp',
    'Total': 2000.0, 'Balance': 0.0, 'Last Payment Date': pay_date_5, 'Invoice Status': 'Closed'
})
payments.append({
    'Payment Date': pay_date_5, 'Customer ID': 'CUST-005', 'Customer Name': 'Epsilon Corp',
    'Payment Amount': 5000.0, 'Amount Applied to Invoice': 2000.0, 'Unused Amount': 3000.0,
    'Invoice Date': inv_date_5, 'Payment Number': get_pay_id(5)
})

# 6. Tiny Unpaid Anomaly (< 100 Rs)
inv_date_6 = today - timedelta(days=100)
invoices.append({
    'Invoice Date': inv_date_6, 'Due Date': inv_date_6 + timedelta(days=30), 'Invoice ID': get_inv_id(6), 'Customer ID': 'CUST-006', 'Customer Name': 'Zeta Traders',
    'Total': 50.0, 'Balance': 50.0, 'Last Payment Date': pd.NaT, 'Invoice Status': 'Overdue'
})

# 7. Multiple invoices cleared by one massive payment
inv_date_7a = today - timedelta(days=20)
inv_date_7b = today - timedelta(days=18)
pay_date_7 = today - timedelta(days=5)

invoices.append({
    'Invoice Date': inv_date_7a, 'Due Date': inv_date_7a + timedelta(days=30), 'Invoice ID': get_inv_id(7), 'Customer ID': 'CUST-007', 'Customer Name': 'Omega Logistics',
    'Total': 4000.0, 'Balance': 0.0, 'Last Payment Date': pay_date_7, 'Invoice Status': 'Closed'
})
invoices.append({
    'Invoice Date': inv_date_7b, 'Due Date': inv_date_7b + timedelta(days=30), 'Invoice ID': get_inv_id(8), 'Customer ID': 'CUST-007', 'Customer Name': 'Omega Logistics',
    'Total': 6000.0, 'Balance': 0.0, 'Last Payment Date': pay_date_7, 'Invoice Status': 'Closed'
})
payments.append({
    'Payment Date': pay_date_7, 'Customer ID': 'CUST-007', 'Customer Name': 'Omega Logistics',
    'Payment Amount': 10000.0, 'Amount Applied to Invoice': 4000.0, 'Unused Amount': 0.0,
    'Invoice Date': inv_date_7a, 'Payment Number': get_pay_id(7)
})
payments.append({
    'Payment Date': pay_date_7, 'Customer ID': 'CUST-007', 'Customer Name': 'Omega Logistics',
    'Payment Amount': 10000.0, 'Amount Applied to Invoice': 6000.0, 'Unused Amount': 0.0,
    'Invoice Date': inv_date_7b, 'Payment Number': get_pay_id(8)
})

# 8. Single Invoice cleared by Multiple Payments over time
inv_date_8 = today - timedelta(days=120)
invoices.append({
    'Invoice Date': inv_date_8, 'Due Date': inv_date_8 + timedelta(days=30), 'Invoice ID': get_inv_id(9), 'Customer ID': 'CUST-008', 'Customer Name': 'Theta Services',
    'Total': 30000.0, 'Balance': 0.0, 'Last Payment Date': today - timedelta(days=10), 'Invoice Status': 'Closed'
})
payments.append({
    'Payment Date': today - timedelta(days=100), 'Customer ID': 'CUST-008', 'Customer Name': 'Theta Services',
    'Payment Amount': 10000.0, 'Amount Applied to Invoice': 10000.0, 'Unused Amount': 0.0,
    'Invoice Date': inv_date_8, 'Payment Number': get_pay_id(9)
})
payments.append({
    'Payment Date': today - timedelta(days=60), 'Customer ID': 'CUST-008', 'Customer Name': 'Theta Services',
    'Payment Amount': 10000.0, 'Amount Applied to Invoice': 10000.0, 'Unused Amount': 0.0,
    'Invoice Date': inv_date_8, 'Payment Number': get_pay_id(10)
})
payments.append({
    'Payment Date': today - timedelta(days=10), 'Customer ID': 'CUST-008', 'Customer Name': 'Theta Services',
    'Payment Amount': 10000.0, 'Amount Applied to Invoice': 10000.0, 'Unused Amount': 0.0,
    'Invoice Date': inv_date_8, 'Payment Number': get_pay_id(11)
})

# 9. Extremely old unpaid invoice
inv_date_9 = today - timedelta(days=800)
invoices.append({
    'Invoice Date': inv_date_9, 'Due Date': inv_date_9 + timedelta(days=30), 'Invoice ID': get_inv_id(10), 'Customer ID': 'CUST-009', 'Customer Name': 'Sigma Legacy',
    'Total': 45000.0, 'Balance': 45000.0, 'Last Payment Date': pd.NaT, 'Invoice Status': 'Overdue'
})

# 10. Same-day clearance
inv_date_10 = today - timedelta(days=2)
invoices.append({
    'Invoice Date': inv_date_10, 'Due Date': inv_date_10 + timedelta(days=30), 'Invoice ID': get_inv_id(11), 'Customer ID': 'CUST-010', 'Customer Name': 'FastTrack Ltd',
    'Total': 8500.0, 'Balance': 0.0, 'Last Payment Date': inv_date_10, 'Invoice Status': 'Closed'
})
payments.append({
    'Payment Date': inv_date_10, 'Customer ID': 'CUST-010', 'Customer Name': 'FastTrack Ltd',
    'Payment Amount': 8500.0, 'Amount Applied to Invoice': 8500.0, 'Unused Amount': 0.0,
    'Invoice Date': inv_date_10, 'Payment Number': get_pay_id(12)
})

# 11. Credit Note / Refund (Negative Amounts)
inv_date_11 = today - timedelta(days=15)
invoices.append({
    'Invoice Date': inv_date_11, 'Due Date': inv_date_11 + timedelta(days=30), 'Invoice ID': get_inv_id(12), 'Customer ID': 'CUST-011', 'Customer Name': 'Refunded Inc',
    'Total': -5000.0, 'Balance': 0.0, 'Last Payment Date': pd.NaT, 'Invoice Status': 'Closed'
})
payments.append({
    'Payment Date': today - timedelta(days=14), 'Customer ID': 'CUST-011', 'Customer Name': 'Refunded Inc',
    'Payment Amount': -5000.0, 'Amount Applied to Invoice': -5000.0, 'Unused Amount': 0.0,
    'Invoice Date': inv_date_11, 'Payment Number': get_pay_id(13)
})

# 12. Overpayment on a Single Invoice
inv_date_12 = today - timedelta(days=20)
pay_date_12 = today - timedelta(days=15)
invoices.append({
    'Invoice Date': inv_date_12, 'Due Date': inv_date_12 + timedelta(days=30), 'Invoice ID': get_inv_id(13), 'Customer ID': 'CUST-012', 'Customer Name': 'Overpay LLC',
    'Total': 4000.0, 'Balance': 0.0, 'Last Payment Date': pay_date_12, 'Invoice Status': 'Closed'
})
payments.append({
    'Payment Date': pay_date_12, 'Customer ID': 'CUST-012', 'Customer Name': 'Overpay LLC',
    'Payment Amount': 6000.0, 'Amount Applied to Invoice': 4000.0, 'Unused Amount': 2000.0,
    'Invoice Date': inv_date_12, 'Payment Number': get_pay_id(14)
})

# 13. Mixed History Customer (One paid on time, one very late, one completely unpaid)
inv_date_13a = today - timedelta(days=100)
inv_date_13b = today - timedelta(days=60)
inv_date_13c = today - timedelta(days=20)
pay_date_13a = today - timedelta(days=98)
pay_date_13b = today - timedelta(days=5)

invoices.append({
    'Invoice Date': inv_date_13a, 'Due Date': inv_date_13a + timedelta(days=30), 'Invoice ID': get_inv_id(14), 'Customer ID': 'CUST-013', 'Customer Name': 'Mixed History Corp',
    'Total': 1000.0, 'Balance': 0.0, 'Last Payment Date': pay_date_13a, 'Invoice Status': 'Closed'
})
payments.append({
    'Payment Date': pay_date_13a, 'Customer ID': 'CUST-013', 'Customer Name': 'Mixed History Corp',
    'Payment Amount': 1000.0, 'Amount Applied to Invoice': 1000.0, 'Unused Amount': 0.0,
    'Invoice Date': inv_date_13a, 'Payment Number': get_pay_id(15)
})
invoices.append({
    'Invoice Date': inv_date_13b, 'Due Date': inv_date_13b + timedelta(days=30), 'Invoice ID': get_inv_id(15), 'Customer ID': 'CUST-013', 'Customer Name': 'Mixed History Corp',
    'Total': 2000.0, 'Balance': 0.0, 'Last Payment Date': pay_date_13b, 'Invoice Status': 'Closed'
})
payments.append({
    'Payment Date': pay_date_13b, 'Customer ID': 'CUST-013', 'Customer Name': 'Mixed History Corp',
    'Payment Amount': 2000.0, 'Amount Applied to Invoice': 2000.0, 'Unused Amount': 0.0,
    'Invoice Date': inv_date_13b, 'Payment Number': get_pay_id(16)
})
invoices.append({
    'Invoice Date': inv_date_13c, 'Due Date': inv_date_13c + timedelta(days=30), 'Invoice ID': get_inv_id(16), 'Customer ID': 'CUST-013', 'Customer Name': 'Mixed History Corp',
    'Total': 3000.0, 'Balance': 3000.0, 'Last Payment Date': pd.NaT, 'Invoice Status': 'Overdue'
})

# 14. Data Missing Fields (Missing Due Date, Missing Customer Name)
inv_date_14 = today - timedelta(days=40)
invoices.append({
    'Invoice Date': inv_date_14, 'Due Date': pd.NaT, 'Invoice ID': get_inv_id(17), 'Customer ID': 'CUST-014', 'Customer Name': '',
    'Total': 7500.0, 'Balance': 7500.0, 'Last Payment Date': pd.NaT, 'Invoice Status': 'Overdue'
})

# 15. Zero-Dollar Dummy Invoice (Free Sample - Should be ignored by filter)
invoices.append({
    'Invoice Date': today - timedelta(days=5), 'Due Date': today + timedelta(days=25), 'Invoice ID': get_inv_id(18), 'Customer ID': 'CUST-015', 'Customer Name': 'Freebie Org',
    'Total': 0.0, 'Balance': 0.0, 'Last Payment Date': pd.NaT, 'Invoice Status': 'Closed'
})

# 16. Zero-Dollar Payment
payments.append({
    'Payment Date': today - timedelta(days=2), 'Customer ID': 'CUST-016', 'Customer Name': 'Zero Payment LLC',
    'Payment Amount': 0.0, 'Amount Applied to Invoice': 0.0, 'Unused Amount': 0.0,
    'Invoice Date': today - timedelta(days=10), 'Payment Number': get_pay_id(17)
})

# 17. Extreme Future Payment (Negative delay)
inv_date_17 = today + timedelta(days=30)
pay_date_17 = today - timedelta(days=1)
invoices.append({
    'Invoice Date': inv_date_17, 'Due Date': inv_date_17 + timedelta(days=30), 'Invoice ID': get_inv_id(19), 'Customer ID': 'CUST-017', 'Customer Name': 'Future Pay Inc',
    'Total': 5000.0, 'Balance': 0.0, 'Last Payment Date': pay_date_17, 'Invoice Status': 'Closed'
})
payments.append({
    'Payment Date': pay_date_17, 'Customer ID': 'CUST-017', 'Customer Name': 'Future Pay Inc',
    'Payment Amount': 5000.0, 'Amount Applied to Invoice': 5000.0, 'Unused Amount': 0.0,
    'Invoice Date': inv_date_17, 'Payment Number': get_pay_id(18)
})

# 18. Tiny partial payment made, leaving large balance unpaid
inv_date_18 = today - timedelta(days=50)
pay_date_18 = today - timedelta(days=40)
invoices.append({
    'Invoice Date': inv_date_18, 'Due Date': inv_date_18 + timedelta(days=30), 'Invoice ID': get_inv_id(20), 'Customer ID': 'CUST-018', 'Customer Name': 'Tiny Payers',
    'Total': 100000.0, 'Balance': 99000.0, 'Last Payment Date': pay_date_18, 'Invoice Status': 'Partially Paid'
})
payments.append({
    'Payment Date': pay_date_18, 'Customer ID': 'CUST-018', 'Customer Name': 'Tiny Payers',
    'Payment Amount': 1000.0, 'Amount Applied to Invoice': 1000.0, 'Unused Amount': 0.0,
    'Invoice Date': inv_date_18, 'Payment Number': get_pay_id(19)
})

# 19. Extremely Large Numbers (Overflow testing)
inv_date_19 = today - timedelta(days=60)
pay_date_19 = today - timedelta(days=10)
invoices.append({
    'Invoice Date': inv_date_19, 'Due Date': inv_date_19 + timedelta(days=30), 'Invoice ID': get_inv_id(21), 'Customer ID': 'CUST-019', 'Customer Name': 'Whale Capital',
    'Total': 50000000.0, 'Balance': 0.0, 'Last Payment Date': pay_date_19, 'Invoice Status': 'Closed'
})
payments.append({
    'Payment Date': pay_date_19, 'Customer ID': 'CUST-019', 'Customer Name': 'Whale Capital',
    'Payment Amount': 50000000.0, 'Amount Applied to Invoice': 50000000.0, 'Unused Amount': 0.0,
    'Invoice Date': inv_date_19, 'Payment Number': get_pay_id(20)
})

# Create DataFrames
df_invoices = pd.DataFrame(invoices)
df_payments = pd.DataFrame(payments)

# Save to Excel
df_invoices.to_excel('Test_Integration_Invoice.xlsx', index=False)
df_payments.to_excel('Test_Integration_Customer_Payment.xlsx', index=False)

print(f"Generated {len(df_invoices)} Invoices and {len(df_payments)} Payment rows across 19 complex scenarios.")
print("Test files generated successfully:")
print("- Test_Integration_Invoice.xlsx")
print("- Test_Integration_Customer_Payment.xlsx")

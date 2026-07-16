import pandas as pd
df = pd.read_excel('Customer_Payment.xlsx')
applied_col = None
for col in df.columns:
    if 'applied' in col.lower() and 'amount' in col.lower():
        applied_col = col
        break

if applied_col:
    df['Effective_Amount'] = df[applied_col].fillna(df['Amount'])
else:
    df['Effective_Amount'] = df['Amount']

print(df[df.duplicated(subset=['Payment Number'], keep=False)][['Payment Number', 'Amount', applied_col, 'Effective_Amount']].head(10))

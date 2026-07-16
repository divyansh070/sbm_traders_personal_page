import pandas as pd
from datetime import date, timedelta
from cibil_simulator import MockCustomer, MockPayment
import os

def create_edge_cases():
    cases = []
    
    # 1. The Perfect Whale (High volume, perfect payments)
    cases.append(MockCustomer("1. Perfect Whale", [
        MockPayment(1000000, 0),
        MockPayment(500000, 0),
        MockPayment(2000000, 0)
    ], last_order_days_ago=5))
    
    # 2. The Micro Newbie (1 tiny order, perfect payment)
    cases.append(MockCustomer("2. Micro Newbie", [
        MockPayment(1000, 0)
    ], last_order_days_ago=2))
    
    # 3. The Reformed Defaulter (3 huge late payments in past, 5 perfect recent ones)
    cases.append(MockCustomer("3. Reformed Defaulter", [
        MockPayment(100000, 100), # Old, late
        MockPayment(50000, 80),   # Old, late
        MockPayment(100000, 120), # Old, late
        MockPayment(20000, 0),    # Recent, perfect
        MockPayment(20000, 0),    # Recent, perfect
        MockPayment(20000, 0),    # Recent, perfect
        MockPayment(20000, 0),    # Recent, perfect
        MockPayment(20000, 0)     # Recent, perfect
    ], last_order_days_ago=5))
    
    # 4. The Fallen Angel (10 perfect payments, 2 terrible recent ones)
    cases.append(MockCustomer("4. Fallen Angel", [
        MockPayment(50000, 0) for _ in range(10)
    ] + [
        MockPayment(50000, 60), # Recent, terribly late
        MockPayment(50000, 60)  # Recent, terribly late
    ], last_order_days_ago=10))
    
    # 5. The Consistently 1-Day Late (Always just barely misses the deadline)
    cases.append(MockCustomer("5. The 'Oops' Payer (1d Late)", [
        MockPayment(10000, 1) for _ in range(8)
    ], last_order_days_ago=5))
    
    # 6. The 20-Day Late Whale (Huge volume, but always 20 days late)
    cases.append(MockCustomer("6. The Late Whale", [
        MockPayment(500000, 20),
        MockPayment(1000000, 20),
        MockPayment(500000, 20)
    ], last_order_days_ago=5))
    
    # 7. The Ghost / One-Hit Wonder (1 huge order 2 years ago, never returned)
    cases.append(MockCustomer("7. One-Hit Wonder Ghost", [
        MockPayment(1000000, 0)
    ], last_order_days_ago=700))
    
    # 8. The Installment Grinder (Pays in tiny chunks, some late, some on time)
    # Total invoice 100k, paid in 10k chunks
    payments = []
    for i in range(10):
        delay = i * 2 # progressively later: 0, 2, 4, 6... up to 18 days late
        payments.append(MockPayment(10000, delay))
    cases.append(MockCustomer("8. Installment Grinder", payments, last_order_days_ago=15))
    
    # 9. Extreme Outlier Anomaly (Perfect payer, but 1 tiny ₹10 payment was forgotten for 500 days)
    cases.append(MockCustomer("9. The Tiny Forgotten Invoice", [
        MockPayment(100000, 0),
        MockPayment(100000, 0),
        MockPayment(100000, 0),
        MockPayment(10, 500) # The forgotten ₹10
    ], last_order_days_ago=2))
    
    # 10. The Advance Payer (Always pays in advance, delay is 0 or negative)
    cases.append(MockCustomer("10. Advance Payer", [
        MockPayment(50000, 0),
        MockPayment(50000, 0)
    ], last_order_days_ago=2))
    
    return cases

def run_tests():
    cases = create_edge_cases()
    rows = []
    
    for c in cases:
        v1_score, v1_avg_delay = c.calculate_cibil_v1()
        v2_score, v2_median_delay, vol_boost, decay, total_sales = c.calculate_cibil_v2()
        
        # Determine combination meaning
        v1_tier = "High" if v1_score >= 800 else ("Medium" if v1_score >= 500 else "Low")
        v2_tier = "High" if v2_score >= 700 else ("Medium" if v2_score >= 500 else "Low")
        
        # Summarize payments
        payments_str = f"{len(c.payments)} payments. Total: ₹{total_sales}"
        
        rows.append({
            "Profile Name": c.name,
            "Total Sales (₹)": total_sales,
            "Last Order (Days)": c.last_order_days_ago,
            "V1 (Dynamic)": v1_score,
            "V2 (Standard)": v2_score,
            "V1_Tier": v1_tier,
            "V2_Tier": v2_tier,
            "V1 Avg Delay": v1_avg_delay,
            "V2 Median Delay": v2_median_delay,
            "V2 Volume Boost": vol_boost,
            "V2 Decay": decay
        })
        
    df = pd.DataFrame(rows)
    
    output_path = "cibil_comprehensive_report.xlsx"
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name="Edge Cases", index=False)
        
        worksheet = writer.sheets["Edge Cases"]
        for col in worksheet.columns:
            max_length = 0
            column = col[0].column_letter 
            for cell in col:
                try: 
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            worksheet.column_dimensions[column].width = min(max_length + 2, 40)
            
    print(f"Excel report generated at: {os.path.abspath(output_path)}")
    return df

if __name__ == "__main__":
    run_tests()

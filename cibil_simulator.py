import pandas as pd
import math
import os
from datetime import date, timedelta

class MockPayment:
    def __init__(self, amount, late_only_delay, invoice_date=None, payment_date=None):
        self.amount = amount
        self.late_only_delay = max(0, late_only_delay)
        self.invoice_date = invoice_date or date.today()
        self.payment_date = payment_date or date.today()
        
    def __repr__(self):
        return f"Payment(₹{self.amount}, delay={self.late_only_delay}d)"

class MockCustomer:
    def __init__(self, name, payments, last_order_days_ago=0, **kwargs):
        self.name = name
        self.payments = payments
        self.last_order_days_ago = last_order_days_ago
        
        # --- CIBIL V1 Params ---
        self.delay_weight_v1 = kwargs.get('delay_weight_v1', 5.0)
        self.inactivity_weight_v1 = kwargs.get('inactivity_weight_v1', 2.0)
        
        # --- CIBIL V2 Params ---
        self.gold_limit = kwargs.get('gold_limit', 4)
        self.average_limit = kwargs.get('average_limit', 15)
        self.v2_delay_penalty_mult = kwargs.get('v2_delay_penalty_mult', 10.0)
        self.v2_volume_boost_mult = kwargs.get('v2_volume_boost_mult', 25.0)
        self.v2_decay_start_days = kwargs.get('v2_decay_start_days', 90)
        self.v2_decay_penalty_mult = kwargs.get('v2_decay_penalty_mult', 0.5)
        self.v2_volume_percentile = kwargs.get('v2_volume_percentile', 0.5)
        
    def calculate_cibil_v1(self):
        base_score = 1000
        late_payments = [p for p in self.payments if p.late_only_delay > 0]
        # In actual django we sorted by date reverse, here we assume they are chronological
        last_5_late = late_payments[-5:] 
        
        if last_5_late:
            total_late_amount = sum(float(p.amount) for p in last_5_late if p.amount)
            if total_late_amount > 0:
                avg_delay = sum(p.late_only_delay * float(p.amount or 0) for p in last_5_late) / total_late_amount
            else:
                avg_delay = sum(p.late_only_delay for p in last_5_late) / len(last_5_late)
        else:
            avg_delay = 0
            
        days_inactive = self.last_order_days_ago
        
        penalty = (avg_delay * self.delay_weight_v1) + (days_inactive * self.inactivity_weight_v1)
            
        final_score = base_score - penalty
        return max(100, min(1000, int(final_score))), round(avg_delay, 2)
        
    def calculate_cibil_v2(self):
        score = 300
        max_score = 1000
        
        late_payments = [p for p in self.payments if p.late_only_delay > 0 and p.amount]
        
        median_delay = 0
        if late_payments:
            # Sort by delay ascending to find the percentile
            late_payments.sort(key=lambda x: x.late_only_delay)
            total_late_amount = sum(float(p.amount) for p in late_payments)
            
            cumulative_amount = 0
            for p in late_payments:
                cumulative_amount += float(p.amount)
                if cumulative_amount >= (total_late_amount * self.v2_volume_percentile):
                    median_delay = p.late_only_delay
                    break
                    
        # 1. Base Score + Class assignment
        if median_delay <= self.gold_limit:
            score += 300
        elif median_delay <= self.average_limit:
            score += 200
        else:
            excess = median_delay - self.average_limit
            score += 100 - (excess * self.v2_delay_penalty_mult)
            
        # 2. Volume Boost
        unique_invoices = set()
        total_sales = 0
        for p in self.payments:
            if p.amount and (p.invoice_date, p.amount) not in unique_invoices:
                unique_invoices.add((p.invoice_date, p.amount))
                total_sales += float(p.amount)
                
        volume_boost = 0
        if total_sales > 0:
            volume_boost = math.log10(float(total_sales)) * self.v2_volume_boost_mult
            score += volume_boost
            
        # 3. Inactivity Penalty
        days_since_last = self.last_order_days_ago
        decay_penalty = 0
        if days_since_last > self.v2_decay_start_days:
            decay_penalty = (days_since_last - self.v2_decay_start_days) * self.v2_decay_penalty_mult
            score -= decay_penalty
            
        return max(300, min(max_score, int(score))), median_delay, round(volume_boost, 2), round(decay_penalty, 2), total_sales


def generate_scenarios():
    scenarios = [
        # Scenario 1: Perfect Payer
        MockCustomer("Perfect Payer", [
            MockPayment(10000, 0),
            MockPayment(15000, 0),
            MockPayment(20000, 0)
        ]),
        
        # Scenario 2: Installments - Some early, some late
        MockCustomer("Installment User (50th Percentile Delay)", [
            MockPayment(20000, 0), # 1st installment, on time
            MockPayment(10000, 3), # 2nd installment, 3 days late
            MockPayment(10000, 10),# 3rd installment, 10 days late (This will be the 50th percentile)
            MockPayment(5000, 25), # 4th installment, 25 days late
        ]),
        
        # Scenario 3: Bad Payer - Mostly large delays
        MockCustomer("Late Payer (Consistently Late)", [
            MockPayment(50000, 20),
            MockPayment(30000, 35),
            MockPayment(10000, 45)
        ]),
        
        # Scenario 4: High Volume but Slightly Late
        MockCustomer("High Volume, Slightly Late", [
            MockPayment(200000, 10),
            MockPayment(150000, 12),
            MockPayment(500000, 5)
        ]),
        
        # Scenario 5: Old Inactive Customer
        MockCustomer("Inactive Customer (6 Months)", [
            MockPayment(10000, 0),
            MockPayment(5000, 2)
        ], last_order_days_ago=180),
        
        # Scenario 6: High Volume, Installments crossing penalty threshold
        MockCustomer("Whale with staggered payments", [
            MockPayment(50000, 0),
            MockPayment(30000, 5),
            MockPayment(100000, 18), # The bulk of money is 18 days late -> Penalty triggered!
            MockPayment(20000, 30),
        ]),
    ]
    
    rows = []
    for c in scenarios:
        v1_score, v1_avg_delay = c.calculate_cibil_v1()
        v2_score, v2_median_delay, vol_boost, decay, total_sales = c.calculate_cibil_v2()
        
        # Build payment string
        payments_str = "\n".join([f"₹{p.amount} ({p.late_only_delay}d late)" for p in c.payments])
        
        rows.append({
            "Scenario / Customer Name": c.name,
            "Payments (Amount & Delay)": payments_str,
            "Total Volume (Sales)": total_sales,
            "Days Inactive": c.last_order_days_ago,
            "---": "---",
            "V1 Score": v1_score,
            "V1 Avg Delay (Amount Wt.)": v1_avg_delay,
            "----": "----",
            "V2 Score": v2_score,
            "V2 Calculated Baseline Delay": v2_median_delay,
            "V2 Volume Boost Added": vol_boost,
            "V2 Inactivity Penalty": decay,
        })
        
    return pd.DataFrame(rows)

def analyze_parameters():
    """
    Shows how changing a parameter affects a specific customer's score.
    We will use the 'Installment User' for this test.
    """
    base_payments = [
        MockPayment(20000, 0), 
        MockPayment(10000, 3), 
        MockPayment(10000, 10),
        MockPayment(5000, 25), 
    ]
    
    # 1. Base Score
    base = MockCustomer("Base Config", base_payments)
    
    # 2. Change Volume Percentile (e.g. from 50% to 80% - meaning 80% of late money must clear before delay is set)
    p80 = MockCustomer("Volume Percentile = 80%", base_payments, v2_volume_percentile=0.8)
    
    # 3. Change Delay Penalty Multiplier (e.g. from 10 to 5)
    soft_penalty = MockCustomer("Delay Penalty Mult = 5 (Softer)", base_payments, v2_delay_penalty_mult=5.0)
    
    # 4. Change Gold Limit (e.g. from 4 to 10)
    high_gold = MockCustomer("Gold Limit = 10", base_payments, gold_limit=10)
    
    # 5. Change Volume Boost Multiplier (e.g. from 25 to 50)
    high_boost = MockCustomer("Volume Boost Mult = 50", base_payments, v2_volume_boost_mult=50.0)
    
    variations = [base, p80, soft_penalty, high_gold, high_boost]
    
    rows = []
    for c in variations:
        v2_score, v2_median_delay, vol_boost, decay, total_sales = c.calculate_cibil_v2()
        rows.append({
            "Configuration": c.name,
            "V2 Final Score": v2_score,
            "Baseline Delay Calculated": v2_median_delay,
            "Volume Boost": vol_boost,
            "Delay Category": "Gold" if v2_median_delay <= c.gold_limit else ("Average" if v2_median_delay <= c.average_limit else "Poor"),
        })
        
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("Generating Scenarios DataFrame...")
    df_scenarios = generate_scenarios()
    
    print("Generating Parameter Analysis DataFrame...")
    df_analysis = analyze_parameters()
    
    output_path = "cibil_score_simulation.xlsx"
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_scenarios.to_excel(writer, sheet_name="Test Scenarios", index=False)
        df_analysis.to_excel(writer, sheet_name="Parameter Analysis", index=False)
        
        # Adjust column widths for better readability
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for col in worksheet.columns:
                max_length = 0
                column = col[0].column_letter # Get the column name
                for cell in col:
                    try: 
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column].width = min(adjusted_width, 50) # Cap at 50

    print(f"Excel file successfully generated at: {os.path.abspath(output_path)}")
    print("You can run this script directly `python cibil_simulator.py` after tweaking parameters inside it!")

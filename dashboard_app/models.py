from django.db import models
from django.db.models import Avg, Max, Sum
from django.utils import timezone
import math

class Customer(models.Model):
    customer_id_str = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    
    # --- CIBIL V1 (Dynamic) ---
    cibil_score_v1 = models.IntegerField(default=1000)
    delay_weight_v1 = models.FloatField(default=20.0)
    inactivity_weight_v1 = models.FloatField(default=2.0)
    
    # --- CIBIL V2 (Standard) ---
    cibil_score_v2 = models.IntegerField(default=300)
    gold_limit = models.IntegerField(default=4) # Bonus if delay <= 4
    average_limit = models.IntegerField(default=15) # Penalty if delay > 15
    v2_delay_penalty_mult = models.FloatField(default=10.0)
    v2_volume_boost_mult = models.FloatField(default=25.0)
    v2_decay_start_days = models.IntegerField(default=90)
    v2_decay_penalty_mult = models.FloatField(default=0.5)
    v2_volume_percentile = models.FloatField(default=0.5) # Percentile of late money that dictates the baseline delay.
    
    # Cache fields
    last_order_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return self.name

    def calculate_cibil_v1(self, save=True, payments_list=None):
        """
        Calculates CIBIL score (V1) between 100 and 1000.
        Score = 1000 - (Avg Delay * Weight) - (Days Inactive * Weight)
        """
        base_score = 1000
        
        if payments_list is None:
            payments_list = list(self.payments.all())
            
        # Completely strip out negative amounts (errors) and zero amounts for calculations
        valid_payments = [p for p in payments_list if p.amount and float(p.amount) > 0]
            
        all_payments = sorted(valid_payments, key=lambda p: p.date if p.date else timezone.now().date(), reverse=True)
        # Fix: Look at the last 5 payments overall, not just late payments, so reformed defaulters can recover.
        last_5 = all_payments[:5]
        
        if last_5:
            total_amount = sum(float(p.amount) for p in last_5)
            # Weighted average delay: sum(delay * amount) / sum(amount)
            avg_delay = sum(p.late_only_delay * float(p.amount) for p in last_5) / total_amount
        else:
            avg_delay = 0
            
        days_inactive = 0
        if self.last_order_date:
            days_inactive = (timezone.now().date() - self.last_order_date).days
        else:
            days_inactive = 0 # No valid orders means no inactivity penalty
                
        penalty = (avg_delay * self.delay_weight_v1) + (days_inactive * self.inactivity_weight_v1)
            
        final_score = base_score - penalty
        self.cibil_score_v1 = max(100, min(1000, int(final_score)))
        if save:
            self.save(update_fields=['cibil_score_v1'])
        return self.cibil_score_v1

    def calculate_cibil_v2(self, save=True, payments_list=None):
        """
        Calculates CIBIL score (V2) between 300 and 1000.
        Logic based on thresholds for delay, log-scale volume boost, and inactivity decay.
        """
        score = 300
        max_score = 1000
        
        if payments_list is None:
            payments_list = list(self.payments.all())
            
        # Completely strip out negative amounts (errors) and zero amounts for calculations
        valid_payments = [p for p in payments_list if p.amount and float(p.amount) > 0]
        
        # 1. DELAY LOGIC (Amount-Weighted Median to handle installments & outliers)
        # Fix: Ignore tiny anomalies under 100 to prevent a forgotten 10rs invoice from ruining a whale's score
        late_payments = [p for p in valid_payments if p.late_only_delay > 0 and float(p.amount) >= 100]
        
        if late_payments:
            # Sort by delay ascending
            late_payments.sort(key=lambda x: x.late_only_delay)
            total_late_amount = sum(float(p.amount) for p in late_payments)
            
            cumulative_amount = 0
            median_delay = 0
            # Find the delay where the defined percentage of the late monetary volume is reached
            for p in late_payments:
                cumulative_amount += float(p.amount)
                if cumulative_amount >= (total_late_amount * self.v2_volume_percentile):
                    median_delay = p.late_only_delay
                    break
        else:
            median_delay = 0
        
        if median_delay <= self.gold_limit:
            score += 300 # Gold Class
        elif median_delay <= self.average_limit:
            score += 200  # Average Class
        else:
            # Proportional penalty only for delay exceeding the average limit
            excess = median_delay - self.average_limit
            score += 100 - (excess * self.v2_delay_penalty_mult)
            
        # 2. VOLUME BONUS (Log Scale)
        unique_invoices = set()
        total_sales = 0
        for p in valid_payments:
            if (p.invoice_date, p.amount) not in unique_invoices:
                unique_invoices.add((p.invoice_date, p.amount))
                total_sales += float(p.amount)
                
        if total_sales > 0:
            volume_boost = math.log10(float(total_sales)) * self.v2_volume_boost_mult
            score += volume_boost
            
        # 3. RECENCY DECAY
        days_since_last = 0
        if self.last_order_date:
            days_since_last = (timezone.now().date() - self.last_order_date).days
        else:
            days_since_last = 0 # No valid orders means no inactivity penalty
            
        if days_since_last > self.v2_decay_start_days:
            decay_penalty = (days_since_last - self.v2_decay_start_days) * self.v2_decay_penalty_mult
            score -= decay_penalty
            
        # Final Clip
        self.cibil_score_v2 = max(300, min(max_score, int(score)))
        if save:
            self.save(update_fields=['cibil_score_v2'])
        return self.cibil_score_v2

class Payment(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name= 'payments')
    date = models.DateField(null=True, blank=True)
    invoice_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    unused_amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_status = models.CharField(max_length=50) # Paid, Pending
    delay = models.IntegerField(default=0)
    late_only_delay = models.IntegerField(default=0)
    external_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    @property
    def display_id(self):
        if self.external_id and '_' in self.external_id:
            parts = self.external_id.split('_', 1)
            return f"Pay: {parts[0]} | Inv: {parts[1]}"
        return self.external_id

    def __str__(self):
        return f"{self.customer.name} - {self.display_id or self.amount} ({self.payment_status})"

class SystemSettings(models.Model):
    """
    Singleton model to hold global application settings.
    """
    google_sheet_url = models.URLField(verbose_name="Payments Google Sheet URL", max_length=500, blank=True, null=True, help_text="Public URL to the Payments Google Sheet (Anyone with the link can view)")
    invoice_google_sheet_url = models.URLField(verbose_name="Invoices Google Sheet URL", max_length=500, blank=True, null=True, help_text="Public URL to the Invoices Google Sheet (Anyone with the link can view)")
    delay_bucket_thresholds = models.CharField(verbose_name="Delay Bucket Thresholds", max_length=100, default="5, 15, 30, 60", help_text="Comma-separated list of days for delay buckets. Example: 5, 15, 30, 60")
    
    @classmethod
    def get_settings(cls):
        settings, created = cls.objects.get_or_create(id=1)
        return settings
    
    def save(self, *args, **kwargs):
        # Force the ID to be 1 so it acts as a Singleton
        self.id = 1
        super().save(*args, **kwargs)


from django.db import models
from django.db.models import Avg, Max, Sum
from django.utils import timezone
import math

class Customer(models.Model):
    customer_id_str = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    
    # --- CIBIL V1 (Dynamic) ---
    cibil_score_v1 = models.IntegerField(default=1000)
    delay_weight_v1 = models.FloatField(default=5.0)
    inactivity_weight_v1 = models.FloatField(default=2.0)
    
    # --- CIBIL V2 (Standard) ---
    cibil_score_v2 = models.IntegerField(default=300)
    gold_limit = models.IntegerField(default=4) # Bonus if delay <= 4
    average_limit = models.IntegerField(default=15) # Penalty if delay > 15
    v2_delay_penalty_mult = models.FloatField(default=10.0)
    v2_volume_boost_mult = models.FloatField(default=25.0)
    v2_decay_start_days = models.IntegerField(default=90)
    v2_decay_penalty_mult = models.FloatField(default=0.5)
    
    # Cache fields
    last_order_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return self.name

    def calculate_cibil_v1(self):
        """
        Calculates CIBIL score (V1) between 100 and 1000.
        Score = 1000 - (Avg Delay * Weight) - (Days Inactive * Weight)
        """
        base_score = 1000
        avg_delay = self.payments.filter(late_only_delay__gt=0).aggregate(Avg('late_only_delay'))['late_only_delay__avg'] or 0
        days_inactive = 0
        if self.last_order_date:
            days_inactive = (timezone.now().date() - self.last_order_date).days
        else:
            days_inactive = 365
                
        final_score = base_score - (avg_delay * self.delay_weight_v1) - (days_inactive * self.inactivity_weight_v1)
        self.cibil_score_v1 = max(100, min(1000, int(final_score)))
        self.save(update_fields=['cibil_score_v1'])
        return self.cibil_score_v1

    def calculate_cibil_v2(self):
        """
        Calculates CIBIL score (V2) between 300 and 1000.
        Logic based on thresholds for delay, log-scale volume boost, and inactivity decay.
        """
        score = 300
        max_score = 1000
        
        # 1. DELAY LOGIC
        avg_delay = self.payments.filter(late_only_delay__gt=0).aggregate(Avg('late_only_delay'))['late_only_delay__avg'] or 0
        if avg_delay <= self.gold_limit:
            score += 400 # Gold Class
        elif avg_delay <= self.average_limit:
            score += 200 # Average Class
        else:
            score -= (avg_delay * self.v2_delay_penalty_mult) # Heavy penalty
            
        # 2. VOLUME BONUS (Log Scale)
        total_sales = self.payments.aggregate(Sum('amount'))['amount__sum'] or 0
        if total_sales > 0:
            volume_boost = math.log10(float(total_sales)) * self.v2_volume_boost_mult
            score += volume_boost
            
        # 3. RECENCY DECAY
        days_since_last = 0
        if self.last_order_date:
            days_since_last = (timezone.now().date() - self.last_order_date).days
        else:
            days_since_last = 365
            
        if days_since_last > self.v2_decay_start_days:
            decay_penalty = (days_since_last - self.v2_decay_start_days) * self.v2_decay_penalty_mult
            score -= decay_penalty
            
        # Final Clip
        self.cibil_score_v2 = max(300, min(max_score, int(score)))
        self.save(update_fields=['cibil_score_v2'])
        return self.cibil_score_v2

class Payment(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payments')
    date = models.DateField(null=True, blank=True)
    invoice_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    unused_amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_status = models.CharField(max_length=50) # Paid, Pending
    delay = models.IntegerField(default=0)
    late_only_delay = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.customer.name} - {self.amount} ({self.payment_status})"

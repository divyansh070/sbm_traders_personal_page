import os, django, time
from datetime import datetime
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sbm_website.settings')
django.setup()

from dashboard_app.models import Customer, Payment

print("Updating payment statuses and delays...")
payments = Payment.objects.all()
today = timezone.now().date()

updated_payments = []
for p in payments:
    changed = False
    
    # Status
    if p.unused_amount > 1:
        if p.payment_status != 'Pending':
            p.payment_status = 'Pending'
            changed = True
            
        # Ongoing delay:
        start_date = p.date if p.date else p.invoice_date
        if start_date:
            true_delay = (today - start_date).days
            if true_delay > 0 and p.late_only_delay != true_delay:
                p.late_only_delay = true_delay
                p.delay = true_delay
                changed = True
    else:
        if p.payment_status != 'Paid':
            p.payment_status = 'Paid'
            changed = True
            
    if changed:
        updated_payments.append(p)

if updated_payments:
    Payment.objects.bulk_update(updated_payments, ['payment_status', 'late_only_delay', 'delay'], batch_size=2000)
    print(f"Fixed {len(updated_payments)} payments.")

print("Recalculating all CIBIL scores natively...")
customers = list(Customer.objects.prefetch_related('payments'))
for c in customers:
    c.calculate_cibil_v1(save=False)
    c.calculate_cibil_v2(save=False)

Customer.objects.bulk_update(customers, ['cibil_score_v1', 'cibil_score_v2'], batch_size=500)
print(f"Successfully recalculated CIBIL scores for {len(customers)} customers.")

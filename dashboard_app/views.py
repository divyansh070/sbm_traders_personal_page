from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Avg, Count
from django.contrib import messages
from django.core.management import call_command
from .models import Customer, Payment

def dashboard_overview(request):
    payments = Payment.objects.all()
    
    unique_invoices_all = set()
    total_amount = 0
    for p in payments:
        if p.amount and (p.customer_id, p.invoice_date, p.amount) not in unique_invoices_all:
            unique_invoices_all.add((p.customer_id, p.invoice_date, p.amount))
            total_amount += float(p.amount)
            
    total_unused = payments.aggregate(Sum('unused_amount'))['unused_amount__sum'] or 0
    avg_delay = payments.filter(late_only_delay__gt=0).aggregate(Avg('late_only_delay'))['late_only_delay__avg'] or 0
    
    # Top 10 customers calculated cleanly
    customers = list(Customer.objects.prefetch_related('payments'))
    for c in customers:
        unique_invs = set()
        c_total = 0
        for p in c.payments.all():
            if p.amount and (p.invoice_date, p.amount) not in unique_invs:
                unique_invs.add((p.invoice_date, p.amount))
                c_total += float(p.amount)
        c.total_payment = c_total
        
    customers.sort(key=lambda x: x.total_payment, reverse=True)
    top_customers = customers[:10]
    
    context = {
        'total_amount': total_amount,
        'total_unused': total_unused,
        'avg_delay': avg_delay,
        'top_customers': top_customers,
    }
    return render(request, 'dashboard/overview.html', context)

def customer_list(request):
    customers = list(Customer.objects.prefetch_related('payments'))
    for c in customers:
        unique_invs = set()
        c_total = 0
        for p in c.payments.all():
            if p.amount and (p.invoice_date, p.amount) not in unique_invs:
                unique_invs.add((p.invoice_date, p.amount))
                c_total += float(p.amount)
        c.total_ordered = c_total
        c.order_count = len(unique_invs)
        
    customers.sort(key=lambda x: x.total_ordered, reverse=True)
    
    context = {
        'customers': customers
    }
    return render(request, 'dashboard/customer_list.html', context)

def customer_detail(request, customer_id):
    try:
        customer = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        messages.warning(request, 'Customer not found. The database may have been synced — please select from the list below.')
        return redirect('dashboard:customer_list')
    payments = customer.payments.all().order_by('-date')
    
    unique_invs = set()
    total_ordered = 0
    for p in payments:
        if p.amount and (p.invoice_date, p.amount) not in unique_invs:
            unique_invs.add((p.invoice_date, p.amount))
            total_ordered += float(p.amount)
    
    context = {
        'customer': customer,
        'payments': payments,
        'total_ordered': total_ordered
    }
    return render(request, 'dashboard/customer_detail.html', context)

def update_customer_settings(request, customer_id):
    if request.method == 'POST':
        customer = get_object_or_404(Customer, id=customer_id)
        # V1 Params
        customer.delay_weight_v1 = float(request.POST.get('delay_weight_v1', 5.0))
        customer.inactivity_weight_v1 = float(request.POST.get('inactivity_weight_v1', 2.0))
        
        # V2 Params
        customer.gold_limit = int(request.POST.get('gold_limit', 4))
        customer.average_limit = int(request.POST.get('average_limit', 15))
        customer.v2_delay_penalty_mult = float(request.POST.get('v2_delay_penalty_mult', 10.0))
        customer.v2_volume_boost_mult = float(request.POST.get('v2_volume_boost_mult', 25.0))
        customer.v2_decay_start_days = int(request.POST.get('v2_decay_start_days', 90))
        customer.v2_decay_penalty_mult = float(request.POST.get('v2_decay_penalty_mult', 0.5))
        
        customer.save()
        customer.calculate_cibil_v1()
        customer.calculate_cibil_v2()
    return redirect('dashboard:customer_detail', customer_id=customer_id)

from utils import get_processed_data, import_from_dataframe

def sync_database(request):
    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            messages.error(request, 'Please select an Excel file to upload.')
            return redirect('dashboard:overview')
            
        try:
            df = get_processed_data(excel_file)
            if df is None:
                messages.error(request, 'Failed to process the uploaded file. Please ensure it is the correct format.')
                return redirect('dashboard:overview')
                
            customers_created, payments_created = import_from_dataframe(df)
            messages.success(request, f'Database synced successfully! Imported {customers_created} customers and {payments_created} payments.')
        except Exception as e:
            messages.error(request, f'Sync failed: {str(e)}')
    return redirect('dashboard:overview')


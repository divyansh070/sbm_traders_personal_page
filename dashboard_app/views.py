from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Avg, Count
from .models import Customer, Payment

def dashboard_overview(request):
    total_amount = Payment.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    total_unused = Payment.objects.aggregate(Sum('unused_amount'))['unused_amount__sum'] or 0
    avg_delay = Payment.objects.filter(late_only_delay__gt=0).aggregate(Avg('late_only_delay'))['late_only_delay__avg'] or 0
    
    # Top 10 customers
    top_customers = Customer.objects.annotate(
        total_payment=Sum('payments__amount')
    ).order_by('-total_payment')[:10]
    
    context = {
        'total_amount': total_amount,
        'total_unused': total_unused,
        'avg_delay': avg_delay,
        'top_customers': top_customers,
    }
    return render(request, 'dashboard/overview.html', context)

def customer_list(request):
    customers = Customer.objects.annotate(
        total_ordered=Sum('payments__amount'),
        order_count=Count('payments')
    ).order_by('-total_ordered')
    
    context = {
        'customers': customers
    }
    return render(request, 'dashboard/customer_list.html', context)

def customer_detail(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    payments = customer.payments.all().order_by('-date')
    
    total_ordered = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    
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

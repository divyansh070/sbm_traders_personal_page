from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Avg, Count
from django.contrib import messages
from django.core.management import call_command
from .models import Customer, Payment
from django.utils import timezone
from django.db import connection

def dashboard_overview(request):
    with connection.cursor() as cursor:
        # Global Total Sales
        cursor.execute("""
            SELECT SUM(amount) FROM (
                SELECT DISTINCT customer_id, invoice_date, amount
                FROM dashboard_app_payment
                WHERE amount IS NOT NULL
            ) u
        """)
        row = cursor.fetchone()
        total_amount = float(row[0] or 0)
        
        # Top 10 Customers
        cursor.execute("""
            SELECT c.id, c.name, SUM(u.amount) as total_sales
            FROM dashboard_app_customer c
            JOIN (
                SELECT DISTINCT customer_id, invoice_date, amount
                FROM dashboard_app_payment
                WHERE amount IS NOT NULL
            ) u ON c.id = u.customer_id
            GROUP BY c.id, c.name
            ORDER BY total_sales DESC
            LIMIT 10
        """)
        top_customers = []
        for row in cursor.fetchall():
            top_customers.append({'id': row[0], 'name': row[1], 'total_payment': float(row[2] or 0)})
            
    total_unused = Payment.objects.aggregate(Sum('unused_amount'))['unused_amount__sum'] or 0
    avg_delay = Payment.objects.filter(late_only_delay__gt=0).aggregate(Avg('late_only_delay'))['late_only_delay__avg'] or 0
    
    context = {
        'total_amount': total_amount,
        'total_unused': total_unused,
        'avg_delay': avg_delay,
        'top_customers': top_customers,
    }
    return render(request, 'dashboard/overview.html', context)

def pending_collections(request):
    with connection.cursor() as cursor:
        # Get customers with outstanding balances
        cursor.execute("""
            SELECT c.id, c.name, SUM(p.unused_amount) as total_outstanding
            FROM dashboard_app_customer c
            JOIN dashboard_app_payment p ON c.id = p.customer_id
            WHERE p.unused_amount > 0
            GROUP BY c.id, c.name
            ORDER BY total_outstanding DESC
        """)
        
        customers = []
        customer_map = {}
        for row in cursor.fetchall():
            c = {'id': row[0], 'name': row[1], 'total_outstanding': float(row[2] or 0), 'pending_invoices': []}
            customers.append(c)
            customer_map[c['id']] = c
            
        # Get only the outstanding invoices
        if customers:
            cursor.execute("""
                SELECT customer_id, invoice_date, date, unused_amount, delay
                FROM dashboard_app_payment
                WHERE unused_amount > 0
                ORDER BY invoice_date ASC NULLS LAST
            """)
            
            today = timezone.now().date()
            for row in cursor.fetchall():
                cid, inv_date, p_date, unused, delay = row
                if cid in customer_map:
                    # Calculate ongoing delay
                    ongoing_delay = 0
                    if p_date:
                        ongoing_delay = (today - p_date).days
                    elif inv_date:
                        ongoing_delay = (today - inv_date).days
                        
                    customer_map[cid]['pending_invoices'].append({
                        'invoice_date': inv_date,
                        'date': p_date,
                        'unused_amount': float(unused or 0),
                        'delay': delay,
                        'ongoing_delay': ongoing_delay
                    })
                    
    context = {
        'customers': customers
    }
    return render(request, 'dashboard/pending_collections.html', context)

def customer_list(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT c.id, c.name, SUM(u.amount) as total_ordered, COUNT(u.amount) as order_count, c.cibil_score_v1, c.cibil_score_v2
            FROM dashboard_app_customer c
            LEFT JOIN (
                SELECT DISTINCT customer_id, invoice_date, amount
                FROM dashboard_app_payment
                WHERE amount IS NOT NULL
            ) u ON c.id = u.customer_id
            GROUP BY c.id, c.name, c.cibil_score_v1, c.cibil_score_v2
            ORDER BY total_ordered DESC NULLS LAST
        """)
        customers = []
        for row in cursor.fetchall():
            customers.append({
                'id': row[0], 'name': row[1], 'total_ordered': float(row[2] or 0), 
                'order_count': row[3] or 0, 'cibil_score_v1': row[4], 'cibil_score_v2': row[5]
            })
    
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
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT SUM(amount) FROM (
                SELECT DISTINCT invoice_date, amount
                FROM dashboard_app_payment
                WHERE customer_id = %s AND amount IS NOT NULL
            ) u
        """, [customer_id])
        row = cursor.fetchone()
        total_ordered = float(row[0] or 0)
    
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


from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Avg, Count
from django.contrib import messages
from django.core.management import call_command
from .models import Customer, Payment, SystemSettings
from django.utils import timezone
from django.db import connection
import json

def dashboard_overview(request):
    with connection.cursor() as cursor:
        # Global Total Ordered
        cursor.execute("""
            SELECT SUM(amount) FROM dashboard_app_payment WHERE amount IS NOT NULL
        """)
        row = cursor.fetchone()
        total_ordered_amount = float(row[0] or 0)
        
        # Global Total Collected (Payments Only)
        cursor.execute("""
            SELECT SUM(amount) FROM dashboard_app_payment 
            WHERE amount IS NOT NULL AND payment_status != 'Pending'
        """)
        row = cursor.fetchone()
        total_collected_amount = float(row[0] or 0)
        
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
            
    total_credit = Payment.objects.aggregate(Sum('unused_amount'))['unused_amount__sum'] or 0
    total_debt = Payment.objects.filter(payment_status='Pending').aggregate(Sum('amount'))['amount__sum'] or 0
    net_outstanding = max(total_debt - total_credit, 0)
    
    avg_delay = Payment.objects.filter(late_only_delay__gt=0).aggregate(Avg('late_only_delay'))['late_only_delay__avg'] or 0
    
    settings = SystemSettings.get_settings()
    
    def parse_thresholds(thresh_str):
        try:
            th = [int(t.strip()) for t in (thresh_str or "5, 15, 30, 60").split(',') if t.strip().isdigit()]
            th = sorted(list(set(th)))
            if not th: return [5, 15, 30, 60]
            return th
        except Exception:
            return [5, 15, 30, 60]
            
    def generate_labels(th):
        labels = []
        prev = 0
        for t in th:
            labels.append(f"0-{t} Days" if prev == 0 else f"{prev + 1}-{t} Days")
            prev = t
        labels.append(f"{prev + 1}+ Days")
        return labels

    pending_th = parse_thresholds(settings.delay_bucket_thresholds)
    pending_labels = generate_labels(pending_th)
    delay_buckets = {label: 0 for label in pending_labels}
    
    customer_th = parse_thresholds(settings.customer_delay_thresholds)
    customer_labels = generate_labels(customer_th)
    customer_buckets = {label: 0 for label in customer_labels}
    
    payment_th = parse_thresholds(settings.payment_delay_thresholds)
    payment_labels = generate_labels(payment_th)
    payment_buckets = {label: 0 for label in payment_labels}
    
    # 1. Pending Invoices (Count)
    for delay in Payment.objects.filter(payment_status='Pending').values_list('delay', flat=True):
        placed = False
        for i, t in enumerate(pending_th):
            if delay <= t:
                delay_buckets[pending_labels[i]] += 1
                placed = True
                break
        if not placed:
            delay_buckets[pending_labels[-1]] += 1
            
    # 2. Payment Completion (Volume)
    for delay, amount in Payment.objects.exclude(payment_status='Pending').filter(amount__gt=0).values_list('late_only_delay', 'amount'):
        placed = False
        for i, t in enumerate(payment_th):
            if delay <= t:
                payment_buckets[payment_labels[i]] += float(amount or 0)
                placed = True
                break
        if not placed:
            payment_buckets[payment_labels[-1]] += float(amount or 0)
            
    # 3. Customer Average Delay (Count)
    customer_avg_delays = Payment.objects.exclude(payment_status='Pending').values('customer_id').annotate(avg_delay=Avg('late_only_delay'))
    for c in customer_avg_delays:
        avg_d = c['avg_delay'] or 0
        placed = False
        for i, t in enumerate(customer_th):
            if avg_d <= t:
                customer_buckets[customer_labels[i]] += 1
                placed = True
                break
        if not placed:
            customer_buckets[customer_labels[-1]] += 1
    
    context = {
        'total_amount': total_ordered_amount,
        'total_unused': net_outstanding, # Renamed internally to mean net outstanding debt
        'total_collected': total_collected_amount,
        'total_debt_value': net_outstanding,
        'avg_delay': avg_delay,
        'top_customers': top_customers,
        
        'delay_buckets_json': json.dumps(list(delay_buckets.values())),
        'delay_labels_json': json.dumps(pending_labels),
        
        'customer_buckets_json': json.dumps(list(customer_buckets.values())),
        'customer_labels_json': json.dumps(customer_labels),
        
        'payment_buckets_json': json.dumps(list(payment_buckets.values())),
        'payment_labels_json': json.dumps(payment_labels),
    }
    return render(request, 'dashboard/overview.html', context)

def pending_collections(request):
    with connection.cursor() as cursor:
        # Get customers with outstanding balances (Net Debt > 0)
        # Net Debt = SUM(Pending Invoices) - SUM(Unused Advance Credits)
        cursor.execute("""
            SELECT 
                c.id, 
                c.name, 
                COALESCE(SUM(CASE WHEN p.payment_status = 'Pending' THEN p.amount ELSE 0 END), 0) as total_debt,
                COALESCE(SUM(p.unused_amount), 0) as total_credit
            FROM dashboard_app_customer c
            JOIN dashboard_app_payment p ON c.id = p.customer_id
            GROUP BY c.id, c.name
            HAVING (COALESCE(SUM(CASE WHEN p.payment_status = 'Pending' THEN p.amount ELSE 0 END), 0) - COALESCE(SUM(p.unused_amount), 0)) > 0
            ORDER BY (COALESCE(SUM(CASE WHEN p.payment_status = 'Pending' THEN p.amount ELSE 0 END), 0) - COALESCE(SUM(p.unused_amount), 0)) DESC
        """)
        
        customers = []
        customer_map = {}
        for row in cursor.fetchall():
            c_id = row[0]
            c_name = row[1]
            total_debt = float(row[2] or 0)
            total_credit = float(row[3] or 0)
            net_outstanding = total_debt - total_credit
            
            c = {
                'id': c_id, 
                'name': c_name, 
                'total_outstanding': net_outstanding, 
                'total_debt': total_debt,
                'total_credit': total_credit,
                'pending_invoices': []
            }
            customers.append(c)
            customer_map[c['id']] = c
            
        # Get only the outstanding invoices
        if customers:
            cursor.execute("""
                SELECT customer_id, invoice_date, date, amount, delay
                FROM dashboard_app_payment
                WHERE payment_status = 'Pending'
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
            SELECT c.id, c.name, SUM(p.amount) as total_ordered, COUNT(p.amount) as order_count, c.cibil_score_v1, c.cibil_score_v2, c.customer_id_str
            FROM dashboard_app_customer c
            LEFT JOIN dashboard_app_payment p ON c.id = p.customer_id AND p.amount IS NOT NULL
            GROUP BY c.id, c.name, c.cibil_score_v1, c.cibil_score_v2, c.customer_id_str
            ORDER BY total_ordered DESC NULLS LAST
        """)
        customers = []
        for row in cursor.fetchall():
            customers.append({
                'id': row[0], 'name': row[1], 'total_ordered': float(row[2] or 0), 
                'order_count': row[3] or 0, 'cibil_score_v1': row[4], 'cibil_score_v2': row[5],
                'customer_id_str': row[6]
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
            SELECT SUM(amount) FROM dashboard_app_payment
            WHERE customer_id = %s AND amount IS NOT NULL AND amount > 0
        """, [customer.id])
        row = cursor.fetchone()
        total_ordered = float(row[0] or 0)
        
        cursor.execute("""
            SELECT SUM(amount) FROM dashboard_app_payment
            WHERE customer_id = %s AND amount IS NOT NULL AND amount > 0 AND payment_status != 'Pending'
        """, [customer.id])
        row = cursor.fetchone()
        total_collected = float(row[0] or 0)
    
    context = {
        'customer': customer,
        'payments': payments,
        'total_ordered': total_ordered,
        'total_collected': total_collected
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
    import pandas as pd
    if request.method == 'POST':
        excel_files = request.FILES.getlist('excel_files')
        if not excel_files:
            messages.error(request, 'Please select at least one Excel file to upload.')
            return redirect('dashboard:overview')
            
        try:
            all_dfs = []
            for f in excel_files:
                df = get_processed_data(f)
                if df is not None:
                    all_dfs.append(df)
            
            if not all_dfs:
                messages.error(request, 'Failed to process the uploaded files. Please ensure they are in the correct format.')
                return redirect('dashboard:overview')
                
            # Combine all processed dataframes
            combined_df = pd.concat(all_dfs, ignore_index=True)
            
            # Sort by Amount so that the lowest balance (most recent) comes first
            if 'Amount' in combined_df.columns:
                combined_df = combined_df.sort_values('Amount')
            
            # Drop duplicates by External ID
            if 'External ID' in combined_df.columns:
                combined_df = combined_df.drop_duplicates(subset=['External ID'], keep='first')
                
            # Now drop Amount == 0 for Pending invoices (fully paid invoices from AR Aging)
            if 'Payment_Status' in combined_df.columns and 'Amount' in combined_df.columns:
                combined_df = combined_df[~((combined_df['Payment_Status'] == 'Pending') & (combined_df['Amount'] == 0))]
                
            # Clear existing payments so the new sheets act as the source of truth
            Payment.objects.all().delete()
                
            customers_created, payments_created = import_from_dataframe(combined_df)
            
            # Delete any old customers that no longer have payments in the new sheets
            deleted_customers, _ = Customer.objects.filter(payments__isnull=True).delete()
            
            messages.success(request, f'Database synced successfully! Imported {customers_created} customers and {payments_created} payments. Removed {deleted_customers} old customers.')
        except Exception as e:
            messages.error(request, f'Sync failed: {str(e)}')
    return redirect('dashboard:overview')

from utils import get_processed_data_from_google_sheet

def sync_google_sheet(request):
    if request.method == 'POST':
        settings = SystemSettings.get_settings()
        if not settings.google_sheet_url and not settings.invoice_google_sheet_url:
            messages.error(request, 'No Google Sheet URLs are configured. Please set them in Global Settings.')
            return redirect('dashboard:overview')
            
        try:
            all_dfs = []
            import pandas as pd
            
            if settings.google_sheet_url:
                df_pay = get_processed_data_from_google_sheet(settings.google_sheet_url)
                if df_pay is not None:
                    all_dfs.append(df_pay)
                    
            if settings.invoice_google_sheet_url:
                df_inv = get_processed_data_from_google_sheet(settings.invoice_google_sheet_url)
                if df_inv is not None:
                    all_dfs.append(df_inv)
                    
            if not all_dfs:
                messages.error(request, 'Failed to download or process the Google Sheets. Please check the URLs and their sharing permissions.')
                return redirect('dashboard:overview')
                
            combined_df = pd.concat(all_dfs, ignore_index=True)
            
            if 'External ID' in combined_df.columns:
                combined_df = combined_df.drop_duplicates(subset=['External ID'])
                
            # Clear existing payments so the new sheet acts as the source of truth
            Payment.objects.all().delete()
                
            customers_created, payments_created = import_from_dataframe(combined_df)
            
            # Delete any old customers that no longer have payments in the new sheet
            deleted_customers, _ = Customer.objects.filter(payments__isnull=True).delete()
            
            messages.success(request, f'Google Sheet synced successfully! Imported {customers_created} customers and {payments_created} payments. Removed {deleted_customers} old customers.')
        except Exception as e:
            messages.error(request, f'Google Sheet sync failed: {str(e)}')
    return redirect('dashboard:overview')

def global_settings(request):
    settings = SystemSettings.get_settings()
    
    if request.method == 'POST':
        google_sheet_url = request.POST.get('google_sheet_url', '').strip()
        invoice_google_sheet_url = request.POST.get('invoice_google_sheet_url', '').strip()
        delay_bucket_thresholds = request.POST.get('delay_bucket_thresholds', '').strip()
        customer_delay_thresholds = request.POST.get('customer_delay_thresholds', '').strip()
        payment_delay_thresholds = request.POST.get('payment_delay_thresholds', '').strip()
        
        settings.google_sheet_url = google_sheet_url
        settings.invoice_google_sheet_url = invoice_google_sheet_url
        
        if delay_bucket_thresholds:
            settings.delay_bucket_thresholds = delay_bucket_thresholds
        if customer_delay_thresholds:
            settings.customer_delay_thresholds = customer_delay_thresholds
        if payment_delay_thresholds:
            settings.payment_delay_thresholds = payment_delay_thresholds
            
        settings.save()
        
        messages.success(request, 'Global settings saved successfully.')
        return redirect('dashboard:global_settings')
        
    context = {
        'settings': settings
    }
    return render(request, 'dashboard/settings.html', context)

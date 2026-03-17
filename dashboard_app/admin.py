from django.contrib import admin
from .models import Customer, Payment

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'customer_id_str', 'cibil_score_v1', 'cibil_score_v2')
    search_fields = ('name', 'customer_id_str')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('customer', 'amount', 'date', 'payment_status')
    list_filter = ('payment_status', 'date')
    search_fields = ('customer__name', 'payment_status')

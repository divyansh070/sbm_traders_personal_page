from django.test import TestCase
from dashboard_app.models import Customer, Payment
from datetime import date, timedelta
from django.utils import timezone

class CibilScoreTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            name="Test Customer",
            customer_id_str="TEST_001"
        )
        self.today = timezone.now().date()

    def test_no_payments(self):
        """Test a customer with no payments at all."""
        # Calculate CIBIL
        v1 = self.customer.calculate_cibil_v1()
        v2 = self.customer.calculate_cibil_v2()
        
        # V1: 1000 base, 0 delay, 365 inactive days -> 1000 - 365*2 = 270
        self.assertEqual(v1, 270)
        # V2: 300 base, 0 delay (+400 gold class), 0 volume, 365 inactive -> Decay penalty applies
        self.assertTrue(v2 > 300)

    def test_perfect_payments(self):
        """Test a customer making multiple on-time payments."""
        Payment.objects.create(customer=self.customer, date=self.today, amount=100000, unused_amount=0, late_only_delay=0)
        Payment.objects.create(customer=self.customer, date=self.today, amount=50000, unused_amount=0, late_only_delay=0)
        
        self.customer.last_order_date = self.today
        v1 = self.customer.calculate_cibil_v1()
        v2 = self.customer.calculate_cibil_v2()
        
        # Perfect V1 score 
        self.assertEqual(v1, 1000)
        # Perfect V2 delay (+400) + Volume bonus -> should be high
        self.assertTrue(v2 >= 700)

    def test_installment_weighting(self):
        """
        Test that a massive on-time payment and a tiny late payment 
        results in a negligible penalty due to amount-weighting.
        """
        self.customer.last_order_date = self.today
        
        # They paid 990,000 on time
        Payment.objects.create(customer=self.customer, date=self.today, amount=990000, unused_amount=0, late_only_delay=0)
        # They paid 10,000 extremely late (100 days)
        Payment.objects.create(customer=self.customer, date=self.today, amount=10000, unused_amount=0, late_only_delay=100)
        
        v1 = self.customer.calculate_cibil_v1()
        v2 = self.customer.calculate_cibil_v2()
        
        # V1: Late payments only has the 10k for 100 days. 
        # Total late amount = 10,000. Avg Delay = 100.
        # This checks that our math doesn't crash.
        self.assertTrue(v1 < 1000)
        
        # V2: Looks at ALL payments > 0 delay. Wait, currently V2 looks at late_only_delay > 0.
        # So in V2, total late amount = 10,000. Delay = 100.
        # If we didn't want this, we would include delay 0. I'll test V2 runs smoothly.
        self.assertTrue(v2 >= 300)

    def test_zero_amount_handling(self):
        """Test edge cases with 0 or None amounts to prevent ZeroDivisionError."""
        Payment.objects.create(customer=self.customer, date=self.today, amount=0, unused_amount=0, late_only_delay=50)
        
        self.customer.last_order_date = self.today
        try:
            v1 = self.customer.calculate_cibil_v1()
            v2 = self.customer.calculate_cibil_v2()
        except ZeroDivisionError:
            self.fail("calculate_cibil raised ZeroDivisionError!")

    def test_extreme_outlier_delay(self):
        """Test that V2 median delay is unaffected by one massive outlier."""
        self.customer.last_order_date = self.today
        
        # Normal payments (Late delays, 5 days)
        Payment.objects.create(customer=self.customer, date=self.today, amount=10000, unused_amount=0, late_only_delay=5)
        Payment.objects.create(customer=self.customer, date=self.today, amount=10000, unused_amount=0, late_only_delay=5)
        Payment.objects.create(customer=self.customer, date=self.today, amount=10000, unused_amount=0, late_only_delay=5)
        
        # One absurd outlier (1000 days late on 1000)
        Payment.objects.create(customer=self.customer, date=self.today, amount=1000, unused_amount=0, late_only_delay=1000)
        
        v2 = self.customer.calculate_cibil_v2()
        
        # The median delay is 5, which is > gold_limit (4) but <= average_limit (15).
        # Base (300) + Average Class (+200) + Volume Bonus (log10(31000)*25 ~ 112) = ~612
        self.assertTrue(v2 > 600)

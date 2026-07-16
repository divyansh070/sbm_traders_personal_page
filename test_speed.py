import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sbm_website.settings')
django.setup()

from utils import get_processed_data, import_from_dataframe
import pandas as pd

start=time.time()
df1 = get_processed_data('Test_Integration_Invoice.xlsx')
df2 = get_processed_data('Test_Integration_Customer_Payment.xlsx')
df = pd.concat([df1,df2], ignore_index=True)
print('Data Processed:', len(df))
import_from_dataframe(df)
print('Total Time:', time.time()-start)

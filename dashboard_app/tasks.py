import io
from celery import shared_task
from django.core.management import call_command

@shared_task(bind=True)
def sync_database_task(self):
    out = io.StringIO()
    # Call the management command, capturing stdout
    call_command('import_data', stdout=out)
    output = out.getvalue()
    # Extract the last line which contains the success summary
    summary_line = output.strip().split('\\n')[-1]
    return summary_line

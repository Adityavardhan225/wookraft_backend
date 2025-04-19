@echo off
cd /d C:\Users\adity\Desktop\WooPOS
set PYTHONPATH=C:\Users\adity\Desktop\WooPOS
echo Starting beat scheduler...
celery -A routes.campaign.sending_campaign.models.celery_worker beat -l info
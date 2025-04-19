@echo off
cd /d C:\Users\adity\Desktop\WooPOS
set PYTHONPATH=C:\Users\adity\Desktop\WooPOS
echo Starting email worker...
celery -A routes.campaign.sending_campaign.models.celery_worker worker -Q emails -n email@%%h -l info --concurrency=2
@echo off
cd /d C:\Users\adity\Desktop\WooPOS
set PYTHONPATH=C:\Users\adity\Desktop\WooPOS

echo Starting all Celery workers...

REM Start email worker
start cmd /k "title Email Worker && color 0A && C:\Users\adity\Desktop\WooPOS\start_email_worker.bat"

REM Start campaign worker
start cmd /k "title Campaign Worker && color 0B && C:\Users\adity\Desktop\WooPOS\start_campaign_worker.bat"

REM Start beat scheduler
start cmd /k "title Beat Scheduler && color 0D && C:\Users\adity\Desktop\WooPOS\start_beat.bat"

echo All workers started!
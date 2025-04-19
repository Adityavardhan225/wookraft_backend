import gevent.monkey
gevent.monkey.patch_all() # MUST BE THE FIRST IMPORT

print("✅ gevent monkey patching complete")
from routes.campaign.sending_campaign.services.campaign_tasks import celery_app

if __name__ == '__main__':
    celery_app.start()
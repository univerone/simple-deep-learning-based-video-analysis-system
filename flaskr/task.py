from celery import Celery

celery_app = Celery(
    'tasks',
    include=['flaskr.worker'],
    broker_url='pyamqp://',
    result_backend='rpc://',
    task_annotations={
        'tasks.add': {'rate_limit': '10/m'}
    }
)

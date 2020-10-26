from celery import Celery

celery_app = Celery(
    'tasks',
    include=['flaskr.worker'],
    broker='pyamqp://guest:guest@localhost:5672//',
    result_backend='rpc://',
    task_annotations={
        'tasks.add': {'rate_limit': '10/m'}
    }
)

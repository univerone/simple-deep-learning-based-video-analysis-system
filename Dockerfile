FROM python:3.8
WORKDIR /app
COPY . /app

# Install the dependencies
RUN pip install -r requirements.txt
RUN sudo apt install ffmpeg
RUN sudo bash rabbitmq-install.sh
RUN sudo rabbitmq-server
RUN celery -A flaskr.task.celery_app worker
RUN cd flaskr
RUN export FLASK_APP=flaskr 
RUN export FLASK_ENV=development
RUN flask init-db
RUN flask run

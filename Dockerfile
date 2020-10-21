FROM tiangolo/meinheld-gunicorn-flask:python3.8

COPY ./app /app
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt 
RUN apt-get update && apt-get install -y software-properties-common
RUN apt-get install -y ffmpeg
RUN export FLASK_APP=flaskr && export FLASK_ENV=development && flask init-db
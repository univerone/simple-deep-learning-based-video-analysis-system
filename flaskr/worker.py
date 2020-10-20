# refrence: https://deepspeech.readthedocs.io/en/v0.8.2/_downloads/67bac4343abf2261d69231fdaead59fb/client.py

import os
import shlex
import subprocess
import wave

import numpy as np
from celery import Task
from flaskr.task import celery_app
from deepspeech import Model
import sqlite3


def separete_audio(video_path):
    pure_audio = video_path.split('.')[0] + '_pure.wav'
    pure_video = video_path.split('.')[0] + '_pure.mp4'
    # if any of the file not exists
    if not (os.path.isfile(pure_audio) & os.path.isfile(pure_video)):
        # I tried a lot on this command to make it works on deepspeech
        ffmpeg_command = f'ffmpeg -i {video_path} -acodec pcm_s16le -b:a 192k -ac 1 -ar 16000 -vn -af silenceremove=1:0:-50dB -y {pure_audio} -codec copy -an -y {pure_video}'
        try:
            subprocess.run(shlex.split(ffmpeg_command), stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise RuntimeError('ffmpeg returned non-zero status: {}'.format(e.stderr))
        except OSError as e:
            raise OSError(e.errno, 'ffmpeg not found : {}'.format(e.strerror))
    return pure_video, pure_audio


class Worker(Task):
    _db = None
    _ds = None

    @property
    def db(self):
        if self._db is None:
            self._db = sqlite3.connect(
                'instance/flaskr.sqlite',
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            self._db.row_factory = sqlite3.Row
        return self._db

    @property
    def ds(self):
        if self._ds is None:
            self._ds = Model('models/deepspeech-0.8.2-models.tflite')
        return self._ds


# refer to https://docs.celeryproject.org/en/stable/userguide/tasks.html#custom-task-classes
@celery_app.task(base=Worker)
def process_video(taskid):
    video_path = process_video.db.execute(
        'SELECT filename'
        ' FROM TASK'
        ' WHERE id = ?',
        (taskid,)
    ).fetchone()['filename']
    video_file = f'flaskr/uploads/{taskid}-{video_path}'
    pure_video, pure_audio = separete_audio(f'flaskr/uploads/{taskid}-{video_path}')
    fin = wave.open(pure_audio, 'rb')
    audio = np.frombuffer(fin.readframes(fin.getnframes()), np.int16)
    fin.close()
    text = process_video.ds.stt(audio)
    # update the task status
    process_video.db.execute(
        'UPDATE TASK'
        ' SET status = ?,result = ?,finished = CURRENT_TIMESTAMP'
        ' WHERE id = ?',
        ('finished', text, taskid)
    )
    process_video.db.commit()
    # delete unnecessary video files
    os.remove(video_file)
    os.remove(pure_video)
    os.remove(pure_audio)

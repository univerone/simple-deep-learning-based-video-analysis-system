# refrence: https://deepspeech.readthedocs.io/en/v0.8.2/_downloads/67bac4343abf2261d69231fdaead59fb/client.py

import os
import shlex
import sqlite3
import subprocess
import wave

import cv2
import numpy as np
from celery import Task
from deepspeech import Model

from flaskr.conf import DEEPSPEECH_MODEL, DETECTOR_MODEL, DETECTOR_CONFIG
from flaskr.task import celery_app


def separete_file(video_path):
    """
    split the uploaded video into pure video and audio files
    :param video_path: the relative path of the video file
    :return: the split video and audio file path
    """
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


def combine_file(pure_video, video_file):
    """
    Combine Audio and Video file into one file
    :param video_file:
    :param pure_video:
    :return: the saved file path default is pure_video
    """
    file_path = pure_video.split('_')[0] + '_generated.mp4'
    if os.path.isfile(video_file) & os.path.isfile(pure_video):
        # change video code format to h264 to display it on html page
        ffmpeg_command = f'ffmpeg -i {pure_video} -i {video_file} -map 0:v -map 1:a -vcodec libx264 -acodec copy -y {file_path}'
        try:
            subprocess.run(shlex.split(ffmpeg_command), stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'ffmpeg returned non-zero status: {e.stderr}')
        except OSError as e:
            raise OSError(e.errno, f'ffmpeg not found : {e.strerror}')
    return file_path.split('/')[-1]


class Worker(Task):
    _db = None
    _deepspeech_model = None
    _detector = None

    @property
    def db(self):
        """
        :return: sqlite database
        """
        if self._db is None:
            self._db = sqlite3.connect(
                'instance/flaskr.sqlite',
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            self._db.row_factory = sqlite3.Row
        return self._db

    @property
    def deepspeech_model(self):
        """
        :return: deepspeech model
        """
        if self._deepspeech_model is None:
            self._deepspeech_model = Model(DEEPSPEECH_MODEL)
        return self._deepspeech_model

    @property
    def detector(self):
        """
        :return: face detection model
        """
        if self._detector is None:
            self._detector = cv2.dnn.readNetFromCaffe(DETECTOR_CONFIG, DETECTOR_MODEL)
        return self._detector


# refer to https://docs.celeryproject.org/en/stable/userguide/tasks.html#custom-task-classes
@celery_app.task(base=Worker)
def process_file(taskid):
    # filename of the target video file
    video_path = process_file.db.execute(
        'SELECT filename'
        ' FROM TASK'
        ' WHERE id = ?',
        (taskid,)
    ).fetchone()['filename']
    # file path of original video file
    video_file = f'flaskr/uploads/{taskid}-{video_path}'
    # generate the transcript part
    pure_video, pure_audio = separete_file(f'flaskr/uploads/{taskid}-{video_path}')
    fin = wave.open(pure_audio, 'rb')
    audio = np.frombuffer(fin.readframes(fin.getnframes()), np.int16)
    fin.close()
    text = process_file.deepspeech_model.stt(audio)
    # face detection part refer to
    # https://www.pyimagesearch.com/2018/02/26/face-detection-with-opencv-and-deep-learning/
    video_capture = cv2.VideoCapture(pure_video)
    # Define the codec and create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    h = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    w = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    fps = int(video_capture.get(cv2.CAP_PROP_FPS))
    tmp_video = f"{pure_video.split('.')[0]}_output.mp4"
    out = cv2.VideoWriter(tmp_video, fourcc, fps, (w, h))

    while video_capture.isOpened():
        # Read the Frame in img
        ret, img = video_capture.read()
        if img is None:
            break
        blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)), 1.0,
                                     (300, 300), (104.0, 177.0, 123.0))
        process_file.detector.setInput(blob)
        faces = process_file.detector.forward()
        # to draw faces on image
        for i in range(faces.shape[2]):
            confidence = faces[0, 0, i, 2]
            if confidence > 0.5:
                box = faces[0, 0, i, 3:7] * np.array([w, h, w, h])
                (x, y, x1, y1) = box.astype("int")
                cv2.rectangle(img, (x, y), (x1, y1), (0, 0, 255), 2)
        # Display the output
        out.write(img)
    video_capture.release()
    out.release()
    result_file = combine_file(tmp_video, video_file)
    # update the task status
    process_file.db.execute(
        'UPDATE TASK'
        ' SET status = ?,result = ?,video = ?,finished = CURRENT_TIMESTAMP'
        ' WHERE id = ?',
        ('finished', text, result_file, taskid)
    )
    process_file.db.commit()
    # delete unnecessary files
    os.remove(video_file)
    os.remove(pure_video)
    os.remove(pure_audio)
    os.remove(tmp_video)
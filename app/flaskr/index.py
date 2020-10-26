import os
from pathlib import Path

from flask import Blueprint, flash, request, redirect, render_template, send_from_directory
from werkzeug.utils import secure_filename
from flaskr.worker import process_file

from flaskr.db import get_db
from flaskr.conf import ALLOWED_EXTENSIONS, MAX_VIDEO_LENGTH, UPLOAD_FOLDER

bp = Blueprint('index', __name__)


def allowed_file(filename):
    """
    supported file type: *.mp4, *.flv, *.mkv
    :param filename: the name of file to be uploaded
    :return: If the file are allowed
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_size(filesize):
    """
    supported file size: below 50MB
    :param filesize: the file size (type of str) of video to be uploaded
    :return: if this video size exceeds the limit
    """
    return int(filesize) <= MAX_VIDEO_LENGTH


@bp.route("/", methods=["GET", "POST"])
def index():
    """
    refer to : https://flask.palletsprojects.com/en/1.1.x/patterns/fileuploads/
    the basic logic to upload a video file and error handling
    :return:
    """
    if request.method == 'POST':
        if 'videoFile' not in request.files:
            flash('No videoFile part', 'warning')
            return redirect(request.url)
        if "filesize" in request.cookies:
            if not allowed_size(request.cookies["filesize"]):
                flash('Please make sure the video size <= 50MB', 'warning')
                return redirect(request.url)

        file = request.files['videoFile']
        if file.filename == '':
            flash('Please select a video', 'warning')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            db = get_db()
            cursor = db.execute(
                'INSERT INTO TASK (filename, status) VALUES (?, ?)',
                (filename, 'pending')
            )
            db.commit()  # insert the task into database
            taskid = cursor.lastrowid  # get an ID for this task
            Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)  # create if save folder not exists
            file.save(os.path.join(UPLOAD_FOLDER, f'{taskid}-{filename}'))  # save video file
            flash(f'Upload succeed! You can view task status at <a href="/task/{taskid}" class="alert-link">here</a>',
                  'success')
            # send the task to task queue
            process_file.delay(taskid)
            return redirect(request.url)
        else:
            flash('The video type is not supported now', 'warning')
            return redirect(request.url)
    return render_template('index.html')


@bp.route("/about")
def about():
    return render_template('about.html')


@bp.route("/task/<taskid>")
def task_status(taskid):
    task = get_db().execute(
        'SELECT *'
        ' FROM TASK'
        ' WHERE id = ?',
        (taskid,)
    ).fetchone()
    return render_template("task.html", task=task)


@bp.route('/uploads/<filename>')
def upload(filename):
    return send_from_directory('uploads', filename)

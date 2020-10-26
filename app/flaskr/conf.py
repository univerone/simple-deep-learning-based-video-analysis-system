# restrictions on the file user can upload
UPLOAD_FOLDER = 'flaskr/uploads'
ALLOWED_EXTENSIONS = {'mp4', 'mkv', 'flv'}
MAX_VIDEO_LENGTH = 50 * 1024 * 1024  # max video size to be uploaded

DEEPSPEECH_MODEL = 'models/deepspeech-0.8.2-models.tflite'
CLADDIFIER_MODEL = "models/haarcascade_frontalface_default.xml"

DETECTOR_MODEL = "models/res10_300x300_ssd_iter_140000_fp16.caffemodel"
DETECTOR_CONFIG = "models/deploy.prototxt"
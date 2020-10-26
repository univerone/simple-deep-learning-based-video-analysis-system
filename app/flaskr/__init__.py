import os
from flask import Flask


def create_app():
    """ Application factory
    Returns:
        The Flask application object
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY= os.urandom(16),
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # index page
    from . import index
    app.register_blueprint(index.bp)

    from . import db
    db.init_app(app)
    return app

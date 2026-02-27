from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager, csrf


def create_app(config_class=Config):
    flask_app = Flask(__name__)
    flask_app.config.from_object(config_class)

    # --- init extensions ---
    db.init_app(flask_app)
    migrate.init_app(flask_app, db)
    login_manager.init_app(flask_app)
    csrf.init_app(flask_app)

    # --- register routes ---
    from app.routes import register_routes

    register_routes(flask_app)

    # --- create tables on first run ---
    with flask_app.app_context():
        from app import models  # noqa: F401 – ensure models are registered

        db.create_all()

    return flask_app

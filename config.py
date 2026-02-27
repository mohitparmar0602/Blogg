import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "dev-secret-key-change-in-production",
    )

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'blog.db')}",
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    RECAPTCHA_SITE_KEY = os.environ.get(
        "RECAPTCHA_SITE_KEY",
        "6LdsyHQsAAAAAFZzuQtDKdHGD3UDSUi6-eR1s128",
    )

    RECAPTCHA_SECRET_KEY = os.environ.get(
        "RECAPTCHA_SECRET_KEY",
        "6LdsyHQsAAAAAGcDYIZRIBCNx92s7lwaLMSJFi_0",
    )

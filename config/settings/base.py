from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

environ.Env.read_env(BASE_DIR / ".env")

from .apps import INSTALLED_APPS
from .database import DATABASES
from .internationalization import LANGUAGE_CODE, TIME_ZONE, USE_I18N, USE_TZ
from .middleware import MIDDLEWARE
from .rest_framework import REST_FRAMEWORK, SPECTACULAR_SETTINGS
from .security import ALLOWED_HOSTS, AUTH_PASSWORD_VALIDATORS, DEBUG, SECRET_KEY
from .static import DEFAULT_AUTO_FIELD, STATIC_URL
from .templates import TEMPLATES

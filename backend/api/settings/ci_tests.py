""" Production Settings """
import logging
import sys
from .stage import *

DEBUG = True
CORS_ALLOW_ALL_ORIGINS = True
EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True

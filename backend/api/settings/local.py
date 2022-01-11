""" Local development Settings """
from .base import *

ALLOWED_HOSTS = ["*"]
EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

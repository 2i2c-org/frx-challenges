"""
Django settings for frx_challenges project.

Generated by 'django-admin startproject' using Django 5.0.7.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import os
from pathlib import Path

import django_yamlconf

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-su6*zos$30s$6@7q6lm-)rf1@bxdq!qd566f!a^9wgqs*p)m3%"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    "web.apps.WebConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_yamlconf",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.github",
    "reversion",
    "django_jsonform",
    "crispy_forms",
    "crispy_bootstrap5",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "frx_challenges.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "web.context_processors.navbar_pages",
                "web.context_processors.site_display_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "frx_challenges.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_ROOT = "web/static/"
STATIC_URL = "static/"

MEDIA_ROOT = "media/"
MEDIA_URL = "media/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by email
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        }
    },
    "loggers": {
        # This will process records from all loggers
        "": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "django.db.backends": {
            "level": "INFO",
            "handlers": ["console"],
            "filters": ["require_debug_true"],
        },
    },
}

# Provider specific settings
SOCIALACCOUNT_PROVIDERS = {
    "github": {
        # For each OAuth based provider, either add a ``SocialApp``
        # (``socialaccount`` app) containing the required client
        # credentials, or list them here:
        "APP": {
            "client_id": "Ov23liodL5AiNt5kfB8d",
            "secret": "bfab0d49f138df0d017d2bcc0f9bbb1b199b7e62",
        },
        "VERIFIED_EMAIL": True,
    }
}

ACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_ONLY = True

# Only use GitHub for login
LOGIN_URL = "/accounts/github/login/"
# Match JupyterHub behavior
# FIXME: Understand the security implications?
SOCIALACCOUNT_LOGIN_ON_GET = True

# Challenge state can have the following values:
# - NOT_STARTED: The challenge has not started yet
# - RUNNING: The challenge is currently running
# Based on this, different views are shown to the user
CHALLENGE_STATE = "RUNNING"


import os

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads/"))

SUBMISSIONS_UPLOADS_DIR = out_dir

output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "outputs/"))
SUBMISSIONS_RESULTS_DIR = output_dir

EVALUATOR_DOCKER_IMAGE = "quay.io/yuvipanda/evaluator-harness:latest"
EVALUATOR_DOCKER_CMD = []

# Set to true to disable network access from inside the container started by evaluator
EVALUATOR_DOCKER_DISABLE_NETWORK = True
EVALUATOR_DOCKER_EXTRA_BINDS = []
EVALUATOR_DOCKER_AUTH = {}
MAX_RUNNING_EVALUATIONS = 3
# If you want to use a GCP Artifact Registry service key, use the following config:
# for EVALUATOR_DOCKER_AUTH
# {
#     "username": "_json_key",
#     "password": open("serviceaccount.json").read(), # or path to your service account file
#     "serveraddress": "us-west2-docker.pkg.dev" # or the host used by your artifact registry
# }

# Max number of CPUs allowed for the evaluator
EVALUATOR_DOCKER_CONTAINER_CPU_LIMIT = 2
# Max memory (in bytes) allowed for the evaluator container
EVALUATOR_DOCKER_CONTAINER_MEMORY_LIMIT = 2 * 1024 * 1024 * 1024

## Site specific display settings
SITE_NAME = ""
SITE_LOGO_URL = ""
SITE_FOOTER_HTML = """
<div class="footer">
    <p>Change this to your custom footer</p>
</div>
"""
SITE_PAGE_HEADER_IMAGE_URL = ""
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
SITE_SUBMISSION_INSTRUCTIONS_MARKDOWN = "Some Text Heree"
SITE_SUBMISSION_FORM_SCHEMA = {
    "type": "object",
    "properties": {
        "repo": {
            "type": "string",
            "title": "Repository",
            "helpText": "Link to repository containing code and stuff",
        }
    },
}

EVALUATION_DISPLAY_CONFIG = [
    {"result_key": "chars", "display_name": "Characters"},
    {"result_key": "lines", "display_name": "Lines"},
]

django_yamlconf.load()
django_yamlconf.list_attrs()

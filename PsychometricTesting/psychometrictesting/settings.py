# project/settings.py

from pathlib import Path
from datetime import timedelta
from decouple import config
import os
import stripe



# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DOMAIN = config("DOMAIN", default="https://api.investmentlab.org")


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-your-secret-key'  # Replace with your actual secret key

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    # "localhost",
    # "127.0.0.1",
    "api.investmentlab.org",
    "app.investmentlab.org",
    "localhost",
    "127.0.0.1",
    "::1",
]

# 1️⃣  Stop allowing every origin — keep this False in prod
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

# # 2️⃣  Explicit allow-list for dev front-ends
# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:5173",           # Vite
#     # "http://127.0.0.1:5173",         # add if you sometimes use 127.0.0.1
#     "https://e8872727810a.ngrok-free.app",
# ]

CORS_ALLOWED_ORIGINS = [
    "https://app.investmentlab.org",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


# 4️⃣  Django ≥ 4.0 + session/cookie auth?  Add the same host here
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "https://*.trycloudflare.com",
    "https://api.investmentlab.org",
    "https://app.investmentlab.org",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Application definition

INSTALLED_APPS = [

    # Default Django apps...
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    # Third-party apps...
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'anymail',
    'drf_spectacular',

    # Your apps...
    'authentication',
    'rating',
    'testing',
    'payment',
    'blog',
    'reportgeneration',
    'percentile',
]

MIDDLEWARE = [
    # Third-party middleware...
    "corsheaders.middleware.CorsMiddleware",
    # Default middleware...
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',

    # Third-party middleware...

    # Default middleware continued...
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Custom middleware...
    'authentication.middleware.PendingRegistrationCleanupMiddleware',
]

ROOT_URLCONF = 'psychometrictesting.urls'

# REST framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),  # Adjust as needed
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),    # Adjust as needed
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Set custom user model
AUTH_USER_MODEL = 'authentication.User'

# Session engine
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True



# Mailgun Configuration
EMAIL_BACKEND = 'anymail.backends.mailgun.EmailBackend'

GEOIP_PATH = BASE_DIR / 'geoip'

# Anymail Configuration
ANYMAIL = {
    'MAILGUN_API_KEY': 'b4574f43ef437b310850f323e4a7570c-f6fe91d3-4e4d93ed',
    'MAILGUN_SENDER_DOMAIN': 'www.big5test.org',  # e.g., 'mg.yourdomain.com'
}
DEFAULT_FROM_EMAIL = 'Big5Test <akil.s@big5test.org>'

STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = config('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET')

stripe.api_key = STRIPE_SECRET_KEY


SPECTACULAR_SETTINGS = {
    'TITLE': 'Psychometric Testing API',
    'DESCRIPTION': 'This API allows taking psychometric tests as logged in users as well as anonymous users',
    'VERSION': '1.0.0',
    # Other settings...
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Default context processors...
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'psychometrictesting.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Use 'django.db.backends.postgresql' for PostgreSQL
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Dubai'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


LOGGING = {
    # Your logging configuration...
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'loggers': {
        '': {  # Root logger
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
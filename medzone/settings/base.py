from pathlib import Path
from decouple import config, Csv
import os


# Add this near the top, after imports
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',        # ← important
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'bootstrap5',
    'crispy_forms',
    'django_cleanup.apps.CleanupConfig',
    'fontawesomefree',
    'django_cron',

    'utilisateur',
    'lecon',
    'lessoncopy',
    'quizzes',
    'dashboard',
    'student',
    'subscriptions',
    # 'teacher',
    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # ← after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'subscriptions.middleware.SubscriptionMiddleware', 

]

ROOT_URLCONF = 'medzone.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'medzone.wsgi.application'
ASGI_APPLICATION = 'medzone.asgi.application'


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Indian/Antananarivo'        # ← correct for Madagascar
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

if not os.path.exists(MEDIA_ROOT):
    os.makedirs(MEDIA_ROOT, exist_ok=True)
    print(f"Created media directory: {MEDIA_ROOT}")


# Check permissions
import stat
if os.path.exists(MEDIA_ROOT):
    mode = os.stat(MEDIA_ROOT).st_mode
    if not mode & stat.S_IWUSR:
        print(f"WARNING: Media directory not writable: {MEDIA_ROOT}")


AUTH_USER_MODEL = 'utilisateur.User'
LOGIN_URL = 'utilisateur:login'
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'utilisateur:login'

DEFAULT_FROM_EMAIL = 'MedZone <noreply@yourdomain.mg>'

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"


# Channels – default to InMemory for dev, Redis in prod
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# ——————————————————————
# MVOLA PAYMENT SETTINGS – ALWAYS IN base.py
# ——————————————————————


FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Use Django's built-in handlers in the correct order
FILE_UPLOAD_HANDLERS = [
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',  # For large files
    'django.core.files.uploadhandler.MemoryFileUploadHandler',     # For small files
]

# Increase memory buffer size
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB - files larger go to disk
DATA_UPLOAD_MAX_MEMORY_SIZE = 350 * 1024 * 1024  # 350MB total request size

# Increase max fields
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# Temp directory
import tempfile
FILE_UPLOAD_TEMP_DIR = tempfile.gettempdir()
print(f"Using temp directory: {FILE_UPLOAD_TEMP_DIR}")

# Check temp directory
if not os.path.exists(FILE_UPLOAD_TEMP_DIR):
    os.makedirs(FILE_UPLOAD_TEMP_DIR, exist_ok=True)

# Add caching for better performance
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379',
    }
}

# Add custom file upload handlers
FILE_UPLOAD_HANDLERS = [
    'splitter_app.handlers.LargeFileUploadHandler',  # Our custom handler first
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
]

# Cron job settings
CRON_CLASSES = [
    "students_subscriptions.cron.CheckExpiredSubscriptions",
    "students_subscriptions.cron.CleanupPendingPayments",
    "students_subscriptions.cron.SendPaymentReminders",
    "students_subscriptions.cron.SendRenewalReminders",
    "students_subscriptions.cron.UpdateSubscriptionUsage",
    "students_subscriptions.cron.GenerateSubscriptionReports",
]


# Base directory for bulk imports
BULK_IMPORT_ROOT = 'C:/Users/ZICO/Desktop/medzone-documents'   # Change to your actual path

# Subfolder names (must match exactly)
BULK_SPLITTED_DIR = 'splitted'
BULK_SHIFTED_DIR = 'shifted down'
BULK_EXERCICES_DIR = 'exercices'

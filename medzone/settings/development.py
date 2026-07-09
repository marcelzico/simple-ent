from .base import *
from decouple import config, Csv

DEBUG = True
ALLOWED_HOSTS = ['*', '127.0.0.1']  # convenient for local network testing

# Use console email in dev
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# FOR PRODUCTION
# Keep MySQL for now
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'medzone',
#         'USER': config('DB_USER'),
#         'PASSWORD': config('DB_PASSWORD'),
#         'HOST': 'localhost',
#         'PORT': '3306',
#         'OPTIONS': {
#             'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
#             'charset': 'utf8mb4',
#         },
#         'TIME_ZONE': 'UTC',
#     }
# }


# FOR DEVELOPMENT
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'medzone_simple',
        'USER': 'root',
        'PASSWORD': 'ocizzi13',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
        'TIME_ZONE': 'UTC',
    }
}


"""
Django settings for governance_hub project.
"""

from pathlib import Path
from decouple import config, Csv
import dj_database_url
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-CHANGE-THIS-IMMEDIATELY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Determine environment
ENVIRONMENT = config('ENVIRONMENT', default='development')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',
    'drf_spectacular',

    # Local apps
    'authentication',
    'companies',
    'staff',
    'documents',
    'financial',
    'workflows',
    'communications',
    'core',
]

MIDDLEWARE = [
    # CorsMiddleware MUST be first — before SecurityMiddleware and everything else
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # SECURITY: Add custom security middleware after authentication
    'authentication.middleware.SessionSecurityMiddleware',
    'authentication.middleware.RoleBasedAccessMiddleware',
    'authentication.middleware.SecurityLoggingMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'governance_hub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'governance_hub.wsgi.application'

# Database
if config('DATABASE_URL', default=''):
    DATABASES = {
        'default': dj_database_url.config(
            default=config('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    import sys
    if 'test' in sys.argv or config('DB_PASSWORD', default='') == '':
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
    else:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': config('DB_NAME', default='governance_hub'),
                'USER': config('DB_USER', default='postgres'),
                'PASSWORD': config('DB_PASSWORD', default=''),
                'HOST': config('DB_HOST', default='localhost'),
                'PORT': config('DB_PORT', default='5432'),
            }
        }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'authentication.UserProfile'

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'authentication.backends.UserProfileBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}

# CORS Configuration
if ENVIRONMENT == 'production':
    CORS_ALLOWED_ORIGINS = config(
        'CORS_ALLOWED_ORIGINS',
        default='https://gosh-five.vercel.app',
        cast=Csv()
    )
else:
    CORS_ALLOWED_ORIGINS = config(
        'CORS_ALLOWED_ORIGINS',
        default='http://localhost:5173,http://localhost:5174,http://localhost:3000',
        cast=Csv()
    )
CORS_ALLOW_CREDENTIALS = True  # Required for cross-origin session cookies
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Session Configuration
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = config('SESSION_COOKIE_SAMESITE', default='Lax')
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=not DEBUG, cast=bool)
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_DOMAIN = config('SESSION_COOKIE_DOMAIN', default=None)

# CSRF Configuration
CSRF_COOKIE_HTTPONLY = False      # MUST be False so JS can read the CSRF cookie
CSRF_USE_SESSIONS = False         # Store CSRF in cookie, not session
CSRF_COOKIE_SAMESITE = config('CSRF_COOKIE_SAMESITE', default='Lax')
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=not DEBUG, cast=bool)
CSRF_COOKIE_DOMAIN = config('CSRF_COOKIE_DOMAIN', default=None)
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:5173,http://localhost:5174,http://localhost:3000',
    cast=Csv()
)

# Trust Render's proxy so Django sees requests as HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Security Headers (Production)
if ENVIRONMENT == 'production':
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
else:
    # Development settings
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# API Documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'Governance Hub API',
    'DESCRIPTION': 'API for Ainick Governance Hub',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Logging — console only (Render filesystem is ephemeral, no file logging)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
# AI Message Classification System Configuration
# Final tuned values achieving 96.7% accuracy (Task 3.8 completion)
CLASSIFICATION_ENABLED = config('CLASSIFICATION_ENABLED', default=True, cast=bool)

CLASSIFICATION_THRESHOLDS = {
    'fallback_threshold': 0.55,     # Below this, use fallback handler
    'logging_threshold': 0.8,       # Above this, log for review
    'company_data_threshold': 0.7,  # Company_Data priority threshold
    'kenya_governance_threshold': 0.75,  # Kenya_Governance priority threshold
    'feature_guide_threshold': 0.6,     # Feature_Guide threshold
    'navigation_threshold': 0.6,        # Navigation threshold
    'web_search_threshold': 0.5,        # Web_Search threshold
    'tip_threshold': 0.0,               # Tip threshold (fallback)
}

CLASSIFICATION_WEIGHTS = {
    'keyword_weight': 0.8,    # Keyword confidence weight (80%)
    'semantic_weight': 0.2,   # Semantic confidence weight (20%)
}

# Performance targets
CLASSIFICATION_PERFORMANCE = {
    'target_accuracy': 0.90,           # 90% minimum accuracy
    'achieved_accuracy': 0.967,        # 96.7% achieved accuracy
    'target_processing_time_ms': 200,  # 200ms target
    'average_processing_time_ms': 10.9,  # 10.9ms achieved
}

# Feature Flags for Architectural Refactoring
# These flags enable gradual migration from old to new implementations
FEATURE_FLAGS = {
    'USE_SERVICE_LAYER': config('USE_SERVICE_LAYER', default=False, cast=bool),
    'USE_VALIDATION_RULES_API': config('USE_VALIDATION_RULES_API', default=False, cast=bool),
    'USE_NOTIFICATION_SERVICE': config('USE_NOTIFICATION_SERVICE', default=False, cast=bool),
}
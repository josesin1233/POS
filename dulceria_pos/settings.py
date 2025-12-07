from pathlib import Path 
import os
import dj_database_url

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, use os.environ directly
    pass

BASE_DIR = Path(__file__).resolve().parent.parent 

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes', 'on')

# Allowed hosts - specify your domain names
if DEBUG:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']
else:
    # Production - allow all Railway domains
    ALLOWED_HOSTS = ['*'] 

# 🗄️ Database configuration
# Auto-adaptive Railway PostgreSQL connection
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL and 'railway' in DATABASE_URL:
    # Railway PostgreSQL detected - use with SSL and error handling
    try:
        db_config = dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=True
        )
        # Add PostgreSQL specific options for Railway
        db_config['OPTIONS'] = {
            'sslmode': 'require',
            'connect_timeout': 30,
            'application_name': 'dulceria_pos'
        }
        DATABASES = {'default': db_config}
    except Exception as e:
        print(f"⚠️ DATABASE_URL parsing failed: {e}")
        # Fallback to manual parsing
        import re
        match = re.match(r'postgresql://(.+):(.+)@(.+):(\d+)/(.+)', DATABASE_URL)
        if match:
            user, password, host, port, name = match.groups()
            DATABASES = {
                'default': {
                    'ENGINE': 'django.db.backends.postgresql',
                    'NAME': name,
                    'USER': user,
                    'PASSWORD': password,
                    'HOST': host,
                    'PORT': port,
                    'OPTIONS': {
                        'sslmode': 'require',
                        'connect_timeout': 30,
                        'application_name': 'dulceria_pos',
                    },
                }
            }
        else:
            raise Exception("Could not parse DATABASE_URL")
            
elif not DEBUG:
    # Production without DATABASE_URL - use environment variables
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DATABASE', 'railway'),
            'USER': os.getenv('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
            'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
            'OPTIONS': {
                'sslmode': 'prefer',
                'connect_timeout': 30,
                'application_name': 'dulceria_pos',
            },
        }
    }
else:
    # Local development - usar SQLite para desarrollo local
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Apps locales
    'accounts',
    'pos',
    
    # Apps de terceros
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'pos.middleware.AdminIPRestrictionMiddleware',
    'pos.middleware.AdminSecurityHeadersMiddleware',
] 

ROOT_URLCONF = 'dulceria_pos.urls' 

TEMPLATES = [ 
    { 
        'BACKEND': 'django.template.backends.django.DjangoTemplates', 
        'DIRS': [
            BASE_DIR / 'templates',
            BASE_DIR / 'pos' / 'templates',
            BASE_DIR / 'accounts' / 'templates',
        ],
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

# Database configuration is above 

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

# Static files - Force serving from source directory
STATIC_URL = '/static/'

# In production, use STATICFILES_DIRS to serve directly from source
if not DEBUG:
    # Serve directly from static source directory - bypass staticfiles completely
    STATICFILES_DIRS = [
        "/app/static",  # Railway path
        BASE_DIR / "static",  # Fallback
    ]
    STATIC_ROOT = None  # Disable collectstatic requirement
else:
    STATICFILES_DIRS = [
        BASE_DIR / "static",
    ]
    STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField' 
AUTH_USER_MODEL = 'accounts.User'

APPEND_SLASH = True
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/punto_de_venta/'
LOGOUT_REDIRECT_URL = '/admin/'

# Session configuration
SESSION_COOKIE_AGE = 86400  # 24 horas
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# CORS settings
cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000')
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(',')]
CORS_ALLOW_CREDENTIALS = True

# Security settings
SECURE_BROWSER_XSS_FILTER = os.getenv('SECURE_BROWSER_XSS_FILTER', 'True').lower() in ('true', '1', 'yes', 'on')
SECURE_CONTENT_TYPE_NOSNIFF = os.getenv('SECURE_CONTENT_TYPE_NOSNIFF', 'True').lower() in ('true', '1', 'yes', 'on')
X_FRAME_OPTIONS = os.getenv('X_FRAME_OPTIONS', 'DENY')

# Session security
SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'True').lower() in ('true', '1', 'yes', 'on')
CSRF_COOKIE_HTTPONLY = os.getenv('CSRF_COOKIE_HTTPONLY', 'True').lower() in ('true', '1', 'yes', 'on')

# Only enable secure cookies in production (HTTPS)
if not DEBUG:
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() in ('true', '1', 'yes', 'on')
    CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True').lower() in ('true', '1', 'yes', 'on')
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() in ('true', '1', 'yes', 'on')
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # For Railway
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django_errors.log'),
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'pos': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# WhiteNoise configuration - Force use finders in production
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
    WHITENOISE_USE_FINDERS = True  # Force use finders to serve from STATICFILES_DIRS
    WHITENOISE_AUTOREFRESH = True  # Force refresh in production
    WHITENOISE_SKIP_COMPRESS_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'zip', 'gz', 'tgz', 'bz2', 'tbz', 'xz']
    WHITENOISE_ROOT = "/app/static"  # Override root directory
else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
    WHITENOISE_USE_FINDERS = True
    WHITENOISE_AUTOREFRESH = DEBUG

# Cache configuration (use Redis in production if available)
if os.getenv('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.getenv('REDIS_URL'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# Admin security
ADMIN_URL = os.getenv('ADMIN_URL', 'admin/')  # Allow custom admin URL

# Rate limiting configuration (if django-ratelimit is installed)
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Email configuration for error reporting
if not DEBUG:
    ADMINS = [
        ('Admin', os.getenv('ADMIN_EMAIL', 'admin@example.com')),
    ]
    MANAGERS = ADMINS
    SERVER_EMAIL = os.getenv('SERVER_EMAIL', 'server@example.com')
    EMAIL_SUBJECT_PREFIX = '[POS Mexico] '

WSGI_APPLICATION = 'dulceria_pos.wsgi.application'

# ====================================
# STRIPE CONFIGURATION
# ====================================

# Stripe API Keys (configure in environment variables)
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')

# Stripe Webhook Secret (for production)
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

# Stripe Settings
STRIPE_CURRENCY = 'mxn'  # Mexican Pesos
STRIPE_API_VERSION = '2025-11-17.clover'  # Latest API version

# ====================================
# ADMIN SECURITY CONFIGURATION
# ====================================

# IPs permitidas para acceder al Django Admin
# En desarrollo, todas las IPs están permitidas
# En producción, solo estas IPs pueden acceder al admin
ADMIN_ALLOWED_IPS = [
    '127.0.0.1',
    'localhost',
    '::1',  # IPv6 localhost
    # IPs autorizadas para administradores
    '187.190.184.26',  # IP autorizada del administrador
    '187.190.192.210',  # IP autorizada
    '189.136.123.181',  # IP autorizada
    '189.157.32.83',   # IP autorizada
]

# URL personalizada del admin (para mayor seguridad)
ADMIN_URL_PATH = os.getenv('ADMIN_URL_PATH', 'admin/')

# Rate limiting para admin (intentos de login)
ADMIN_LOGIN_ATTEMPTS = int(os.getenv('ADMIN_LOGIN_ATTEMPTS', '5'))
ADMIN_LOGIN_TIMEOUT = int(os.getenv('ADMIN_LOGIN_TIMEOUT', '300'))  # 5 minutos

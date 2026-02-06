from pathlib import Path
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-!40k#t=cg=hmcku(zkk)d%v*ax@8ou*8^63+-w*)nn9neo)09*'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['coingry.shop', 'localhost', '127.0.0.1']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'CoinGryComm',
    # Django REST Framework
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',
    # Celery
    'django_celery_beat',
    'django_celery_results',
    # SEO Analyzer
    'seo_analyzer',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS must be before CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'telegram_bot.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # 프로젝트 전역 템플릿 디렉토리 (Django admin 템플릿 오버라이드용)
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
            os.path.join(BASE_DIR, 'frontend/build'),
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

WSGI_APPLICATION = 'telegram_bot.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {
  'default': {
      'ENGINE': 'django.db.backends.mysql',
        'NAME': 'coingry',
        'USER': 'root',
        'PASSWORD': 'root',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'use_unicode': True,
        },
     }
}


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = 'ko-kr'

TIME_ZONE = 'Asia/Seoul'

USE_I18N = True

USE_TZ = True

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'frontend/build'),
]

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# SEO Analyzer Configuration
# =============================================================================

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React development server
    "http://coingry.shop:3000",  # React on server
    "https://coingry.shop",   # Production domain
]
CORS_ALLOW_CREDENTIALS = True

# Django REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # 개발/테스트 단계: 인증 없이 모든 작업 허용
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Celery Beat Schedule (자동 분석 및 학습)
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    # =========================================================================
    # GSC 동기화 (하루 2회 - API 쿼터 절약)
    # GSC 데이터는 2-3일 지연되므로 자주 호출할 필요 없음
    # =========================================================================
    'gsc-sync-morning': {
        'task': 'seo_analyzer.tasks.gsc_sync_all_domains',
        'schedule': crontab(hour=8, minute=0),  # 08:00 아침
    },
    'gsc-sync-evening': {
        'task': 'seo_analyzer.tasks.gsc_sync_all_domains',
        'schedule': crontab(hour=20, minute=0),  # 20:00 저녁
    },

    # =========================================================================
    # Full Scan (매일 - SEO 트렌드 추적을 위해 일일 실행)
    # =========================================================================
    'daily-full-scan': {
        'task': 'seo_analyzer.tasks.nightly_cache_update',
        'schedule': crontab(hour=4, minute=0),  # 매일 04:00
    },

    # =========================================================================
    # AI 분석 및 학습
    # =========================================================================
    # 매일 새벽 2시: 전체 도메인 AI 분석
    'daily-ai-analysis': {
        'task': 'seo_analyzer.tasks.schedule_all_domain_analysis',
        'schedule': crontab(hour=2, minute=0),
    },
    # 12시간마다: 벡터 임베딩 증분 업데이트 (6시간 → 12시간으로 변경)
    'vector-embedding-update': {
        'task': 'seo_analyzer.tasks.update_vector_embeddings',
        'schedule': crontab(minute=0, hour='*/12'),
    },
    # 매일 새벽 3시: 수정 효과성 평가
    'evaluate-fix-effectiveness': {
        'task': 'seo_analyzer.tasks.evaluate_fix_effectiveness',
        'schedule': crontab(hour=3, minute=0),
    },
    # 매일 새벽 5시: 일일 스냅샷 생성
    'daily-snapshot': {
        'task': 'seo_analyzer.tasks.generate_daily_snapshot',
        'schedule': crontab(hour=5, minute=0),
    },

    # =========================================================================
    # AI 제안 추적 시스템
    # =========================================================================
    # 매일 08:30: 추적중인 제안 일일 스냅샷 캡처 (GSC 동기화 후)
    'tracking-daily-snapshot': {
        'task': 'seo_analyzer.tasks.capture_tracking_snapshots',
        'schedule': crontab(hour=8, minute=30),
    },
    # 매주 월요일 09:00: 주간 효과 분석
    'tracking-weekly-analysis': {
        'task': 'seo_analyzer.tasks.analyze_tracking_effectiveness',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),
    },
    # 매주 일요일 00:00: 오래된 추적 자동 완료 (90일 초과)
    'tracking-auto-complete': {
        'task': 'seo_analyzer.tasks.auto_complete_old_tracking',
        'schedule': crontab(hour=0, minute=0, day_of_week=0),
    },
}

# Google API Settings
GOOGLE_SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'config', 'google_service_account.json')
GOOGLE_API_KEY = 'AIzaSyDNKdFURUYeUJ_Z3VXEkYowTWnnxpaPRaU'  # PageSpeed Insights API Key
GOOGLE_API_SCOPES = [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/webmasters',  # Full access for sitemap submission
    'https://www.googleapis.com/auth/analytics.readonly',
    'https://www.googleapis.com/auth/indexing',  # URL indexing requests
]

# SEO Analyzer Specific Settings
SEO_CACHE_TTL = 86400  # 24 hours in seconds
SEO_MAX_PAGES_PER_DOMAIN = 1000
SEO_SUBDOMAIN_DISCOVERY_METHODS = ['dns', 'sitemap', 'search_console']

# Claude AI Settings (Anthropic API)
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
CLAUDE_MODEL = 'claude-sonnet-4-20250514'  # Default model
CLAUDE_MAX_TOKENS = 4096
CLAUDE_RATE_LIMIT_PER_MINUTE = 50
CLAUDE_CACHE_TTL = 86400  # 24 hours in seconds

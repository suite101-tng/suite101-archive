from __future__ import absolute_import
import os
import sys
import dj_database_url
import django_cache_url
from celery.schedules import crontab
from datetime import timedelta

def env_var(key, default=None):
    """Retrieves env vars and makes Python boolean replacements"""
    val = os.environ.get(key, default)
    if val == 'True':
        val = True
    elif val == 'False':
        val = False
    return val

SITE_URL = env_var('SITE_URL', 'http://localhost:8000')
DEBUG = env_var('DEBUG', False)

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
    ('Michael', 'michael@suite.io'),
)
MANAGERS = ADMINS

DATABASES = {
    'default': dj_database_url.parse(env_var('DATABASE_URL', 'postgres://localhost')),
    'slave': dj_database_url.parse(env_var('DB_SLAVE1_URL', 'postgres://localhost')),
}

if not DEBUG:
    DATABASE_ROUTERS = ['project.dbrouter.AuthRouter', 'project.dbrouter.MasterSlaveRouter']

hosts = env_var('ALLOWED_HOSTS', 'localhost')
ALLOWED_HOSTS = [x for x in hosts.split(',')]
ALLOWED_HOSTS = ['*']

# debug toolbar
INTERNAL_IPS = ('127.0.1.1', '10.0.2.2')

settings_dir = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.dirname(settings_dir))
sys.path.append(os.path.join(PROJECT_ROOT, 'apps/'))


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Vancouver'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'
LANGUAGES = (
    ('en', 'EN'),
)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

# The baseUrl to pass to the r.js optimizer.
REQUIRE_BASE_URL = "js"

# The name of a build profile to use for your project, relative to REQUIRE_BASE_URL.
# A sensible value would be 'app.build.js'. Leave blank to use the built-in default build profile.
REQUIRE_BUILD_PROFILE = os.path.join(PROJECT_ROOT, 'build.js')

# The name of the require.js script used by your project, relative to REQUIRE_BASE_URL.
REQUIRE_JS = "require.js"

# A dictionary of standalone modules to build with almond.js.
# See the section on Standalone Modules, below.
REQUIRE_STANDALONE_MODULES = {}

# Whether to run django-require in debug mode.
REQUIRE_DEBUG = DEBUG

# A tuple of files to exclude from the compilation result of r.js.
REQUIRE_EXCLUDE = ("build.txt",)

# The execution environment in which to run r.js: auto, node or rhino.
# auto will autodetect the environment and make use of node if available and rhino if not.
# It can also be a path to a custom class that subclasses require.environments.Environment and defines some "args" function that returns a list with the command arguments to execute.
REQUIRE_ENVIRONMENT = "auto"

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = env_var('MEDIA_ROOT')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = env_var('STATIC_ROOT', os.path.join(PROJECT_ROOT, 'collectedstaticfiles/'))

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = env_var('STATIC_URL', '/static/')

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    (os.path.join(PROJECT_ROOT, 'static/')),
)

S3_URL = env_var('S3_URL', STATIC_URL)
# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = env_var('SECRET_KEY', 'idv!)94jbng)af)r79(dkgtzjjf)@r#j6(c!8&amp;nlvj0-dz9p*1')

# TEMPLATE_LOADERS = (
#     (   'django.template.loaders.filesystem.Loader',
#         'django.template.loaders.app_directories.Loader',
#     )),

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
            # Always use forward slashes, even on Windows.
            # Don't forget to use absolute paths, not relative paths.
            os.path.join(PROJECT_ROOT, 'templates/'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG,
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.template.context_processors.request',
                'django.template.context_processors.debug',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.static',
                'project.context_processors.settings',
                'project.context_processors.accepted_terms',
                'project.context_processors.get_client_ip',
                'project.context_processors.login_disabled',
                'project.context_processors.get_initial_referer',
                'project.context_processors.get_user_agent',
                'social.apps.django_app.context_processors.backends',
                'social.apps.django_app.context_processors.login_redirect',
            ],
        },
    },
]

MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'lib.middleware.AppendOrRemoveSlashMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'maintenancemode.middleware.MaintenanceModeMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'profiles.middleware.LastSeenMiddleware',
    'profiles.middleware.SocialAuthExceptionMiddleware',

    # 'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATE_VISIBLE_SETTINGS = (
    'S3_URL',
    'SITE_URL',
    'DEFAULT_CACHE_TIMEOUT',
    'DEBUG',
    'SOCIAL_AUTH_FACEBOOK_KEY',
)

ROOT_URLCONF = 'project.urls'

APPEND_SLASH = False

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'project.wsgi.application'

AUTH_USER_MODEL = 'profiles.SuiteUser'
# Auth Stuff.....
AUTHENTICATION_BACKENDS = (
    'social.backends.facebook.FacebookOAuth2',
    'social.backends.google.GoogleOAuth2',
    'social.backends.twitter.TwitterOAuth',
    'django.contrib.auth.backends.ModelBackend',

    'profiles.backends.auth.KeyBasedBackend',
    'profiles.backends.auth.EmailBasedBackend'
)
LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.admin',
   
    # 'django.contrib.redirects',
    'django.contrib.humanize',
    'django.contrib.sitemaps',

    # third party apps
    'django_extensions',
    'djangosecure',
    'elasticsearch',
    'django_nose',
    'compressor',
    'haystack',
    'require',
    'celery_haystack',
    'static_sitemaps',
    'solo',
    'social.apps.django_app.default',
    'hijack',
    'compat',    
    'storages',
    'tastypie',
    'lib',
    'links',
    'notifications',
    'profiles',
    'articles',
    'conversations',
    'moderation',
    'suites',
    'support',
    # 'twitter_api',
    'stats'
)

HANDLEBARS_DIRS = (os.path.join(PROJECT_ROOT, 'static/templates')),

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
        'URL': env_var('HAYSTACK_URL', 'http://127.0.0.1:9200/'),
        'BATCH_SIZE': 100,
        'INDEX_NAME': 'default'
    },
}

HAYSTACK_SIGNAL_PROCESSOR = 'celery_haystack.signals.CelerySignalProcessor'

LOG_STORAGE = env_var('LOG_STORAGE', '/tmp/')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '[%(levelname)s] %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'db': {
            'format': '[%(levelname)s] %(asctime)s %(module)s %(process)d %(thread)d %(message)s %(duration)s'
        },
        'standard': {
            'format': '[%(levelname)s] %(asctime)s %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'filters': ['require_debug_false'],
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_STORAGE + 'suite_application.log',
            'maxBytes': 1024*1024*10,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'request_handler': {
            'level': 'INFO',
            'filters': ['require_debug_false'],
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_STORAGE + 'suite_request.log',
            'maxBytes': 1024*1024*10,
            'backupCount': 5,
            'formatter': 'standard',
        },
        'db_handler': {
            'level': 'INFO',
            'filters': ['require_debug_false'],
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_STORAGE + 'suite_db.log',
            'maxBytes': 1024*1024*10,
            'backupCount': 5,
            'formatter': 'db',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': True
        },
        'django.request': {
            # 'handlers': ['request_handler', 'mail_admins', 'airbrake'],
            'handlers': ['request_handler', 'mail_admins'],
            'level': 'ERROR',
            'propagate': True
        },
        'celery': {
            'level': 'ERROR',
            'handlers': ['mail_admins'],
            'propagate': False,
        },
        'django.db': {
            'handlers': ['db_handler'],
            'level': 'INFO',
            'propagate': False
        },
    }
}

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

###########################################################
# AWS settings
###########################################################

AWS_ACCESS_KEY_ID = env_var('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = env_var('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = env_var('AWS_STORAGE_BUCKET_NAME')
AWS_QUERYSTRING_AUTH = env_var('AWS_QUERYSTRING_AUTH', False)
AWS_S3_SECURE_URLS = False
AWS_IS_GZIPPED = True
AWS_S3_CUSTOM_DOMAIN = env_var('STATIC_URL_BASE', '')
AWS_HEADERS = {
    'Cache-Control': 'max-age=21600',
}
# for file handling only..Fv

AWS_BASE_URL = env_var('AWS_BASE_URL', 's3-us-west-2.amazonaws.com/suite.io.staging')

###########################################################
# Security settings
###########################################################

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = env_var('SECURE_SSL_REDIRECT', False)

SESSION_COOKIE_SECURE = env_var('SESSION_COOKIE_SECURE', False)
SESSION_COOKIE_HTTPONLY = env_var('SESSION_COOKIE_HTTPONLY', False)
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

###########################################################
# Celery settings
###########################################################
BROKER_URL = env_var('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}  # 1 hour.
CELERY_ALWAYS_EAGER = env_var('CELERY_ALWAYS_EAGER', False)

# don't let celery hijack the root logger
CELERYD_HIJACK_ROOT_LOGGER = False

CELERY_IMPORTS = ("lib.tasks", "stats.tasks", "articles.tasks",)
CELERYBEAT_SCHEDULE = {
    'stats_inbox': {
        'task': 'stats.tasks.process_stats_inbox',
        'schedule': timedelta(seconds=30),
        'args': (),
    },
    'truncate_unique_ips': {
        'task': 'stats.tasks.truncate_unique_ip_lists',
        'schedule': crontab(minute=0, hour=0),
        'args': (),
    },
    'sitemaps': {
        'task': 'lib.tasks.refresh_sitemaps',
        'schedule': timedelta(minutes=30),
        'args': (),
    },
}

###########################################################
# Email settings
###########################################################
EMAIL_BACKEND = env_var('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST_USER = env_var('EMAIL_HOST_USER')
SERVER_EMAIL = env_var('EMAIL_HOST_USER')
FROM_EMAIL = env_var('FROM_EMAIL')
EMAIL_HOST_PASSWORD = env_var('EMAIL_HOST_PASSWORD')
EMAIL_HOST = env_var('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = env_var('EMAIL_PORT', '587')
EMAIL_USE_TLS = env_var('EMAIL_USE_TLS', True)


###########################################################
# Storages(django-storages) settings
###########################################################
DEFAULT_FILE_STORAGE = env_var('DEFAULT_FILE_STORAGE', 'django.core.files.storage.FileSystemStorage')
STATICFILES_STORAGE = env_var('STATICFILES_STORAGE', 'django.contrib.staticfiles.storage.StaticFilesStorage')
from boto.s3.connection import OrdinaryCallingFormat 
AWS_S3_CALLING_FORMAT = OrdinaryCallingFormat()

###########################################################
# Compressor settings
###########################################################
COMPRESS_STORAGE = env_var('COMPRESS_STORAGE', 'django.contrib.staticfiles.storage.StaticFilesStorage')
COMPRESS_ENABLED = not DEBUG
COMPRESS_OFFLINE = True
COMPRESS_ROOT = STATIC_ROOT
COMPRESS_URL = STATIC_URL
COMPRESS_OFFLINE = env_var('COMPRESS_OFFLINE', False)
COMPRESS_CSS_HASHING_METHOD = 'content'
COMPRESS_PRECOMPILERS = (
    ('text/less', 'lessc {infile} {outfile}'),
)

#####################################################################
#
# Testing
#
#####################################################################
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
NOSE_ARGS = ['--nologcapture', '-s']

###########################################################
# Cache settings
###########################################################
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'
CACHES = {
    'default': django_cache_url.parse(env_var('CACHE_DEFAULT', 'djangopylibmc://127.0.0.1:11211')),
    'sessions': django_cache_url.parse(env_var('CACHE_SESSIONS', 'djangopylibmc://127.0.0.1:11211'))
}
DEFAULT_CACHE_TIMEOUT = 10800  # 3 hours
SHORT_CACHE_TIMEOUT = 3600 # 1 hours

REDIS_MASTER_HOST = env_var('REDIS_MASTER_HOST', 'localhost')
REDIS_SLAVE_HOST = env_var('REDIS_SLAVE_HOST', 'localhost')

###########################################################
# Maintenance Mode
###########################################################
MAINTENANCE_MODE = env_var('MAINTENANCE_MODE', False)
MAINTENANCE_IGNORE_URLS = (
    r'^/appstatus',
)
LOGIN_DISABLED = env_var('LOGIN_DISABLED', False)

TESTING = False
if 'test' in sys.argv:
    try:
        from test_settings import *
    except ImportError:
        pass
    else:
        TESTING = True

STATICSITEMAPS_ROOT_SITEMAP = 'project.urls.sitemaps'
STATICSITEMAPS_ROOT_DIR = env_var('STATICSITEMAPS_ROOT_DIR', '/home/suite/sitemaps/')
STATICSITEMAPS_URL = env_var('STATICSITEMAPS_URL', 'https://suite.io/sitemaps/')
STATICSITEMAPS_USE_GZIP = True
STATICSITEMAPS_PING_GOOGLE = env_var('STATICSITEMAPS_PING_GOOGLE', False)

MODERATOR_EMAIL = env_var('MODERATOR_EMAIL', 'help@suite.io')

TASTYPIE_DEFAULT_FORMATS = ['json']
API_LIMIT_PER_PAGE = 15

HIJACK_LOGIN_REDIRECT_URL = '/'
HIJACK_LOGOUT_REDIRECT_URL = '/'
HIJACK_DISPLAY_ADMIN_BUTTON = False
HIJACK_AUTHORIZE_STAFF = True
HIJACK_DISPLAY_WARNING = False

###########################################################
# Embedly
###########################################################
EMBEDLY_KEY = env_var('EMBEDLY_KEY')

###########################################################
# Alchemy API
###########################################################
ALCHEMY_API_KEY = env_var('ALCHEMY_API_KEY', '')

###########################################################
# Copyscape
###########################################################
COPYSCAPE_USERNAME = env_var('COPYSCAPE_USERNAME', 'suite')
COPYSCAPE_API_KEY = env_var('COPYSCAPE_API_KEY', '5a57fjt53do5r46c')

###########################################################
# PayPal
###########################################################
PAYPAL_APPID = env_var('PAYPAL_APPID', '')
PAYPAL_USERNAME = env_var('PAYPAL_USERNAME', '')
PAYPAL_PW = env_var('PAYPAL_PW', '')
PAYPAL_SIG = env_var('PAYPAL_SIG', '')

############
# Node Rendering.
############
NODE_PRIMARY_URL = env_var('NODE_PRIMARY_URL', 'http://localhost:1337')
NODE_SECONDARY_URL = env_var('NODE_SECONDARY_URL', 'http://localhost:1337')

###############
# Social AUTH
###############
SOCIAL_AUTH_FACEBOOK_KEY = env_var('SOCIAL_AUTH_FACEBOOK_KEY')
SOCIAL_AUTH_FACEBOOK_SECRET = env_var('SOCIAL_AUTH_FACEBOOK_SECRET')
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email']

# SOCIAL_AUTH_TWITTER_LOGIN_URL = '/login'
SOCIAL_AUTH_TWITTER_KEY = env_var('TWITTER_KEY')
SOCIAL_AUTH_TWITTER_SECRET = env_var('TWITTER_SECRET')
            
TWITTER_KEY = env_var('TWITTER_KEY')
TWITTER_SECRET = env_var('TWITTER_SECRET')
TWITTER_ACCESS_TOKEN = env_var('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = env_var('TWITTER_ACCESS_TOKEN_SECRET')

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = env_var('GOOGLE_OAUTH_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = env_var('GOOGLE_OAUTH_SECRET')

SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'social.pipeline.social_auth.social_user',
    # 'profiles.pipeline.start_association',
    
    # inject our own check for matching email
    'profiles.pipeline.associate_by_email',

    'social.pipeline.user.get_username',
    'social.pipeline.user.create_user',
    'social.pipeline.social_auth.associate_user',
    'social.pipeline.social_auth.load_extra_data',

    # 'profiles.pipeline.require_email_password',

    'social.pipeline.user.user_details',
    # 'profiles.pipeline.user_details',

    # complete the pipeline with our own
    'profiles.pipeline.complete_association'

)

SOCIAL_AUTH_DISCONNECT_PIPELINE = (
    # Verifies that the social association can be disconnected from the current
    # user (ensure that the user login mechanism is not compromised by this
    # disconnection).
    'social.pipeline.disconnect.allowed_to_disconnect',

    # Collects the social associations to disconnect.
    'social.pipeline.disconnect.get_entries',

    # Revoke any access_token when possible.
    'social.pipeline.disconnect.revoke_tokens',

    # Removes the social associations.
    'social.pipeline.disconnect.disconnect',

    'profiles.pipeline.complete_disconnect',
)
DISCONNECT_REDIRECT_URL = '/'

SOCIAL_AUTH_NEW_USER_REDIRECT_URL = '/'
SOCIAL_AUTH_LOGIN_ERROR_URL = '/'
SOCIAL_AUTH_COMPLETE_URL_NAME  = 'socialauth_complete'
SOCIAL_AUTH_ASSOCIATE_URL_NAME = 'socialauth_associate_complete'
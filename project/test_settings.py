"""Local test settings and globals which allows us to run our
test suite locally."""

CELERY_ALWAYS_EAGER = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'my_db',                      # Or path to database file if using sqlite3.
        'USER': '',                   # Not used with sqlite3.
        'PASSWORD': '',               # Not used with sqlite3.
        'HOST': '',                   # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                   # Set to empty string for default. Not used with sqlite3.
    },
    'slave': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'my_db',                      # Or path to database file if using sqlite3.
        'USER': '',                   # Not used with sqlite3.
        'PASSWORD': '',               # Not used with sqlite3.
        'HOST': '',                   # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                   # Set to empty string for default. Not used with sqlite3.
        'TEST_MIRROR': 'default',
    },
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    },
    'sessions': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
    },
}
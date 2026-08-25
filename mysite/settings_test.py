"""Settings used when running the test suite.

The application itself targets PostgreSQL, but the tests do not depend on any
PostgreSQL specific behaviour, so an in-memory SQLite database is used to keep
the suite self contained (no database server required in CI).
"""

from mysite.settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Speed up the tests: the default hasher is intentionally slow.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

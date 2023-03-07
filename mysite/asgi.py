"""
ASGI config for mysite project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

if os.getenv('TRACE_ENABLED') is not None or os.getenv('CLOUD_TRACED_ENABLED') is not None:
    import mysite.opentelemetry_config
    mysite.opentelemetry_config.add_instrumentation()

application = get_asgi_application()

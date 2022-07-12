# Modified from: https://abdus.dev/posts/django-orm-standalone/


from typing import Dict, List, Optional


def init_django(installed_apps: Optional[List[str]] = None, default_database: Optional[Dict[str, str]] = None):
    import django
    from django.conf import settings

    if settings.configured:
        return

    if not installed_apps or not default_database:
        raise ValueError("Django not configured and no installed apps and/or default database provided.")

    settings.configure(
        INSTALLED_APPS=installed_apps,
        DATABASES={
            'default': default_database
        }
    )
    django.setup()

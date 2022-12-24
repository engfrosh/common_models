# Modified from: https://abdus.dev/posts/django-orm-standalone/


from typing import Dict, List, Optional

try:
    from common_models.configs import INSTALLED_APPS, DATABASE
except ModuleNotFoundError:
    INSTALLED_APPS: Optional[List[str]] = None
    DATABASE: Optional[Dict[str, str]] = None


def init_django(
        installed_apps: Optional[List[str]] = INSTALLED_APPS, default_database: Optional[Dict[str, str]] = DATABASE):
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
        },
        DEFAULT_SCAVENGER_PUZZLE_REQUIRE_PHOTO_UPLOAD=True,
        DEBUG=True
    )
    django.setup()

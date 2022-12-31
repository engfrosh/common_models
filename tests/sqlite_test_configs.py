DATABASE = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": "test/temp_db.sqlite3"
}

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'common_models.apps.CommonModelsConfig'
]

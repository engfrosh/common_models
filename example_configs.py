DATABASE = {
    "ENGINE": "django.db.backends.postgresql_psycopg2",
    "NAME": "engfrosh_dev_2022_07_05",
    "USER": "engfrosh_bot",
    "PASSWORD": "mypassword",
    "HOST": "localhost",
    "PORT": "5432",
}

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'common_models.apps.CommonModelsConfig'
]

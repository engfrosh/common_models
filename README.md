# common_models
Common database models for interacting with the common database

## Standalone Setup

Create a `manage.py` file in the parent directory to where common_models is installed.

The `manage.py` file should be as follows:

```python
from common_models.common_modules_setup import init_django

DEFAULT_DATABASE = {
    "ENGINE": "django.db.backends.postgresql_psycopg2",
    "NAME": "engfrosh_dev_2022_07_01",
    "USER": "engfrosh_bot",
    "PASSWORD": "there-exercise-fenegle",
    "HOST": "localhost",
    "PORT": "5432",
}

INSTALLED_APPS = ['common_models', ]

if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    init_django(installed_apps=INSTALLED_APPS, default_database=DEFAULT_DATABASE)
    execute_from_command_line()
```

## Django Integrated Setup

Import the module to your django project folder. In the `settings.py` file add `'common_models.apps.CommonModelsConfig'`
to the `INSTALLED_APPS` setting.

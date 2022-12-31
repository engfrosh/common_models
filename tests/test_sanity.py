from ..common_models_setup import init_django
from .sqlite_test_configs import DATABASE, INSTALLED_APPS


def database_models_sanity():
    init_django(installed_apps=INSTALLED_APPS, default_database=DATABASE)
    return True


def test_database_models_sanity():
    assert database_models_sanity() is True

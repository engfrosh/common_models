from django.db import models
from common_models.common_modules_setup import init_django

init_django()


class NewModel(models.Model):

    id = models.AutoField(primary_key=True)
    name = models.TextField(max_length=40)

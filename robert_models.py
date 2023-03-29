from django.db import models
from django_unixdatetimefield import UnixDateTimeField


class RobertEntry(models.Model):
    user = models.PositiveBigIntegerField("User ID")
    created = UnixDateTimeField(auto_now=True)
    type = models.IntegerField("Robert Type")

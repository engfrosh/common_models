from django.db import models


class RobertEntry(models.Model):
    user = models.PositiveBigIntegerField("User ID")
    created = models.DateTimeField(auto_now=True)
    type = models.IntegerField("Robert Type")

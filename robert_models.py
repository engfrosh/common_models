from django.db import models
from django.db.models.deletion import CASCADE
from common_models.models import DiscordUser


class RobertEntry(models.Model):
    user = models.ForeignKey(DiscordUser, on_delete=CASCADE)
    created = models.DateTimeField(auto_now=True)
    type = models.IntegerField("Robert Type")

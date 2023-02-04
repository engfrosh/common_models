from django.db import models
from django.db.models.deletion import CASCADE, SET_NULL
import common_models.models as md
from django_unixdatetimefield import UnixDateTimeField


class TeamTradeUpActivity(models.Model):

    team = models.ForeignKey(md.Team, on_delete=CASCADE)
    verification_photo = models.ForeignKey(md.VerificationPhoto, on_delete=SET_NULL, null=True,
                                           blank=True, default=None)
    entered_at = UnixDateTimeField(auto_now=True)
    object_name = models.CharField(max_length=200, null=True, blank=True)

    class Meta:

        verbose_name = "Team Trade Up Activity"
        verbose_name_plural = "Team Trade Up Activities"

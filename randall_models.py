from django.db import models
from django.db.models.deletion import CASCADE
from django.contrib.auth.models import User
import geopy.distance


class RandallBooking(models.Model):
    user = models.ForeignKey(User, on_delete=CASCADE)
    start = models.DateTimeField()
    end = models.DateTimeField()
    message = models.TextField()
    approved = models.BooleanField(default=False)
    permissions = [
        ("book_randall", "Can create bookings"),
        ("manage_randall", "Can manage bookings"),
        ("locate_randall", "Can send location data through the API"),
        ("view_randall", "Can view randall")
    ]


class RandallLocation(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()
    altitude = models.IntegerField()
    timestamp = models.DateTimeField(auto_now=True)

    CAMPUS = (45.387096, -75.695891)

    @property
    def is_on_campus(self):
        return geopy.distance.geodesic(self.CAMPUS, (self.latitude, self.longitude)).km <= 1.0


class RandallBlocked(models.Model):
    start = models.DateTimeField()
    end = models.DateTimeField()

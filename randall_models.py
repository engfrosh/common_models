from django.db import models
from django.db.models.deletion import CASCADE, SET_NULL
from django.contrib.auth.models import User, Group
import common_models.models as md
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
    def is_on_campus():
        return geopy.distance.geodesic(CAMPUS, (latitude, longitude)).km <= 1.0

class RandallBlocked(models.Model):
    start = models.DateTimeField()
    end = models.DateTimeField()
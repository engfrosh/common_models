"""Admin site setup for common_models"""

from django.contrib import admin

from .models import Puzzle

admin.site.register([Puzzle])

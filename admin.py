"""Admin site setup for common_models"""

from django.contrib import admin


from .models import Puzzle, Team

# admin.site.register([Puzzle])


class PuzzleAdmin(admin.ModelAdmin):
    """Admin for Scavenger Puzzle"""

    pass


admin.site.register(Puzzle, PuzzleAdmin)


class TeamAdmin(admin.ModelAdmin):
    """Admin for scavenger teams."""

    pass


admin.site.register(Team, TeamAdmin)

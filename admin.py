"""Admin site setup for common_models"""

from typing import Optional, Sequence
from django.contrib import admin


from .models import ChannelTag, DiscordBingoCards, DiscordChannel, DiscordOverwrite, DiscordRole, FroshRole, Puzzle, PuzzleStream, \
    Team, DiscordUser, MagicLink, TeamPuzzleActivity, UniversityProgram, UserDetails, VerificationPhoto, VirtualTeam, DiscordGuild

# region Discord


class DiscordRoleAdmin(admin.ModelAdmin):
    pass


admin.site.register(DiscordRole, DiscordRoleAdmin)


class DiscordOverwriteAdmin(admin.ModelAdmin):
    pass

# region Discord Channels & Channel Tags


@admin.action(description="Lock Channels")
def lock_discord_channels(modeladmin, request, queryset):
    """Lock Channels."""

    for obj in queryset:
        obj.lock()


@admin.action(description="Unlock Channels")
def unlock_discord_channels(modeladmin, request, queryset):
    """Unlock Channels."""

    for obj in queryset:
        obj.unlock()


class DiscordChannelAdmin(admin.ModelAdmin):

    actions = [
        lock_discord_channels,
        unlock_discord_channels
    ]


class ChannelTagAdmin(admin.ModelAdmin):

    actions = [
        lock_discord_channels,
        unlock_discord_channels
    ]
# endregion


class DiscordUserAdmin(admin.ModelAdmin):
    """Admin for Discord Users."""

    list_display = ('discord_username', 'user')
    search_fields = ('discord_username', 'user__username')

# region Discord Guild


@admin.action(description="Delete guild from discord")
def delete_discord_guild(modeladmin, request, queryset):

    for obj in queryset:
        obj.delete_guild()


class DiscordGuildAdmin(admin.ModelAdmin):

    actions = [
        delete_discord_guild
    ]
    list_display = ("name", "id", "deleted")
    search_fields = ("name", "id")
    ordering: Optional[Sequence[str]] = ["deleted"]


admin.site.register(DiscordGuild, DiscordGuildAdmin)
# endregion

admin.site.register(ChannelTag, ChannelTagAdmin)
admin.site.register(DiscordOverwrite, DiscordOverwriteAdmin)
admin.site.register(DiscordChannel, DiscordChannelAdmin)
admin.site.register(DiscordUser, DiscordUserAdmin)

# endregion


class PuzzleStreamAdmin(admin.ModelAdmin):

    pass


admin.site.register(PuzzleStream, PuzzleStreamAdmin)


class PuzzleAdmin(admin.ModelAdmin):
    """Admin for Scavenger Puzzle"""

    list_display = ("name", "stream", "enabled", "order", "answer")
    search_fields = ("id", "name", "answer", "secret_id", "stream", "order", "puzzle_text")
    ordering: Optional[Sequence[str]] = ("enabled", "stream", "order")


class TeamPuzzleActivityAdmin(admin.ModelAdmin):

    @admin.display(boolean=True, description="Is Active")
    def activity_is_active(self, obj) -> bool:
        return obj.is_active

    @admin.display(boolean=True, description="Is Completed")
    def activity_is_completed(self, obj) -> bool:
        return obj.is_completed

    readonly_fields: Sequence[str] = ('puzzle_start_at', "activity_is_active", "activity_is_completed")
    list_display = ("team", "puzzle", "activity_is_active", "activity_is_completed",
                    "puzzle_start_at", "puzzle_completed_at", "locked_out_until")


admin.site.register(TeamPuzzleActivity, TeamPuzzleActivityAdmin)


class VerificationPhotoAdmin(admin.ModelAdmin):

    list_display = ("datetime", "approved")


admin.site.register(VerificationPhoto, VerificationPhotoAdmin)


class TeamAdmin(admin.ModelAdmin):
    """Admin for teams."""

    list_display = ("display_name", "scavenger_team", "scavenger_finished")
    search_fields: Sequence[str] = ("display_name", "group")
    actions = [
        "reset_team_scavenger_progress"
    ]
    ordering: Optional[Sequence[str]] = ("scavenger_team",)

    @admin.action(description="Reset team scavenger progress")
    def reset_team_scavenger_progress(self, request, queryset):

        for obj in queryset:
            obj.reset_scavenger_progress()


class MagicLinkAdmin(admin.ModelAdmin):
    """Admin for Magic Links."""

    list_display = ('user', 'expiry', 'delete_immediately')


admin.site.register(Puzzle, PuzzleAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(MagicLink, MagicLinkAdmin)

admin.site.register([FroshRole, UniversityProgram, VirtualTeam])


class UserDetailsAdmin(admin.ModelAdmin):
    """User Details Admin."""

    search_fields = ('user__username', 'name')


admin.site.register(UserDetails, UserDetailsAdmin)


class DiscordBingoCardAdmin(admin.ModelAdmin):
    """Discord Bingo Card Admin."""

    list_display = ('bingo_card', 'discord_id')
    search_fields = ('bingo_card', 'discord_id')


admin.site.register(DiscordBingoCards, DiscordBingoCardAdmin)

# admin.site.register([Hint, QuestionTime, Settings])

# # region Question Admin
# class QuestionAdmin(admin.ModelAdmin):
#     """Admin for Scavenger Questions."""

#     ordering = ["weight"]


# admin.site.register(Question, QuestionAdmin)
# # endregion

# # region Team Admin


# @admin.action(description="Reset selected teams' progress")
# def reset_scavenger_progress(modeladmin, request, queryset):
#     """Reset selected teams scavenger progress back to the beginning."""

#     for obj in queryset:
#         obj.reset_progress()


# @admin.action(description="Remove lockouts and cooldowns")
# def remove_lockouts_cooldowns(modeladmin, request, queryset):
#     """Remove the lockouts and cooldowns for selected teams."""

#     for obj in queryset:
#         obj.remove_blocks()


# @admin.action(description="Lockout teams for 15 minutes")
# def lockout_15_minutes(modeladmin, request, queryset):
#     """Lockout teams for 15 minutes."""

#     for obj in queryset:
#         obj.lockout(datetime.timedelta(minutes=15))


# endregion

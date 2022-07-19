"""Admin site setup for common_models"""

from django.contrib import admin


from .models import ChannelTag, DiscordChannel, DiscordOverwrite, Puzzle, Team, DiscordUser, MagicLink

# admin.site.register([Puzzle])


class PuzzleAdmin(admin.ModelAdmin):
    """Admin for Scavenger Puzzle"""

    pass


class TeamAdmin(admin.ModelAdmin):
    """Admin for scavenger teams."""

    pass


class DiscordRoleAdmin(admin.ModelAdmin):
    pass


class DiscordOverwriteAdmin(admin.ModelAdmin):
    pass


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


class DiscordUserAdmin(admin.ModelAdmin):
    """Admin for Discord Users."""

    list_display = ('discord_username', 'user')
    search_fields = ('discord_username', 'user__username')


class MagicLinkAdmin(admin.ModelAdmin):
    """Admin for Magic Links."""

    list_display = ('user', 'expiry', 'delete_immediately')


admin.site.register(Puzzle, PuzzleAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(ChannelTag, ChannelTagAdmin)
admin.site.register(DiscordOverwrite, DiscordOverwriteAdmin)
admin.site.register(DiscordChannel, DiscordChannelAdmin)
admin.site.register(MagicLink, MagicLinkAdmin)
admin.site.register(DiscordUser, DiscordUserAdmin)

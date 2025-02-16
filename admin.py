"""Admin site setup for common_models"""

from typing import Iterable, Optional, Sequence
from django.contrib import admin


from .models import BooleanSetting, ChannelTag, DiscordChannel, DiscordOverwrite, DiscordRole, \
    FroshRole, Puzzle, PuzzleGuess, PuzzleStream, Team, DiscordUser, MagicLink, \
    TeamPuzzleActivity, TeamTradeUpActivity, UniversityProgram, \
    UserDetails, VerificationPhoto, VirtualTeam, DiscordGuild, Announcement, \
    InclusivityPage, FacilShift, FacilShiftSignup, RoleInvite, \
    Setting, LockoutPeriod, FAQPage, QRCode, RoleOption, SiteImage, TeamRoom, Event, \
    Calendar, CalendarRelation, EventRelation, Pronoun, PronounOption, DiscordMessage


class DiscordMessageAdmin(admin.ModelAdmin):
    list_display = ("type", "id")


admin.site.register(DiscordMessage, DiscordMessageAdmin)


class PronounAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "user")


admin.site.register(Pronoun, PronounAdmin)


class PronounOptionAdmin(admin.ModelAdmin):
    list_display = ("emote", "name")


admin.site.register(PronounOption, PronounOptionAdmin)


class EventRelationAdmin(admin.ModelAdmin):
    list_display = ("event", "content_type", "object_id")


admin.site.register(EventRelation, EventRelationAdmin)


class CalendarAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")


admin.site.register(Calendar, CalendarAdmin)


class CalendarRelationAdmin(admin.ModelAdmin):
    list_display = ("calendar", "content_type", "object_id")


admin.site.register(CalendarRelation, CalendarRelationAdmin)


class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "start", "end")


admin.site.register(Event, EventAdmin)


class TeamRoomAdmin(admin.ModelAdmin):
    list_display = ("team", "date", "room")


admin.site.register(TeamRoom, TeamRoomAdmin)


class SiteImageAdmin(admin.ModelAdmin):
    list_display = ("name",)


admin.site.register(SiteImage, SiteImageAdmin)


class RoleOptionAdmin(admin.ModelAdmin):
    list_display = ("emote", "role", "message")


admin.site.register(RoleOption, RoleOptionAdmin)


class QRCodeAdmin(admin.ModelAdmin):
    pass


admin.site.register(QRCode, QRCodeAdmin)


class FAQPageAdmin(admin.ModelAdmin):
    list_display = ("title",)


admin.site.register(FAQPage, FAQPageAdmin)


class LockoutPeriodAdmin(admin.ModelAdmin):
    list_display = ("start", "end", "branch")


admin.site.register(LockoutPeriod, LockoutPeriodAdmin)


class BooleanSettingAdmin(admin.ModelAdmin):

    readonly_fields: Sequence[str] = ("id",)
    list_display = ("id", "value")
    actions = [
        "set_value_to_false",
        "set_value_to_true"
    ]

    @admin.action(description="Set value to False")
    def set_value_to_false(self, request, queryset: Iterable[BooleanSetting]):

        for obj in queryset:
            obj.value = False
            obj.save()

    @admin.action(description="Set value to True")
    def set_value_to_true(self, request, queryset: Iterable[BooleanSetting]):

        for obj in queryset:
            obj.value = True
            obj.save()


admin.site.register(BooleanSetting, BooleanSettingAdmin)


class SettingAdmin(admin.ModelAdmin):
    list_display = ("id", "value")
    search_fields = ("id",)


admin.site.register(Setting, SettingAdmin)


class RoleInviteAdmin(admin.ModelAdmin):
    search_fields = ('user__username', 'link')


admin.site.register(RoleInvite, RoleInviteAdmin)


class InclusivityPageAdmin(admin.ModelAdmin):
    pass


admin.site.register(InclusivityPage, InclusivityPageAdmin)


class FacilShiftAdmin(admin.ModelAdmin):
    list_display = ('name', 'desc', 'administrative', 'start', 'end')
    search_fields = ('name', 'desc')


admin.site.register(FacilShift, FacilShiftAdmin)


class FacilShiftSignupAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'user')
    search_fields = ('shift__name', 'user__username')

    def get_name(self, obj):
        return obj.shift.name

    get_name.short_description = "Name"


admin.site.register(FacilShiftSignup, FacilShiftSignupAdmin)


# region Announcement


class AnnouncementAdmin(admin.ModelAdmin):
    pass


admin.site.register(Announcement, AnnouncementAdmin)

# region Discord


class DiscordRoleAdmin(admin.ModelAdmin):
    pass


admin.site.register(DiscordRole, DiscordRoleAdmin)


class DiscordOverwriteAdmin(admin.ModelAdmin):
    search_fields = ('descriptive_name',)

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
    search_fields = ('name', 'team__display_name')


class ChannelTagAdmin(admin.ModelAdmin):

    actions = [
        lock_discord_channels,
        unlock_discord_channels
    ]
    search_fields = ('name',)
# endregion


class DiscordUserAdmin(admin.ModelAdmin):
    """Admin for Discord Users."""

    list_display = ('discord_username', 'user')
    search_fields = ('discord_username', 'user__username')
    actions = ("kick_user_from_default_guild",)

    @admin.action(description="Kick from default guild")
    def kick_user_from_default_guild(self, request, queryset: Iterable[DiscordUser]):

        for obj in queryset:
            obj.kick_user()

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
    list_display = ("name", "enabled", "locked")


admin.site.register(PuzzleStream, PuzzleStreamAdmin)


class PuzzleAdmin(admin.ModelAdmin):
    """Admin for Scavenger Puzzle"""

    list_display = ("name", "stream", "enabled", "order", "answer", "stream_branch", "stream_puzzle")
    readonly_fields = ("secret_id",)
    search_fields = ("id", "name", "answer", "secret_id", "stream__name", "order", "puzzle_text")
    ordering: Optional[Sequence[str]] = ("enabled", "stream", "order")
    actions = ("disable_puzzle", "enable_puzzle")

    def stream_branch(self, obj):
        return obj.stream_branch.name

    def stream_puzzle(self, obj):
        return obj.stream_puzzle.name

    @admin.action(description="Disable puzzle")
    def disable_puzzle(self, request, queryset):
        for obj in queryset:
            obj.enabled = False
            obj.save()

    @admin.action(description="Enable puzzle")
    def enable_puzzle(self, request, queryset):
        for obj in queryset:
            obj.enabled = True
            obj.save()


class TeamTradeUpActivityAdmin(admin.ModelAdmin):

    list_display = ("team", "entered_at")


admin.site.register(TeamTradeUpActivity, TeamTradeUpActivityAdmin)


class TeamPuzzleActivityAdmin(admin.ModelAdmin):

    @admin.display(boolean=True, description="Is Active")
    def activity_is_active(self, obj) -> bool:
        return obj.is_active

    @admin.display(boolean=True, description="Is Completed")
    def activity_is_completed(self, obj) -> bool:
        return obj.is_completed

    @admin.display(boolean=True, description="Is Verified")
    def activity_is_verified(self, obj) -> bool:
        return obj.is_verified

    readonly_fields: Sequence[str] = ('puzzle_start_at', "activity_is_active",
                                      "activity_is_completed", "activity_is_verified")
    list_display = ("team", "puzzle", "activity_is_active", "activity_is_completed", "activity_is_verified",
                    "puzzle_start_at", "puzzle_completed_at")
    ordering = ("-puzzle_completed_at",)


admin.site.register(TeamPuzzleActivity, TeamPuzzleActivityAdmin)


class VerificationPhotoAdmin(admin.ModelAdmin):

    list_display = ("pk", "datetime", "approved")


admin.site.register(VerificationPhoto, VerificationPhotoAdmin)


class PuzzleGuessAdmin(admin.ModelAdmin):

    list_display = ("activity", "datetime", "value")


admin.site.register(PuzzleGuess, PuzzleGuessAdmin)


class TeamAdmin(admin.ModelAdmin):
    """Admin for teams."""

    list_display = ("display_name", "scavenger_team", "scavenger_finished",
                    "scavenger_enabled_for_team", "trade_up_enabled_for_team")
    search_fields: Sequence[str] = ("display_name", "group")
    actions = [
        "reset_team_scavenger_progress",
        "refresh_team_scavenger_progress",
        "enable_scavenger_for_team",
        "disable_scavenger_for_team",
        "enable_trade_up_for_team",
        "disable_trade_up_for_team"
    ]
    ordering: Optional[Sequence[str]] = ("scavenger_team",)

    @admin.display(boolean=True, description="Scavenger Enabled for Team")
    def scavenger_enabled_for_team(self, obj: Team) -> bool:
        return obj.scavenger_enabled_for_team

    @admin.action(description="Reset team scavenger progress")
    def reset_team_scavenger_progress(self, request, queryset):

        for obj in queryset:
            obj.reset_scavenger_progress()

    @admin.action(description="Refresh team scavenger progress")
    def refresh_team_scavenger_progress(self, request, queryset: Iterable[Team]):

        for obj in queryset:
            obj.refresh_scavenger_progress()

    @admin.action(description="Enable scavenger for the team")
    def enable_scavenger_for_team(self, request, queryset: Iterable[Team]):

        for obj in queryset:
            obj.enable_scavenger_for_team()

    @admin.action(description="Disable scavenger for the team")
    def disable_scavenger_for_team(self, request, queryset: Iterable[Team]):

        for obj in queryset:
            obj.disable_scavenger_for_team()

    @admin.action(description="Enable trade up for the team")
    def enable_trade_up_for_team(self, request, queryset: Iterable[Team]):

        for obj in queryset:
            obj.enable_trade_up_for_team()

    @admin.action(description="Disable trade up for the team")
    def disable_trade_up_for_team(self, request, queryset: Iterable[Team]):

        for obj in queryset:
            obj.disable_trade_up_for_team()


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
    list_display = ['name', 'prc_completed']


admin.site.register(UserDetails, UserDetailsAdmin)


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

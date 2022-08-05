"""


Some inspiration from: https://github.com/Palindrome-Puzzles/2022-hunt/blob/main/hunt/app/models.py
"""

from __future__ import annotations
from collections import namedtuple

import string
import os
import random
import datetime
import secrets
import logging

from typing import List, Dict, Optional
from engfrosh_site.settings import DEFAULT_DISCORD_API_VERSION
from pyaccord import Client
from pyaccord.types.guild import Guild

logger = logging.getLogger("common_models.models")

from common_models.common_models_setup import init_django  # noqa: E402
init_django()

from django.db import models  # noqa: E402
from django.db.models.deletion import CASCADE, PROTECT  # noqa: E402
from django.contrib.auth.models import User, Group  # noqa: E402
from django.utils import timezone  # noqa: E402
from django.core.exceptions import ObjectDoesNotExist  # noqa: E402
from django.conf import settings  # noqa: E402


SCAVENGER_DIR = "scavenger/"
PUZZLE_DIR = "puzzles/"

FILE_RANDOM_LENGTH = 128


def random_path(instance, filename, base=""):
    _, ext = os.path.splitext(filename)
    rnd = "".join(random.choice(string.ascii_letters + string.digits) for i in range(FILE_RANDOM_LENGTH))
    return base + rnd + ext


def puzzle_path(instance, filename):
    return random_path(instance, filename, SCAVENGER_DIR + PUZZLE_DIR)

# For Legacy
# TODO: Remove


def hint_path(instance, filename):
    return random_path(instance, filename, SCAVENGER_DIR + "hints/")


def question_path(instance, filename):
    return puzzle_path(instance, filename)

# region Scavenger


class PuzzleStream(models.Model):
    """Puzzle streams in scavenger"""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self) -> str:
        return f"{self.name}"

    class Meta:
        verbose_name = "Scavenger Puzzle Stream"
        verbose_name_plural = "Scavenger Puzzle Streams"


class Puzzle(models.Model):
    """Puzzles in scavenger"""

    id = models.AutoField(unique=True, primary_key=True)
    name = models.CharField(max_length=200, unique=True)
    answer = models.CharField(max_length=100)

    enabled = models.BooleanField(default=True)

    order = models.PositiveIntegerField()
    stream = models.ForeignKey(PuzzleStream, on_delete=PROTECT)

    puzzle_text = models.CharField("Text", blank=True, max_length=2000)
    puzzle_file = models.FileField(upload_to=puzzle_path, blank=True)
    puzzle_file_display_filename = models.CharField(max_length=256, blank=True)
    puzzle_file_download = models.BooleanField(default=False)
    puzzle_file_is_image = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # teams = models.ManyToManyField(Team, through="TeamPuzzleActivity")

    def __str__(self: Puzzle) -> str:
        return f"Puzzle: {self.name} [{self.id}]"

    class Meta:
        verbose_name = "Scavenger Puzzle"
        verbose_name_plural = "Scavenger Puzzles"

        permissions = [
            ("guess_scavenger_puzzle", "Can guess for scavenger puzzle"),
            ("manage_scav", "Can manage scav")
        ]


# class Hint(models.Model):
#     """Scavenger Hint Model."""

#     id = models.AutoField("Hint ID", primary_key=True)
#     question = models.ForeignKey(Question, CASCADE, db_index=True)
#     text = models.CharField("Hint Text", blank=True, max_length=2000)
#     file = models.FileField(upload_to=hint_path, blank=True)
#     display_filename = models.CharField(max_length=256, blank=True)
#     weight = models.IntegerField(default=0)
#     enabled = models.BooleanField(default=True)
#     lockout_time = models.IntegerField("Lockout Duration in Seconds", default=900)
#     cooldown_time = models.IntegerField("Hint Cooldown duration in Seconds", null=True, default=None)

#     class Meta:
#         """Scavenger Hints Meta info."""

#         verbose_name = "Scavenger Hint"
#         verbose_name_plural = "Scavenger Hints"

#     def __str__(self):
#         return f"{self.question} - Hint {self.weight}"

# class Settings(models.Model):
#     id = models.AutoField(primary_key=True)
#     name = models.CharField(max_length=32, unique=True)
#     display_name = models.CharField(max_length=64, blank=True)
#     enabled = models.BooleanField(default=False)

#     def __str__(self) -> str:
#         if self.display_name:
#             return self.display_name
#         else:
#             return self.name

# endregion


class Team(models.Model):
    """Model of frosh team."""

    display_name = models.CharField("Team Name", max_length=64, unique=True)
    group = models.OneToOneField(Group, CASCADE, primary_key=True)
    scavenger_team = models.BooleanField(default=True)
    scavenger_finished = models.BooleanField("Finished Scavenger", default=False)
    coin_amount = models.BigIntegerField("Coin Amount", default=0)
    color = models.PositiveIntegerField("Hex Color Code", null=True, blank=True, default=None)
    puzzles = models.ManyToManyField(Puzzle, through="TeamPuzzleActivity")
    scavenger_locked_out_until = models.DateTimeField(null=True, default=None)

    # hint_cooldown_until = models.DateTimeField("Hint Cooldown Until", blank=True, null=True)
    # last_hint = models.ForeignKey(Hint, blank=True, on_delete=PROTECT, null=True)
    # last_hint_time = models.DateTimeField(blank=True, null=True)
    # finished = models.BooleanField("Finished Scavenger", default=False)

    class Meta:
        verbose_name = "Team"
        verbose_name_plural = "Teams"
        permissions = [
            ("change_team_coin", "Can change the coin amount of a team."),
            ("view_team_coin_standings", "Can view the coin standings of all teams.")
        ]

    def __str__(self):
        return str(self.display_name)

    @property
    def to_dict(self):
        """Get the dict representation of the team."""
        return {
            "team_id": self.group.id,
            "team_name": self.display_name,
            "coin_amount": self.coin_amount,
            "color_number": self.color,
            "color_code": self.color_code
        }

    @property
    def color_code(self):
        """The hex color code string of the team's color."""
        if self.color is not None:
            return "#{:06x}".format(self.color)
        else:
            return None

    def reset_progress(self):
        """Reset the team's current scavenger question to the first enabled question."""
        #     if Question.objects.filter(enabled=True).exists():
        #         first_question = Question.objects.filter(enabled=True).order_by("weight")[0]
        #     else:
        #         first_question = None
        #     self.current_question = first_question
        #     self.last_hint = None
        #     self.locked_out_until = None
        #     self.hint_cooldown_until = None
        #     self.finished = False
        #     self.save()
        raise NotImplementedError("Reset progress not implemented yet")

    def remove_blocks(self):
        """Remove lockouts and cooldowns."""

        #     self.locked_out_until = None
        #     self.hint_cooldown_until = None

        #     self.save()
        raise NotImplementedError("Remove blocks not implemented yet")

    def lockout(self, duration: Optional[datetime.timedelta] = None) -> None:
        """Lockout team for seconds."""

        #     if duration is None:
        #         duration = datetime.timedelta(minutes=15)

        #     now = timezone.now()
        #     until = now + duration
        #     self.locked_out_until = until
        #     self.save()
        raise NotImplementedError("Lockout team not implemented yet")


class TeamPuzzleActivity(models.Model):
    """Relates teams to the puzzles they have active and have completed."""

    team = models.ForeignKey(Team, on_delete=CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=CASCADE)
    puzzle_start_at = models.DateTimeField(auto_now=True)
    puzzle_completed_at = models.DateTimeField(null=True, default=None)
    locked_out_until = models.DateTimeField(null=True, default=None)


class PuzzleGuess(models.Model):
    """Stores all the guesses for scavenger."""

    datetime = models.DateTimeField(auto_now=True)
    value = models.CharField(max_length=100)
    activity = models.ForeignKey(TeamPuzzleActivity, on_delete=CASCADE)


class FroshRole(models.Model):
    """Frosh role, such as Frosh, Facil, Head, Planning."""

    name = models.CharField("Role Name", max_length=64, unique=True)
    group = models.OneToOneField(Group, on_delete=CASCADE, primary_key=True)

    class Meta:
        """Frosh Role Meta information."""

        verbose_name = "Frosh Role"
        verbose_name_plural = "Frosh Roles"

    def __str__(self) -> str:
        return self.name


class UniversityProgram(models.Model):
    """Map a role as a course program."""

    name = models.CharField("Program Name", max_length=64, unique=True)
    group = models.OneToOneField(Group, on_delete=CASCADE, primary_key=True)

    class Meta:
        """University Program Meta Information."""

        verbose_name = "Program"
        verbose_name_plural = "Programs"

    def __str__(self) -> str:
        return self.name


class UserDetails(models.Model):
    """Details pertaining to users without fields in the default User."""

    user = models.OneToOneField(User, on_delete=CASCADE, primary_key=True)
    name = models.CharField("Name", max_length=64)
    pronouns = models.CharField("Pronouns", max_length=20, blank=True)
    invite_email_sent = models.BooleanField("Invite Email Sent", default=False)

    class Meta:
        """User Details Meta information."""

        verbose_name = "User Details"
        verbose_name_plural = "Users' Details"

    def __str__(self) -> str:
        return f"{self.name} ({self.user.username})"


class DiscordBingoCards(models.Model):
    """Lists bingo cards and their assigned discord ids."""

    discord_id = models.PositiveBigIntegerField(db_index=True, unique=True)
    bingo_card = models.PositiveIntegerField(primary_key=True)

    class Meta:
        """Discord Bingo Card Meta Information."""

        verbose_name = "Discord Bingo Card"
        verbose_name_plural = "Discord Bingo Cards"

    def __str__(self) -> str:
        return f"<Bingo Card {self.bingo_card} assigned to {self.discord_id}>"


class VirtualTeam(models.Model):
    """Tracks Virtual Teams and their discord ids."""

    role_id = models.PositiveBigIntegerField(primary_key=True)
    num_members = models.PositiveIntegerField(unique=False, default=0)

    class Meta:
        """Virtual Team Meta Information."""

        verbose_name = "Virtual Team"
        verbose_name_plural = "Virtual Teams"

    def __str__(self) -> str:
        return f"<Virtual Team {self.role_id} with {self.num_members} members>"


# region Discord

DiscordGuildUpdateGuildResult = namedtuple("DiscordGuildUpdatedGuildResult", [
                                           "num_added", "num_existing_updated",
                                           "num_existing_not_updated", "num_removed"])


class DiscordGuild(models.Model):
    """Refers to a discord server (guild)"""

    id = models.PositiveBigIntegerField(primary_key=True)
    name = models.CharField(max_length=200)
    deleted = models.BooleanField(default=False)

    def __init__(self, *args, pyaccord_guild: Optional[Guild] = None, **kwargs) -> None:
        if pyaccord_guild:
            super().__init__(*args, id=pyaccord_guild.id, name=pyaccord_guild.name, **kwargs)
        else:
            super().__init__(*args, **kwargs)

    class Meta:

        verbose_name = "Discord Guild"
        verbose_name_plural = "Discord Guilds"
        permissions = [
        ]

    def __str__(self) -> str:
        if self.deleted:
            return f"{self.name} [DELETED]"
        else:
            return f"{self.name}"

    def __repr__(self) -> str:
        if self.deleted:
            return f"<Guild: {self.name} #{self.id} [DELETED]>"
        else:
            return f"<Guild: {self.name} #{self.id}>"

    def delete_guild(self) -> None:
        """Deletes the specified guild from discord and sets it's value to deleted."""

        client = Client(settings.DISCORD_BOT_TOKEN, api_version=DEFAULT_DISCORD_API_VERSION)

        client.delete_guild(self.id)

        self.deleted = True
        self.save()

    @staticmethod
    def create_new_guild(name: str) -> DiscordGuild:
        """Creates a new guild using the discord api, saves it to the database and returns the database object."""

        client = Client(settings.DISCORD_BOT_TOKEN, api_version=DEFAULT_DISCORD_API_VERSION)

        pyaccord_guild = client.create_guild(name)

        guild = DiscordGuild(pyaccord_guild=pyaccord_guild)

        guild.save()

        return guild

    @staticmethod
    def scan_and_update_guilds() -> DiscordGuildUpdateGuildResult:
        """Returns (num_added, num_existing_updated, num_existing_not_updated, num_removed)"""

        client = Client(settings.DISCORD_BOT_TOKEN, api_version=DEFAULT_DISCORD_API_VERSION)

        current_guilds = client.get_current_user_guilds()

        existing_guilds = DiscordGuild.objects.all()

        num_added = 0
        num_existing_updated = 0
        num_existing_not_updated = 0
        num_removed = 0

        for g in current_guilds:
            exg = existing_guilds.filter(id=g.id)
            if exg.exists():
                updated_guild: DiscordGuild = exg.first()  # type: ignore
                if updated_guild.name != g.name:
                    updated_guild.name = g.name
                    updated_guild.save()
                    num_existing_updated += 1
                else:
                    num_existing_not_updated += 1

            else:
                new_guild = DiscordGuild(pyaccord_guild=g)
                new_guild.save()
                num_added += 1

        existing_ids = [g.id for g in current_guilds]

        removed_guilds = existing_guilds.exclude(id__in=existing_ids)

        for g in removed_guilds:
            g.deleted = True
            g.save()
            num_removed += 1

        return DiscordGuildUpdateGuildResult(num_added, num_existing_updated, num_existing_not_updated, num_removed)


class Role(models.Model):
    """Relates a Django group to a discord role."""

    role_id = models.PositiveBigIntegerField("Discord Role ID", primary_key=True)
    group_id = models.OneToOneField(Group, CASCADE)

    class Meta:
        """Meta information for Discord roles."""

        verbose_name = "Discord Role"
        verbose_name_plural = "Discord Roles"

    def __str__(self) -> str:
        return self.group_id.name


class ChannelTag(models.Model):
    """Tags classifying Discord Channels."""

    id = models.AutoField(primary_key=True)
    name = models.CharField("Tag Name", max_length=64, unique=True)

    class Meta:
        """ChannelTag Meta information."""

        verbose_name = "Channel Tag"
        verbose_name_plural = "Channel Tags"

    def __str__(self) -> str:
        return self.name

    def lock(self):
        """Lock the channel."""

        for channel in DiscordChannel.objects.filter(tags__id=self.id):
            channel.lock()

    def unlock(self):
        """Unlock the channel."""
        for channel in DiscordChannel.objects.filter(tags__id=self.id):
            channel.unlock()


class DiscordOverwrite(models.Model):
    """Represents Discord Permission Overwrites."""

    descriptive_name = models.CharField(max_length=100, blank=True, default="")
    id = models.AutoField("Overwrite ID", primary_key=True)
    user_id = models.PositiveBigIntegerField("User or Role ID")
    type = models.IntegerField(choices=[(0, "Role"), (1, "Member")])
    allow = models.PositiveBigIntegerField("Allowed Overwrites")
    deny = models.PositiveBigIntegerField("Denied Overwrites")

    class Meta:
        """Discord Overwrite Meta Info."""

        verbose_name = "Discord Permission Overwrite"
        verbose_name_plural = "Discord Permission Overwrites"

    def __str__(self) -> str:
        if self.descriptive_name:
            return self.descriptive_name
        elif self.type == 0:
            try:
                role = Role.objects.get(role_id=self.user_id)
                return f"Role Overwrite for {role.group_id.name}"
            except ObjectDoesNotExist:
                return f"Role Overwrite: {self.user_id}"
        else:
            return f"User Overwrite: {self.user_id}"

    @property
    def verbose(self) -> str:
        """Return a verbose representation of the object."""
        return f"<DiscordOverwrite: id = {self.id}, user_id = {self.user_id}, allow = {self.allow}, deny = {self.deny}"

    @property
    def to_encoded_dict(self) -> dict:
        """Return the encoded dictionary version."""
        d = {
            "id": self.user_id,
            "allow": str(self.allow),
            "deny": str(self.deny)
        }
        return d

    @staticmethod
    def overwrite_from_dict(d: dict) -> DiscordOverwrite:
        """Create a DiscordOverwrite object from the json encoded response dictionary."""
        return DiscordOverwrite(
            user_id=int(d["id"]),
            type=d["type"],
            allow=int(d["allow"]),
            deny=int(d["deny"])
        )


class DiscordChannel(models.Model):
    """Discord Channel Object."""

    id = models.PositiveBigIntegerField("Discord Channel ID", primary_key=True)
    name = models.CharField("Discord Channel Name", max_length=100, unique=False, blank=True, default="")
    tags = models.ManyToManyField(ChannelTag, blank=True)
    type = models.IntegerField("Channel Type", choices=[
        (0, "GUILD_TEXT"),
        (1, "DM"),
        (2, "GUILD_VOICE"),
        (3, "GROUP_DM"),
        (4, "GUILD_CATEGORY"),
        (5, "GUILD_NEWS"),
        (6, "GUILD_STORE"),
        (10, "GUILD_NEWS_THREAD"),
        (11, "GUILD_PUBLIC_THREAD"),
        (12, "GUILD_PRIVATE_THREAD"),
        (13, "GUILD_STAGE_VOICE")
    ])
    locked_overwrites = models.ManyToManyField(DiscordOverwrite, blank=True)
    unlocked_overwrites = models.ManyToManyField(
        DiscordOverwrite, related_name="unlocked_channel_overwrites", blank=True)

    class Meta:
        """Discord Channel Model Meta information."""

        permissions = [
            ("lock_channels", "Can lock or unlock discord channels.")
        ]

        verbose_name = "Discord Channel"
        verbose_name_plural = "Discord Channels"

    def __str__(self) -> str:
        if self.name:
            name = self.name
        else:
            name = f"<Discord Channel {self.id}>"

        if self.type == 0:
            return f"TEXT: {name}"
        elif self.type == 2:
            return f"VOICE: {name}"
        elif self.type == 4:
            return f"CATEGORY: {name}"
        else:
            return name

    @property
    def overwrites(self) -> List[DiscordOverwrite]:
        """Gets all the current overwrites for the channel."""
        api = Client(settings.DISCORD_BOT_TOKEN, api_version=settings.DEFAULT_DISCORD_API_VERSION)
        raw_overwrites = api.get_channel_overwrites(self.id)

        overwrites = []
        for ro in raw_overwrites:
            o = DiscordOverwrite.overwrite_from_dict(ro)
            overwrites.append(o)

        return overwrites

    @property
    def overwrite_dict(self) -> Dict[int, DiscordOverwrite]:
        """Get all the current overwrites for the channel as a dictionary with the user id as the key."""

        o_dict = {}

        overwrites = self.overwrites
        for ov in overwrites:
            o_dict[ov.user_id] = ov

        return o_dict

    def lock(self) -> bool:
        """Lock the channel, only affecting the overwrites in the channel info."""

        logger.debug(f"Locking channel {self.name}({self.id})")

        overwrites = self.overwrite_dict
        for o in self.locked_overwrites.all():
            overwrites[o.user_id] = o

        logger.debug(f"Permission Overwrites: {[o.verbose for o in overwrites.values()]}")

        encoded_overwrites = []
        for k, v in overwrites.items():
            encoded_overwrites.append(v.to_encoded_dict)

        api = Client(settings.DISCORD_BOT_TOKEN, api_version=settings.DEFAULT_DISCORD_API_VERSION)
        api.modify_channel_overwrites(self.id, encoded_overwrites)

        return True

    def unlock(self) -> bool:
        """Unlock the channel, only affecting the overwrites in the channel info."""

        logger.debug(f"Unlocking channel {self.name}({self.id})")

        overwrites = self.overwrite_dict
        for o in self.unlocked_overwrites.all():
            overwrites[o.user_id] = o

        logger.debug(f"Permission Overwrites: {[o.verbose for o in overwrites.values()]}")

        encoded_overwrites = []
        for k, v in overwrites.items():
            encoded_overwrites.append(v.to_encoded_dict)

        api = Client(settings.DISCORD_BOT_TOKEN, api_version=settings.DEFAULT_DISCORD_API_VERSION)
        api.modify_channel_overwrites(self.id, encoded_overwrites)

        return True

# endregion

# region Authentication


def days5():
    return timezone.now() + datetime.timedelta(days=5)


def random_token():
    return secrets.token_urlsafe(42)


class DiscordUser(models.Model):
    """Linking Discord user to website user."""

    id = models.BigIntegerField("Discord ID", primary_key=True)
    discord_username = models.CharField(max_length=100, blank=True)
    discriminator = models.IntegerField(blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, db_index=True)
    access_token = models.CharField(max_length=40, blank=True)
    expiry = models.DateTimeField(blank=True, null=True)
    refresh_token = models.CharField(max_length=40, blank=True)

    class Meta:
        """Meta information for Discord Users."""

        verbose_name = "Discord User"
        verbose_name_plural = "Discord Users"

    def __str__(self) -> str:
        return f"{self.discord_username}#{self.discriminator}"

    def set_tokens(self, access_token, expires_in, refresh_token):
        """Set the user's discord tokens."""

        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expiry = datetime.datetime.now() + datetime.timedelta(seconds=expires_in - 10)
        self.save()


class MagicLink(models.Model):
    token = models.CharField(max_length=64, default=random_token)
    user = models.OneToOneField(User, models.CASCADE)
    expiry = models.DateTimeField(default=days5)
    delete_immediately = models.BooleanField(default=True)

    def link_used(self) -> bool:
        """Returns True if link can still be used, or False if not."""
        if self.delete_immediately:
            self.delete()
            return False

        if self.expiry < timezone.now() + datetime.timedelta(days=1):
            # Only 1 day left, do nothing
            return True

        else:
            self.expiry = timezone.now() + datetime.timedelta(days=1)
            self.save()
            return True

# endregion

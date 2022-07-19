"""


Some inspiration from: https://github.com/Palindrome-Puzzles/2022-hunt/blob/main/hunt/app/models.py
"""

from __future__ import annotations

import string
import os
import random
import datetime
import secrets
import logging

from typing import List, Dict
from pyaccord import DiscordAPIClient

logger = logging.getLogger("common_models.models")

from common_models.common_models_setup import init_django
init_django()

from django.db import models  # noqa: E402
from django.db.models.deletion import CASCADE, PROTECT  # noqa: E402
from django.contrib.auth.models import User, Group  # noqa: E402
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings


SCAVENGER_DIR = "scavenger/"
PUZZLE_DIR = "puzzles/"

FILE_RANDOM_LENGTH = 128


def random_path(instance, filename, base=""):
    _, ext = os.path.splitext(filename)
    rnd = "".join(random.choice(string.ascii_letters + string.digits) for i in range(FILE_RANDOM_LENGTH))
    return base + rnd + ext


def puzzle_path(instance, filename):
    return random_path(instance, filename, SCAVENGER_DIR + PUZZLE_DIR)

# region Scavenger


class Puzzle(models.Model):
    """Puzzles in scavenger"""

    id = models.IntegerField(unique=True, primary_key=True)
    name = models.CharField(max_length=200, unique=True)
    answer = models.CharField(max_length=100)

    enabled = models.BooleanField(default=True)

    puzzle_text = models.CharField("Text", blank=True, max_length=2000)
    puzzle_file = models.FileField(upload_to=puzzle_path, blank=True)
    puzzle_file_display_filename = models.CharField(max_length=256, blank=True)
    puzzle_file_download = models.BooleanField(default=False)
    puzzle_file_is_image = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self: Puzzle) -> str:
        return f"Puzzle: {self.name} [{self.id}]"

    class Meta:
        verbose_name = "Scavenger Puzzle"
        verbose_name_plural = "Scavenger Puzzles"

        permissions = [
            ("guess_scavenger_puzzle", "Can guess for scavenger puzzle")
        ]


# endregion


class Team(models.Model):
    """Model of scavenger team."""

    group = models.OneToOneField(Group, CASCADE, primary_key=True)
    scavenger_team = models.BooleanField(default=True)
    scavenger_finished = models.BooleanField("Finished Scavenger", default=False)

    class Meta:
        verbose_name = "Team"
        verbose_name_plural = "Teams"

    def __str__(self) -> str:
        return self.group.name

# region Discord


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
        api = DiscordAPIClient(credentials.BOT_TOKEN, api_version=settings.DEFAULT_DISCORD_API_VERSION)
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

        api = DiscordAPIClient(credentials.BOT_TOKEN, api_version=settings.DEFAULT_DISCORD_API_VERSION)
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

        api = DiscordAPIClient(credentials.BOT_TOKEN, api_version=settings.DEFAULT_DISCORD_API_VERSION)
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
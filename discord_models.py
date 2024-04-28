from django.db import models
from collections import namedtuple
import pyaccord
from pyaccord import Client
from pyaccord.invite import Invite
from pyaccord.channel import TextChannel
from pyaccord.guild import Guild
from pyaccord.permissions import Permissions
from typing import Iterable, List, Dict, Optional
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.deletion import CASCADE
from django.conf import settings
from django.contrib.auth.models import User, Group
import datetime
import logging
from django_unixdatetimefield import UnixDateTimeField

logger = logging.getLogger("common_models.discord_models")

try:
    from credentials import GUILD_ID
except (ModuleNotFoundError, ImportError):
    logger.warn("Could not import GUILD_ID from credentials")
    GUILD_ID = 0


def get_client() -> Client:
    return Client(settings.DISCORD_BOT_TOKEN, api_version=settings.DEFAULT_DISCORD_API_VERSION)


DiscordGuildUpdateGuildResult = namedtuple("DiscordGuildUpdatedGuildResult", [
                                           "num_added", "num_existing_updated",
                                           "num_existing_not_updated", "num_removed"])


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
                role = DiscordRole.objects.get(role_id=self.user_id)
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
    def overwrite_from_dict(d: dict):
        """Create a DiscordOverwrite object from the json encoded response dictionary."""
        return DiscordOverwrite(
            user_id=int(d["id"]),
            type=d["type"],
            allow=int(d["allow"]),
            deny=int(d["deny"])
        )


class DiscordRole(models.Model):
    """Relates a Django group to a discord role."""

    role_id = models.PositiveBigIntegerField("Discord Role ID", primary_key=True)
    group_id = models.ForeignKey(Group, CASCADE)
    secondary_group_id = models.ForeignKey(Group, CASCADE, null=True, blank=True, related_name="secondary_group")

    @property
    def group(self) -> Group:
        return self.group_id

    @property
    def secondary_group(self) -> Group:
        return self.secondary_group_id

    def compute_name(self) -> str:
        if self.secondary_group_id is None:
            return self.group_id.name
        return self.group_id.name + " " + self.secondary_group_id.name

    def rename(self):
        client = get_client()
        guild = DiscordGuild.objects.all().first()
        client.rename_role(guild.id, self.role_id, self.compute_name())

    class Meta:
        """Meta information for Discord roles."""

        verbose_name = "Discord Role"
        verbose_name_plural = "Discord Roles"

    def __str__(self) -> str:
        if self.secondary_group_id is not None:
            return self.group_id.name + " - " + self.secondary_group_id.name
        else:
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
            ("create_role", "Allows a user to create discord roles"),
            ("create_channel", "Allows a user to create discord channels"),
            ("spirit_on_duty", "Allows a user to mark themselves as the spirit on duty")
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

        client = Client(settings.DISCORD_BOT_TOKEN, api_version=settings.DEFAULT_DISCORD_API_VERSION)

        client.delete_guild(self.id)

        self.deleted = True
        self.save()

    def create_channel(self, name: str, category: int, is_category: bool = False):
        client = get_client()
        return client.create_channel(name, category, self.id, is_category)

    def create_invite(self, *, unique: Optional[bool] = None, max_uses: Optional[int] = None) -> Invite:

        client = Client(settings.DISCORD_BOT_TOKEN, api_version=settings.DEFAULT_DISCORD_API_VERSION)

        guild = client.get_guild(self.id)
        if not guild:
            raise Exception("No guild exists with the id")

        for ch in guild.channels:
            if isinstance(ch, TextChannel):
                return ch.create_invite(max_uses=max_uses, unique=unique)

        raise Exception("Could not find a valid text channel to invite to.")

    def create_role(
            self, name: Optional[str] = None, *, permissions: Optional[Iterable[Permissions]] = None,
            position: Optional[int] = None, color: Optional[int] = None) -> pyaccord.Role:

        client = get_client()

        role = client.create_guild_role(self.id, name=name, permissions=permissions, color=color)
        if position is not None:
            client.set_guild_role_position(self.id, role.id, position)
        return role

    def get_role(self, name):
        client = get_client()
        roles = client.get_guild_roles(self.id)
        for role in roles:
            if role.name == name:
                return role
        return None

    def change_nick(self, user: int, nickname: Optional[str] = None):
        client = get_client()
        client.change_user_nickname(self.id, user, nickname=nickname)

    def add_role_to_member(self, discord_member_id: int, discord_role: DiscordRole | int) -> None:

        client = get_client()

        return client.add_role_to_guild_member(self.id, discord_member_id, discord_role)

    @staticmethod
    def create_new_guild(name: str):
        """Creates a new guild using the discord api, saves it to the database and returns the database object."""

        client = Client(settings.DISCORD_BOT_TOKEN, api_version=settings.DEFAULT_DISCORD_API_VERSION)

        pyaccord_guild = client.create_guild(name)

        guild = DiscordGuild(pyaccord_guild=pyaccord_guild)

        guild.save()

        return guild

    @staticmethod
    def scan_and_update_guilds() -> DiscordGuildUpdateGuildResult:
        """Returns (num_added, num_existing_updated, num_existing_not_updated, num_removed)"""

        client = Client(settings.DISCORD_BOT_TOKEN, api_version=settings.DEFAULT_DISCORD_API_VERSION)

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


class DiscordChannel(models.Model):
    """Discord Channel Object."""

    id = models.PositiveBigIntegerField("Discord Channel ID", primary_key=True)
    name = models.CharField("Discord Channel Name", max_length=100, unique=False, blank=True, default="")
    tags = models.ManyToManyField(ChannelTag, blank=True)
    team = models.ForeignKey('Team', blank=True, null=True, on_delete=CASCADE)
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
            ("lock_channels", "Can lock or unlock discord channels."),
            ("purge_channels", "Can purge a discord channel of all messages")
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
        if raw_overwrites:
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

    @staticmethod
    def updates_channels() -> List:
        ChannelTag.objects.get_or_create(name="MANAGEMENT_UPDATES_CHANNEL")

        return list(DiscordChannel.objects.filter(tags__name="MANAGEMENT_UPDATES_CHANNEL"))

    @staticmethod
    def send_to_updates_channels(content) -> None:
        for ch in DiscordChannel.updates_channels():
            ch.send(content=content)

    def compute_name(self):
        if self.team is None:
            print("1-"+self.name)
            return self.name
        else:
            if self.type == 0:
                tags = ""
                for t in self.tags.all():
                    tags += "-" + t.name
                return self.team.discord_name + tags
            elif self.type == 4:
                return self.team.display_name

    def rename(self):
        self.rename_name(self.compute_name())

    def rename_name(self, name: str):
        api = get_client()
        api.set_channel_name(self.id, name)
        self.name = name
        self.save()

    def send(self, content: str):
        """Sends a message to the channel."""

        api = get_client()
        return api.send_channel_message(self.id, content=content)

    def lock(self) -> bool:
        """Lock the channel, only affecting the overwrites in the channel info."""

        logger.info(f"Locking channel {self.name}({self.id})")

        overwrites = self.overwrite_dict
        for o in self.locked_overwrites.all():
            overwrites[o.user_id] = o

        logger.info(f"Permission Overwrites: {[o.verbose for o in overwrites.values()]}")

        encoded_overwrites = []
        for k, v in overwrites.items():
            encoded_overwrites.append(v.to_encoded_dict)

        api = Client(settings.DISCORD_BOT_TOKEN, api_version=settings.DEFAULT_DISCORD_API_VERSION)
        api.modify_channel_overwrites(self.id, encoded_overwrites)

        return True

    def unlock(self) -> bool:
        """Unlock the channel, only affecting the overwrites in the channel info."""

        logger.info(f"Unlocking channel {self.name}({self.id})")

        overwrites = self.overwrite_dict
        for o in self.unlocked_overwrites.all():
            overwrites[o.user_id] = o

        logger.info(f"Permission Overwrites: {[o.verbose for o in overwrites.values()]}")

        encoded_overwrites = []
        for k, v in overwrites.items():
            encoded_overwrites.append(v.to_encoded_dict)

        api = Client(settings.DISCORD_BOT_TOKEN, api_version=settings.DEFAULT_DISCORD_API_VERSION)
        api.modify_channel_overwrites(self.id, encoded_overwrites)

        return True


class RoleInvite(models.Model):
    link = models.CharField("Link", max_length=40, primary_key=True)
    role = models.CharField("Role IDs", max_length=200)
    nick = models.CharField("Nickname", max_length=40, null=True, default=None)
    user = models.ForeignKey("UserDetails", CASCADE, null=True)

    class Meta:
        """Discord Role Invite Model Meta information."""

        permissions = [
            ("create_invite", "Can create invites to the discord server")
        ]

        verbose_name = "Role Invite"
        verbose_name_plural = "Role Invites"


class DiscordMessage(models.Model):
    type = models.CharField("Type", max_length=64)
    id = models.BigIntegerField("Channel ID", primary_key=True)


class DiscordUser(models.Model):
    """Linking Discord user to website user."""

    id = models.BigIntegerField("Discord ID", primary_key=True)
    discord_username = models.CharField(max_length=500, blank=True)
    discriminator = models.IntegerField(blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, db_index=True)
    access_token = models.CharField(max_length=40, blank=True)
    expiry = UnixDateTimeField(blank=True, null=True)
    refresh_token = models.CharField(max_length=40, blank=True)

    class Meta:
        """Meta information for Discord Users."""

        verbose_name = "Discord User"
        verbose_name_plural = "Discord Users"
        permissions = [
            ("view_discord_nicks", "Can view Discord info for users"),
            ("manage_discord_nicks", "Can manage Discord info for users")
        ]

    def __str__(self) -> str:
        return f"{self.discord_username}#{self.discriminator}"

    def set_tokens(self, access_token, expires_in, refresh_token):
        """Set the user's discord tokens."""

        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expiry = datetime.datetime.now() + datetime.timedelta(seconds=expires_in - 10)
        self.save()

    def kick_user(self):
        """Kick user from the default guild"""

        client = get_client()

        client.remove_guild_member(user_id=self.id, guild_id=GUILD_ID)

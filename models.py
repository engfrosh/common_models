"""


Some inspiration from: https://github.com/Palindrome-Puzzles/2022-hunt/blob/main/hunt/app/models.py
"""

from __future__ import annotations
from collections import namedtuple
from io import BytesIO

import string
import os
import random
import datetime
import secrets
import logging
import qrcode
import qrcode.constants
import qrcode.image.svg
from qrcode.image.styledpil import StyledPilImage

from typing import Iterable, List, Dict, Optional, Tuple, Union
from engfrosh_site.settings import DEFAULT_DISCORD_API_VERSION

import pyaccord
from pyaccord import Client
from pyaccord.invite import Invite
from pyaccord.channel import TextChannel
from pyaccord.guild import Guild
from pyaccord.permissions import Permissions

logger = logging.getLogger("common_models.models")

from common_models.common_models_setup import init_django  # noqa: E402
init_django()

from django.db import models  # noqa: E402
from django.db.models.deletion import CASCADE, PROTECT, SET_NULL  # noqa: E402
from django.contrib.auth.models import User, Group  # noqa: E402
from django.utils import timezone  # noqa: E402
from django.core.exceptions import ObjectDoesNotExist  # noqa: E402
from django.conf import settings  # noqa: E402
from django.core.files import File


SCAVENGER_DIR = "scavenger/"
PUZZLE_DIR = "puzzles/"
PUZZLE_VERIFICATION_DIR = "verification_photos/"
QR_CODE_DIR = "qr_codes/"

FILE_RANDOM_LENGTH = 128

PUZZLE_SECRET_ID_LENGTH = 16

# region Database Setup


def initialize_database() -> None:
    ChannelTag.objects.get_or_create(name="SCAVENGER_MANAGEMENT_UPDATES_CHANNEL")
    ChannelTag.objects.get_or_create(name="TRADE_UP_MANAGEMENT_UPDATES_CHANNEL")
    BooleanSetting.objects.get_or_create(id="SCAVENGER_ENABLED")
    BooleanSetting.objects.get_or_create(id="TRADE_UP_ENABLED")

# endregion


def get_client() -> Client:
    return Client(settings.DISCORD_BOT_TOKEN, api_version=DEFAULT_DISCORD_API_VERSION)


def random_path(instance, filename, base="", *, length: Optional[int] = None):
    if length is None:
        length = FILE_RANDOM_LENGTH
    _, ext = os.path.splitext(filename)
    rnd = "".join(random.choice(string.ascii_letters + string.digits) for i in range(length))
    return base + rnd + ext


def puzzle_path(instance, filename):
    return random_path(instance, filename, SCAVENGER_DIR + PUZZLE_DIR)


def qr_code_path(instance, filename):
    return random_path(instance, filename, SCAVENGER_DIR + QR_CODE_DIR)


def random_puzzle_secret_id():
    return "".join(random.choice(string.ascii_lowercase) for i in range(PUZZLE_SECRET_ID_LENGTH))


def hint_path(instance, filename):
    return random_path(instance, filename, SCAVENGER_DIR + "hints/")


def question_path(instance, filename):
    return puzzle_path(instance, filename)

# region Scavenger


class PuzzleStream(models.Model):
    """Puzzle streams in scavenger"""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    enabled = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name}"

    class Meta:
        verbose_name = "Scavenger Puzzle Stream"
        verbose_name_plural = "Scavenger Puzzle Streams"

    @property
    def _all_puzzles_qs(self) -> models.QuerySet:
        return Puzzle.objects.filter(stream=self.id).order_by("order")

    @property
    def all_puzzles(self) -> List[Puzzle]:
        return list(self._all_puzzles_qs)

    @property
    def _all_enabled_puzzles_qs(self) -> models.QuerySet:
        return Puzzle.objects.filter(stream=self.id, enabled=True).order_by("order")

    @property
    def all_enabled_puzzles(self) -> List[Puzzle]:
        """Returns a list of enabled puzzles in order they are to be completed."""
        return list(self._all_enabled_puzzles_qs)

    @property
    def first_enabled_puzzle(self) -> Optional[Puzzle]:
        """Returns the first enabled puzzle for the stream if it exists."""

        return self._all_enabled_puzzles_qs.first()

    def get_next_enabled_puzzle(self, puzzle: Puzzle) -> Optional[Puzzle]:
        """Returns the next puzzle, returns None if there are no more Puzzles, ie stream completed."""

        return self._all_enabled_puzzles_qs.filter(order__gt=puzzle.order).order_by("order").first()


class Puzzle(models.Model):
    """Puzzles in scavenger"""

    id = models.AutoField(unique=True, primary_key=True)
    name = models.CharField(max_length=200, unique=True)

    answer = models.CharField(max_length=100)
    require_photo_upload = models.BooleanField(default=settings.DEFAULT_SCAVENGER_PUZZLE_REQUIRE_PHOTO_UPLOAD)

    secret_id = models.SlugField(max_length=64, unique=True, default=random_puzzle_secret_id)

    enabled = models.BooleanField(default=True)

    order = models.DecimalField(max_digits=8, decimal_places=3)
    stream = models.ForeignKey(PuzzleStream, on_delete=PROTECT)

    qr_code = models.ImageField(upload_to=qr_code_path, blank=True)

    puzzle_text = models.CharField("Text", blank=True, max_length=2000)
    puzzle_file = models.FileField(upload_to=puzzle_path, blank=True)
    puzzle_file_display_filename = models.CharField(max_length=256, blank=True)
    puzzle_file_download = models.BooleanField(default=False)
    puzzle_file_is_image = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # teams = models.ManyToManyField(Team, through="TeamPuzzleActivity")

    class Meta:
        verbose_name = "Scavenger Puzzle"
        verbose_name_plural = "Scavenger Puzzles"

        permissions = [
            ("guess_scavenger_puzzle", "Can guess for scavenger puzzle"),
            ("manage_scav", "Can manage scav")
        ]

        unique_together = [["order", "stream"]]

    def __str__(self: Puzzle) -> str:
        return f"Puzzle: {self.name} [{self.id}]"

    def puzzle_activity_from_team(self, team: Team) -> Optional[TeamPuzzleActivity]:
        try:
            return TeamPuzzleActivity.objects.get(puzzle=self.id, team=team.id)
        except TeamPuzzleActivity.DoesNotExist:
            return None

    def is_viewable_for_team(self, team: Team) -> bool:
        if not self.enabled:
            return False
        return TeamPuzzleActivity.objects.filter(puzzle=self.id, team=team.id).exists()

    def is_active_for_team(self, team: Team) -> bool:
        if not self.enabled:
            return False

        pa: Union[TeamPuzzleActivity, None] = TeamPuzzleActivity.objects.get(puzzle=self.id, team=team.id)
        if pa:
            return pa.is_active

        else:
            return False

    def is_completed_for_team(self, team: Team) -> bool:
        if not self.enabled:
            return False

        pa: Union[TeamPuzzleActivity, None] = TeamPuzzleActivity.objects.get(puzzle=self.id, team=team.id)
        if pa:
            return pa.is_completed

        else:
            return False

    def requires_verification_photo_by_team(self, team: Team) -> bool:
        if not self.enabled:
            return False

        pa = self.puzzle_activity_from_team(team)
        if not pa:
            return False

        return pa.requires_verification_photo_upload

    def check_team_guess(self, team: Team, guess: str) -> Tuple[bool, bool, Optional[Puzzle], bool]:
        """
        Checks if a team's guess is correct. First is if correct, second if stream complete, 
        third the new puzzle if unlocked, fourth if a verification picture is required.

        Will move team to next question if it is correct or complete scavenger if appropriate.
        """

        activity = TeamPuzzleActivity.objects.get(team=team.id, puzzle=self.id)

        # Create a guess object
        PuzzleGuess(value=guess, activity=activity).save()

        # Check the answer
        correct = self.answer.lower() == guess.lower()

        if not correct:
            return (correct, False, None, False)

        # Mark the question as correct
        activity.mark_completed()

        ChannelTag.objects.get_or_create(name="SCAVENGER_MANAGEMENT_UPDATES_CHANNEL")

        discord_channels = DiscordChannel.objects.filter(tags__name="SCAVENGER_MANAGEMENT_UPDATES_CHANNEL")

        # If verification is required,
        if self.require_photo_upload:

            for ch in discord_channels:
                ch.send(f"{team.display_name} has completed question {self.name}, awaiting a photo upload.")

            return (correct, False, None, True)

        # Otherwise if correct check if done scavenger and if not increment question
        next_puzzle = self.stream.get_next_enabled_puzzle(self)

        if not next_puzzle:
            team.check_if_finished_scavenger()

            for ch in discord_channels:
                ch.send(f"{team.display_name} has completed scavenger stream {self.stream.name}, awaiting a photo upload.")

            return (correct, True, None, False)

        TeamPuzzleActivity(team=team, puzzle=next_puzzle).save()
        for ch in discord_channels:
            ch.send(f"{team.display_name} has completed puzzle {self.name}, moving on to puzzle {next_puzzle.name}")

        return (correct, False, next_puzzle, False)

    def _generate_qr_code(self) -> None:

        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
        qr.add_data(
            "https://" + settings.ALLOWED_HOSTS[0] + "/scavenger/puzzle/" + self.secret_id + "?answer=" + self.answer)
        qr.make(fit=True)

        blob = BytesIO()
        STYLE_IMAGE_PATH = "SpiritX.png"
        USE_IMAGE = True
        if USE_IMAGE:
            img = qr.make_image(image_factory=StyledPilImage, embeded_image_path=STYLE_IMAGE_PATH)
        else:
            img = qr.make_image()
        img.save(blob, "PNG")
        self.qr_code.save("QRCode.png", File(blob))
        self.save()


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

class BooleanSetting(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    value = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Boolean Setting"
        verbose_name_plural = "Boolean Settings"

    def __str__(self) -> str:
        return f"<Setting {self.id}: {self.value} >"


class Team(models.Model):
    """Model of frosh team."""

    # @staticmethod
    # def initialize_all_team_scavenger_questions():
    #     for t in Team.objects.all():

    display_name = models.CharField("Team Name", max_length=64, unique=True)
    group = models.OneToOneField(Group, CASCADE, primary_key=True)

    scavenger_team = models.BooleanField(default=True)
    scavenger_finished = models.BooleanField("Finished Scavenger", default=False)
    scavenger_locked_out_until = models.DateTimeField(blank=True, null=True, default=None)
    scavenger_enabled_for_team = models.BooleanField(default=True)

    trade_up_team = models.BooleanField(default=True)
    trade_up_enabled_for_team = models.BooleanField(default=True)

    puzzles = models.ManyToManyField(Puzzle, through="TeamPuzzleActivity")

    coin_amount = models.BigIntegerField("Coin Amount", default=0)
    color = models.PositiveIntegerField("Hex Color Code", null=True, blank=True, default=None)

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

    @staticmethod
    def from_user(user: User) -> Optional[Team]:
        teams = Team.objects.filter(group__in=user.groups.all())
        if not teams:
            return None
        return teams[0]

    @property
    def id(self) -> int:
        return self.group.id

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

    @property
    def active_puzzles(self) -> List[Puzzle]:
        active_puzzle_activities = filter(TeamPuzzleActivity._is_active,
                                          TeamPuzzleActivity.objects.filter(team=self.group.id))
        return [apa.puzzle for apa in active_puzzle_activities]

    @property
    def completed_puzzles(self) -> List[Puzzle]:
        completed_puzzle_activities = filter(TeamPuzzleActivity._is_completed,
                                             TeamPuzzleActivity.objects.filter(team=self.group.id))
        return [cpa.puzzle for cpa in completed_puzzle_activities]

    @property
    def verified_puzzles(self) -> List[Puzzle]:
        verified_puzzle_activities = filter(TeamPuzzleActivity._is_verified,
                                            TeamPuzzleActivity.objects.filter(team=self.id))
        return [vpa.puzzle for vpa in verified_puzzle_activities]

    @property
    def completed_puzzles_awaiting_verification(self) -> List[Puzzle]:
        return [cpav.puzzle for cpav in filter(TeamPuzzleActivity._is_awaiting_verification,
                                               TeamPuzzleActivity.objects.filter(team=self.id))]

    @property
    def all_puzzles(self) -> List[Puzzle]:
        return [tpa.puzzle for tpa in self.puzzle_activities]

    @property
    def _puzzle_activities_qs(self) -> models.QuerySet:
        return TeamPuzzleActivity.objects.filter(team=self.id)

    @property
    def puzzle_activities(self) -> List[TeamPuzzleActivity]:
        return list(self._puzzle_activities_qs)

    @property
    def completed_puzzles_requiring_photo_upload(self) -> List[Puzzle]:
        return [pa.puzzle for pa in filter(TeamPuzzleActivity._requires_verification_photo_upload,
                                           self.puzzle_activities)]

    # @property
    # def latest_puzzle_activities(self) -> List[TeamPuzzleActivity]:

    @property
    def scavenger_enabled(self) -> bool:
        """Returns a bool if scav is enabled for the team."""

        return BooleanSetting.objects.get_or_create(
            id="SCAVENGER_ENABLED")[0].value and self.scavenger_enabled_for_team and self.scavenger_team

    @property
    def trade_up_enabled(self) -> bool:
        """Returns a bool if trade up is enabled for the team."""

        return BooleanSetting.objects.get_or_create(
            id="TRADE_UP_ENABLED")[0].value and self.trade_up_enabled_for_team and self.trade_up_team

    def enable_scavenger_for_team(self) -> None:

        self.scavenger_enabled_for_team = True
        self.save()

    def disable_scavenger_for_team(self) -> None:

        self.scavenger_enabled_for_team = False
        self.save()

    def enable_trade_up_for_team(self) -> None:
        self.trade_up_enabled_for_team = True
        self.save()

    def disable_trade_up_for_team(self) -> None:
        self.trade_up_enabled_for_team = False
        self.save()

    def reset_scavenger_progress(self) -> None:
        """Reset the team's current scavenger question to the first enabled question."""

        # Eliminate all progress
        TeamPuzzleActivity.objects.filter(team=self.id).delete()

        # Unlock all questions
        streams = PuzzleStream.objects.filter(enabled=True)

        for s in streams:
            puz = s.first_enabled_puzzle

            if puz:
                pa = TeamPuzzleActivity(team=self, puzzle=puz)

                pa.save()

        self.scavenger_finished = False
        self.scavenger_locked_out_until = None
        self.save()

        # If hints are added they also need to be reset here

    def check_if_finished_scavenger(self) -> bool:
        if self.scavenger_finished:
            return True

        all_streams = PuzzleStream.objects.filter(enabled=True)
        for stream in all_streams:
            all_stream_puzzles = stream.all_enabled_puzzles
            for puz in all_stream_puzzles:
                try:
                    if not TeamPuzzleActivity.objects.get(team=self.id, puzzle=puz.id).is_verified:
                        return False
                except TeamPuzzleActivity.DoesNotExist:
                    return False

        self.scavenger_finished = True
        self.save()
        return True

    def refresh_scavenger_progress(self) -> None:
        """Moves team along if verified on a puzzle or a puzzle has been disabled."""

        if self.scavenger_finished:
            return

        # Get all streams
        streams = PuzzleStream.objects.filter(enabled=True)
        for s in streams:

            # Get puzzles in stream in reverse order
            puzzles = s._all_puzzles_qs.reverse()
            for puz in puzzles:

                # If the team has gotten to the puzzle
                if self._puzzle_activities_qs.filter(puzzle=puz.id).exists():

                    puz_disabled = not puz.enabled
                    puz_verified = self._puzzle_activities_qs.filter(puzzle=puz.id).first().is_verified

                    # If the puzzle is now disabled or if the puzzle is now verified
                    if puz_disabled or puz_verified:
                        # Move team to next puzzle
                        next_puzzle = s.get_next_enabled_puzzle(puzzle=puz)

                        if not next_puzzle:
                            if self.check_if_finished_scavenger():
                                return

                        TeamPuzzleActivity(team=self, puzzle=next_puzzle).save()

        return

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


def _puzzle_verification_photo_upload_path(instance, filename) -> str:
    return random_path(instance, filename, PUZZLE_VERIFICATION_DIR)


class VerificationPhoto(models.Model):
    """Stores references to all the uploaded photos for scavenger puzzle verification."""

    datetime = models.DateTimeField(auto_now=True)
    photo = models.ImageField(upload_to=_puzzle_verification_photo_upload_path)
    approved = models.BooleanField(default=False)

    def approve(self) -> None:
        self.approved = True
        self.save()
        TeamPuzzleActivity.objects.get(verification_photo=self).team.refresh_scavenger_progress()


class TeamTradeUpActivity(models.Model):

    team = models.ForeignKey(Team, on_delete=CASCADE)
    verification_photo = models.ForeignKey(VerificationPhoto, on_delete=SET_NULL, null=True, blank=True, default=None)
    entered_at = models.DateTimeField(auto_now=True)

    class Meta:

        verbose_name = "Team Trade Up Activity"
        verbose_name_plural = "Team Trade Up Activities"


class TeamPuzzleActivity(models.Model):
    """Relates teams to the puzzles they have active and have completed."""

    team = models.ForeignKey(Team, on_delete=CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=CASCADE)
    puzzle_start_at = models.DateTimeField(auto_now=True)
    puzzle_completed_at = models.DateTimeField(null=True, blank=True, default=None)
    verification_photo = models.ForeignKey(VerificationPhoto, on_delete=SET_NULL, null=True, blank=True, default=None)
    locked_out_until = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:

        verbose_name = "Team Puzzle Activity"
        verbose_name_plural = "Team Puzzle Activities"

        unique_together = [["team", "puzzle"]]

    def __str__(self) -> str:
        return f"{self.team.display_name} on puzzle: {self.puzzle.name}"

    def _is_active(self) -> bool:
        if self.puzzle_completed_at:
            return False
        return self.puzzle.enabled

    def _is_completed(self) -> bool:
        if self.puzzle_completed_at:
            return self.puzzle.enabled
        return False

    def _is_verified(self) -> bool:
        if self.verification_photo and self.verification_photo.approved or not self.puzzle.require_photo_upload:
            return True

        return False

    def _is_awaiting_verification(self) -> bool:
        if self.verification_photo and not self.verification_photo.approved:
            return True

        return False

    def _requires_verification_photo_upload(self) -> bool:
        if self.is_completed and not self.verification_photo and self.puzzle.require_photo_upload:
            return True

        return False

    def mark_completed(self) -> None:
        if self.puzzle_completed_at:
            raise Exception("Puzzle already completed")

        self.puzzle_completed_at = datetime.datetime.now()
        self.save()

    @property
    def is_active(self) -> bool:
        return self._is_active()

    @property
    def is_completed(self) -> bool:
        return self._is_completed()

    @property
    def is_verified(self) -> bool:
        return self._is_verified()

    @property
    def is_awaiting_verification(self) -> bool:
        return self._is_awaiting_verification()

    @property
    def requires_verification_photo_upload(self) -> bool:
        return self._requires_verification_photo_upload()


class PuzzleGuess(models.Model):
    """Stores all the guesses for scavenger."""

    datetime = models.DateTimeField(auto_now=True)
    value = models.CharField(max_length=100)
    activity = models.ForeignKey(TeamPuzzleActivity, on_delete=CASCADE)

    class Meta:

        verbose_name = "Puzzle Guess"
        verbose_name_plural = "Puzzle Guesses"


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

    def create_invite(self, *, unique: Optional[bool] = None, max_uses: Optional[int] = None) -> Invite:

        client = Client(settings.DISCORD_BOT_TOKEN, api_version=DEFAULT_DISCORD_API_VERSION)

        guild = client.get_guild(self.id)
        if not guild:
            raise Exception("No guild exists with the id")

        for ch in guild.channels:
            if isinstance(ch, TextChannel):
                return ch.create_invite(max_uses=max_uses, unique=unique)

        raise Exception("Could not find a valid text channel to invite to.")

    def create_role(
            self, name: Optional[str] = None, *, permissions: Optional[Iterable[Permissions]] = None) -> pyaccord.Role:

        client = get_client()

        role = client.create_guild_role(self.id, name=name, permissions=permissions)

        return role

    def add_role_to_member(self, discord_member_id: int, discord_role: DiscordRole | int) -> None:

        client = get_client()

        return client.add_role_to_guild_member(self.id, discord_member_id, discord_role)

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


class DiscordRole(models.Model):
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

    @staticmethod
    def scavenger_updates_channels() -> List[DiscordChannel]:
        ChannelTag.objects.get_or_create(name="SCAVENGER_MANAGEMENT_UPDATES_CHANNEL")

        return list(DiscordChannel.objects.filter(tags__name="SCAVENGER_MANAGEMENT_UPDATES_CHANNEL"))

    @staticmethod
    def send_to_scavenger_updates_channels(content) -> None:
        for ch in DiscordChannel.scavenger_updates_channels():
            ch.send(content=content)

    def send(self, content: str):
        """Sends a message to the channel."""

        api = get_client()
        return api.send_channel_message(self.id, content=content)

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

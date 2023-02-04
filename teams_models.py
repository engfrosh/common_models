from django.db import models
from django.utils import timezone
import datetime
import logging
from django.db.models.deletion import CASCADE
from typing import List, Optional
from django.db.utils import IntegrityError
from django.contrib.auth.models import User, Group
from django_unixdatetimefield import UnixDateTimeField

import common_models.models as md

logger = logging.getLogger("common_models.teams_models")


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


class Team(models.Model):
    """Model of frosh team."""

    # @staticmethod
    # def initialize_all_team_scavenger_questions():
    #     for t in Team.objects.all():

    display_name = models.CharField("Team Name", max_length=64, unique=True)
    group = models.OneToOneField(Group, CASCADE, primary_key=True)

    scavenger_team = models.BooleanField(default=True)
    scavenger_finished = models.BooleanField("Finished Scavenger", default=False)
    scavenger_locked_out_until = UnixDateTimeField(blank=True, null=True, default=None)
    scavenger_enabled_for_team = models.BooleanField(default=True)

    trade_up_team = models.BooleanField(default=True)
    trade_up_enabled_for_team = models.BooleanField(default=True)

    puzzles = models.ManyToManyField('Puzzle', through="TeamPuzzleActivity")

    coin_amount = models.BigIntegerField("Coin Amount", default=0)
    color = models.PositiveIntegerField("Hex Color Code", null=True, blank=True, default=None)

    # hint_cooldown_until = UnixDateTimeField("Hint Cooldown Until", blank=True, null=True)
    # last_hint = models.ForeignKey(Hint, blank=True, on_delete=PROTECT, null=True)
    # last_hint_time = UnixDateTimeField(blank=True, null=True)
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
    def from_user(user: User) -> Optional:
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
    def active_puzzles(self) -> List:
        for perm in self.group.permissions.all():
            if perm.codename == "bypass_scav_rules":
                return list(md.Puzzle.objects.filter(enabled=True).order_by("order").all())
        active_puzzle_activities = filter(md.TeamPuzzleActivity._is_active,
                                          self._puzzle_activities_qs)
        return [apa.puzzle for apa in active_puzzle_activities]

    @property
    def completed_puzzles(self) -> List:
        completed_puzzle_activities = filter(md.TeamPuzzleActivity._is_completed,
                                             self._puzzle_activities_qs)
        return [cpa.puzzle for cpa in completed_puzzle_activities]

    @property
    def verified_puzzles(self) -> List:
        verified_puzzle_activities = filter(md.TeamPuzzleActivity._is_completed,
                                            filter(md.TeamPuzzleActivity._is_verified,
                                                   self._puzzle_activities_qs))
        return [vpa.puzzle for vpa in verified_puzzle_activities]

    @property
    def completed_puzzles_awaiting_verification(self) -> List:
        return [cpav.puzzle for cpav in filter(md.TeamPuzzleActivity._is_awaiting_verification,
                                               self._puzzle_activities_qs)]

    @property
    def all_puzzles(self) -> List:
        return [tpa.puzzle for tpa in self.puzzle_activities]

    @property
    def _puzzle_activities_qs(self) -> models.QuerySet:
        return md.TeamPuzzleActivity.objects.filter(team=self.id).order_by("puzzle__order")

    @property
    def puzzle_activities(self) -> List:
        return list(self._puzzle_activities_qs)

    @property
    def completed_puzzles_requiring_photo_upload(self) -> List:
        return [pa.puzzle for pa in filter(md.TeamPuzzleActivity._requires_verification_photo_upload,
                                           self.puzzle_activities)]

    # @property
    # def latest_puzzle_activities(self) -> List[TeamPuzzleActivity]:

    @property
    def scavenger_locked(self) -> bool:
        if self.scavenger_locked_out_until is None:
            return False
        now = timezone.now()
        if self.scavenger_locked_out_until <= now:
            self.scavenger_locked_out_until = None
            self.save()
            return False
        return True

    def scavenger_lock(self, minutes) -> None:
        self.scavenger_locked_out_until = timezone.now() + timezone.timedelta(minutes=minutes)
        self.save()

    @property
    def scavenger_unlock(self) -> None:
        self.scavenger_locked_out_until = None
        self.save()

    @property
    def lockout_remaining(self) -> int:
        if not self.scavenger_locked:
            return 0
        return self.scavenger_locked_out_until - timezone.now()

    @property
    def scavenger_enabled(self) -> bool:
        """Returns a bool if scav is enabled for the team."""
        return md.BooleanSetting.objects.get_or_create(
            id="SCAVENGER_ENABLED")[0].value and self.scavenger_enabled_for_team and \
            self.scavenger_team and not self.scavenger_locked

    @property
    def trade_up_enabled(self) -> bool:
        """Returns a bool if trade up is enabled for the team."""

        return md.BooleanSetting.objects.get_or_create(
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
        md.TeamPuzzleActivity.objects.filter(team=self.id).delete()

        # Unlock all questions
        streams = md.PuzzleStream.objects.filter(enabled=True)

        for s in streams:
            puz = s.first_enabled_puzzle

            if puz:
                pa = md.TeamPuzzleActivity(team=self, puzzle=puz)

                pa.save()

        self.scavenger_finished = False
        self.scavenger_locked_out_until = None
        self.save()

        # If hints are added they also need to be reset here

    def check_if_finished_scavenger(self) -> bool:
        if self.scavenger_finished:
            return True

        all_streams = md.PuzzleStream.objects.filter(enabled=True)
        for stream in all_streams:
            all_stream_puzzles = stream.all_enabled_puzzles
            for puz in all_stream_puzzles:
                try:
                    if not md.TeamPuzzleActivity.objects.get(team=self.id, puzzle=puz.id).is_verified:
                        return False
                except md.TeamPuzzleActivity.DoesNotExist:
                    return False

        self.scavenger_finished = True
        self.save()
        return True

    def refresh_scavenger_progress(self) -> None:
        """Moves team along if verified on a puzzle or a puzzle has been disabled."""

        logger.debug(f"Refreshing scavenger progress for team {self}")

        if self.scavenger_finished:
            return

        # Get all streams
        streams = md.PuzzleStream.objects.filter(enabled=True)
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

                        try:
                            md.TeamPuzzleActivity(team=self, puzzle=next_puzzle).save()
                        except IntegrityError as e:
                            logger.exception("Integrity error trying to set team to next question")
                            raise e

        return

    def remove_blocks(self):
        """Remove lockouts and cooldowns."""

        self.locked_out_until = None
        #     self.hint_cooldown_until = None

        self.save()
        raise True

    def lockout(self, duration: Optional[datetime.timedelta] = None) -> None:
        """Lockout team for seconds."""

        if duration is None:
            duration = datetime.timedelta(minutes=15)

        now = timezone.now()
        until = now + duration
        self.locked_out_until = until
        self.save()
        raise True

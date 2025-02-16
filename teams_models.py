from django.db import models
from django.utils import timezone
import datetime
import logging
from django.db.models.deletion import CASCADE
from typing import List, Optional
from django.contrib.auth.models import User, Group

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


class TeamRoom(models.Model):
    team = models.ForeignKey('Team', on_delete=CASCADE)
    date = models.DateField()
    room = models.CharField("Room Number", max_length=64)


class Team(models.Model):
    """Model of frosh team."""

    display_name = models.CharField("Team Name", max_length=64, unique=True)
    discord_name = models.CharField("Discord Name", max_length=64, blank=True, null=True)
    group = models.OneToOneField(Group, CASCADE, primary_key=True)

    scavenger_team = models.BooleanField(default=True)
    scavenger_finished = models.BooleanField("Finished Scavenger", default=False)
    scavenger_locked_out_until = models.BigIntegerField("Scavenger Locked Out Until", default=0)
    scavenger_enabled_for_team = models.BooleanField(default=True)

    trade_up_team = models.BooleanField(default=True)
    trade_up_enabled_for_team = models.BooleanField(default=True)

    puzzles = models.ManyToManyField('Puzzle', through="TeamPuzzleActivity")

    coin_amount = models.BigIntegerField("Coin Amount", default=0)
    color = models.PositiveIntegerField("Hex Color Code", null=True, blank=True, default=None)

    logo = models.ImageField(upload_to=md.logo_path, blank=True, null=True)
    scav_tree = models.FileField(upload_to=md.tree_path, blank=True, null=True)
    free_hints = models.IntegerField(default=0)
    _room = models.CharField("Room Number", max_length=64, blank=True, null=True)
    invalidate_tree = models.BooleanField(default=True)
    tree_cache = models.TextField(default="")

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
    def room(self):
        rooms = TeamRoom.objects.filter(team=self)
        today = datetime.date.today()
        for room in rooms:
            if room.date == today:
                return room.room
        return self._room

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
    def num_clues_finished(self) -> int:
        return len(self.verified_puzzles)

    @property
    def num_main_clues_finished(self) -> int:
        main_streams = md.PuzzleStream.objects.filter(enabled=True, default=True)
        activities = md.TeamPuzzleActivity.objects \
            .filter(puzzle__stream__in=main_streams, team=self,
                    puzzle__enabled=True, verification_photo__approved=True) \
            .exclude(puzzle_completed_at=None)
        return len(activities)

    @property
    def last_puzzle_timestamp(self) -> str:
        activity = md.TeamPuzzleActivity.objects.filter(team=self).exclude(puzzle_completed_at=None)
        activity = activity.order_by("-puzzle_completed_at").first()
        if activity is None:
            return "N/A"
        return str(activity.puzzle_completed_at)

    @property
    def active_branches(self):
        activities = md.TeamPuzzleActivity.objects.filter(team=self).order_by("puzzle__stream__name") \
                       .select_related("puzzle", "puzzle__stream")
        branches = []
        for a in activities:
            found = False
            for a2 in branches:
                if a.puzzle.stream == a2.puzzle.stream:
                    found = True
            if a.puzzle.stream.enabled and not found:
                branches += [a]
        return branches  # This returns puzzle activities because Django templates can't call functions
        # and the activities are the only model that has both team and puzzle info

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
        result = []
        query = md.TeamPuzzleActivity.objects.select_related("puzzle") \
                  .filter(team=self, puzzle_completed_at=None, puzzle__stream__locked=False) \
                  .order_by("puzzle__order")
        for a in query:
            result += [a.puzzle]
        return result

    @property
    def completed_puzzles(self) -> List:
        result = []
        query = md.TeamPuzzleActivity.objects.select_related("puzzle") \
                  .filter(team=self).exclude(puzzle_completed_at=None).order_by("puzzle__order")
        for a in query:
            result += [a.puzzle]
        return result

    @property
    def verified_puzzles(self) -> List:
        result = []
        query = md.TeamPuzzleActivity.objects.select_related("puzzle", "verification_photo") \
                  .filter(team=self, verification_photo__approved=True).order_by("puzzle__order")
        for a in query:
            result += [a.puzzle]
        return result

    @property
    def completed_puzzles_awaiting_verification(self) -> List:
        result = []
        query = md.TeamPuzzleActivity.objects.select_related("puzzle", "verification_photo") \
                  .filter(team=self, verification_photo__approved=False).order_by("puzzle__order")
        for a in query:
            result += [a.puzzle]
        return result

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
        result = []
        query = md.TeamPuzzleActivity.objects.select_related("puzzle").filter(team=self, verification_photo=None) \
                  .exclude(puzzle_completed_at=None).order_by("puzzle__order")
        for a in query:
            result += [a.puzzle]
        return result

    # @property
    # def latest_puzzle_activities(self) -> List[TeamPuzzleActivity]:

    @property
    def scavenger_locked(self) -> bool:
        now = int(timezone.now().timestamp())
        for period in md.LockoutPeriod.objects.filter(branch=None):
            if int(period.start.timestamp()) <= now and int(period.end.timestamp()) >= now:
                return True
        if self.scavenger_locked_out_until == 0:
            return False
        if self.scavenger_locked_out_until <= now:
            self.scavenger_locked_out_until = 0
            self.save()
            return False
        return True

    @property
    def scavenger_locked_datetime(self) -> str:
        if self.scavenger_locked_out_until == 0:
            return "Unlocked"
        dt = datetime.datetime.fromtimestamp(self.scavenger_locked_out_until)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def scavenger_lock(self, minutes) -> None:
        self.scavenger_locked_out_until = int(timezone.now().timestamp()) + minutes * 60
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
        streams = md.PuzzleStream.objects.filter(enabled=True, default=True)

        for s in streams:
            puz = s.first_enabled_puzzle

            if puz:
                pa = md.TeamPuzzleActivity(team=self, puzzle=puz)

                pa.save()

        self.scavenger_finished = False
        self.scavenger_locked_out_until = None
        self.invalidate_tree = True
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
                    activity = md.TeamPuzzleActivity.objects.get(team=self.id, puzzle=puz.id)
                    if not activity.is_verified or not activity.is_completed:
                        return False
                except md.TeamPuzzleActivity.DoesNotExist:
                    return False

        self.scavenger_finished = True
        self.save()
        return True

    def refresh_scavenger_progress(self) -> None:
        return
        """Moves team along if verified on a puzzle or a puzzle has been disabled."""

        logger.info(f"Refreshing scavenger progress for team {self}")
        self.check_if_finished_scavenger()
        self.invalidate_tree = True
        self.save()
        if self.scavenger_finished:
            return
        activities = md.TeamPuzzleActivity.objects.filter(team=self, puzzle__enabled=True).select_related("puzzle")
        disabled = md.TeamPuzzleActivity.objects.filter(team=self, puzzle__enabled=False).select_related("puzzle")
        for act in activities | disabled:
            if (act.is_verified and act.is_completed) or not act.puzzle.enabled:
                if act.puzzle.stream_branch is not None or act.puzzle.stream_puzzle is not None:
                    if act.puzzle.stream_puzzle is not None:
                        try:
                            md.TeamPuzzleActivity(team=self, puzzle=act.puzzle.stream_puzzle).save()
                        except Exception:
                            pass  # Activity already exists
                    if act.puzzle.stream_branch is not None:
                        next_puz = act.puzzle.stream_branch.first_enabled_puzzle
                        try:
                            md.TeamPuzzleActivity(team=self, puzzle=next_puz).save()
                        except Exception:
                            pass  # Activity already exists
                max_order = act.puzzle.order
                for a2 in activities:
                    if a2.puzzle.stream == act.puzzle.stream and a2.puzzle.order > max_order:
                        max_order = a2.puzzle.order
                if max_order > act.puzzle.order:
                    if not act.is_completed and not act.puzzle.enabled:
                        act.delete()
                    continue
                next_puz = md.Puzzle.objects.filter(stream=act.puzzle.stream,
                                                    order__gt=max_order, enabled=True).first()
                if next_puz is None:
                    if not act.is_completed and not act.puzzle.enabled:
                        act.delete()
                    if self.check_if_finished_scavenger():
                        return
                    continue
                try:
                    md.TeamPuzzleActivity(team=self, puzzle=next_puz).save()
                except Exception:
                    pass  # Activity already exists
                if not act.is_completed and not act.puzzle.enabled:
                    act.delete()

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

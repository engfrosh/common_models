from django.db import models
from django_unixdatetimefield import UnixDateTimeField
import logging
from io import BytesIO
from django.db.models.deletion import CASCADE, PROTECT, SET_NULL
from django.conf import settings
from typing import List, Optional, Tuple, Union
import datetime
import qrcode
import qrcode.constants
import qrcode.image.svg
from qrcode.image.styledpil import StyledPilImage
from django.core.files import File
from PIL import Image, ImageDraw, ImageFont

import common_models.models as md
logger = logging.getLogger("common_models.scav_models")

PUZZLE_VERIFICATION_DIR = "verification_photos/"


def _puzzle_verification_photo_upload_path(instance, filename) -> str:
    return md.random_path(instance, filename, PUZZLE_VERIFICATION_DIR)


class LockoutPeriod(models.Model):
    start = UnixDateTimeField()
    end = UnixDateTimeField()
    branch = models.ForeignKey('PuzzleStream', on_delete=CASCADE, null=True, blank=True)


class PuzzleGuess(models.Model):
    """Stores all the guesses for scavenger."""

    datetime = UnixDateTimeField(auto_now=True)
    value = models.CharField(max_length=100)
    activity = models.ForeignKey('TeamPuzzleActivity', on_delete=CASCADE)

    class Meta:

        verbose_name = "Puzzle Guess"
        verbose_name_plural = "Puzzle Guesses"


class PuzzleStream(models.Model):
    """Puzzle streams in scavenger"""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    enabled = models.BooleanField(default=True)
    default = models.BooleanField(default=True)
    locked = models.BooleanField(default=False)
    online = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.name}"

    class Meta:
        verbose_name = "Scavenger Puzzle Stream"
        verbose_name_plural = "Scavenger Puzzle Streams"

    @property
    def _all_puzzles_qs(self) -> models.QuerySet:
        return Puzzle.objects.filter(stream=self.id).order_by("order")

    @property
    def all_puzzles(self) -> List:
        return list(self._all_puzzles_qs)

    @property
    def _all_enabled_puzzles_qs(self) -> models.QuerySet:
        return Puzzle.objects.filter(stream=self.id, enabled=True).order_by("order")

    @property
    def all_enabled_puzzles(self) -> List:
        """Returns a list of enabled puzzles in order they are to be completed."""
        return list(self._all_enabled_puzzles_qs)

    @property
    def first_enabled_puzzle(self) -> Optional:
        """Returns the first enabled puzzle for the stream if it exists."""

        return self._all_enabled_puzzles_qs.first()

    def get_next_enabled_puzzle(self, puzzle) -> Optional:
        """Returns the next puzzle, returns None if there are no more Puzzles, ie stream completed."""

        return self._all_enabled_puzzles_qs.filter(order__gt=puzzle.order).order_by("order").first()


class VerificationPhoto(models.Model):
    """Stores references to all the uploaded photos for scavenger puzzle verification."""

    datetime = UnixDateTimeField(auto_now=True)
    photo = models.ImageField(upload_to=_puzzle_verification_photo_upload_path, null=True)
    approved = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Verification Photo"
        verbose_name_plural = "Verification Photos"

        permissions = [
            ("photo_api", "Can create verification photos through the API"),
        ]

    def approve(self) -> None:
        activity = TeamPuzzleActivity.objects.filter(verification_photo=self).first()
        puzzle = activity.puzzle
        team = activity.team
        if puzzle.stream_branch is not None:
            first_en = puzzle.stream_branch.first_enabled_puzzle
            if first_en is not None:
                branch_activity = TeamPuzzleActivity(team=team, puzzle=first_en)
                try:
                    branch_activity.save()
                except Exception:
                    logger.warn("Team stream puzzle activity already exists for " + str(team) + ": " + str(puzzle))
        if puzzle.stream_puzzle is not None:
            branch_activity = TeamPuzzleActivity(team=team, puzzle=puzzle.stream_puzzle)
            try:
                branch_activity.save()
            except Exception:
                logger.warn("Team stream_puzzle puzzle activity already exists for " + str(team) + ": " + str(puzzle))
        self.approved = True
        self.save()
        team.invalidate_tree = True
        team.save()
        if puzzle.last_puzzle_in_stream:
            team.free_hints += 1
            team.save()
        try:
            TeamPuzzleActivity.objects.get(verification_photo=self).team.refresh_scavenger_progress()
        except TeamPuzzleActivity.DoesNotExist:
            pass


class TeamPuzzleActivity(models.Model):
    """Relates teams to the puzzles they have active and have completed."""

    team = models.ForeignKey(md.Team, on_delete=CASCADE)
    puzzle = models.ForeignKey('Puzzle', on_delete=CASCADE)
    puzzle_start_at = UnixDateTimeField(auto_now=True)
    puzzle_completed_at = UnixDateTimeField(null=True, blank=True, default=None)
    verification_photo = models.ForeignKey(VerificationPhoto, on_delete=SET_NULL, null=True, blank=True, default=None)
    completed_bitmask = models.IntegerField(default=0)

    class Meta:

        verbose_name = "Team Puzzle Activity"
        verbose_name_plural = "Team Puzzle Activities"

        unique_together = [["team", "puzzle"]]

    @property
    def num_clues_finished(self) -> int:
        activities = TeamPuzzleActivity.objects \
                     .filter(puzzle__stream=self.puzzle.stream, team=self.team,
                             puzzle__enabled=True, verification_photo__approved=True) \
                     .exclude(puzzle_completed_at=0)
        return len(activities)

    @property
    def num_clues_total(self) -> int:
        return len(Puzzle.objects.filter(enabled=True, stream=self.puzzle.stream))

    def __str__(self) -> str:
        return f"{self.team.display_name} on puzzle: {self.puzzle.name}"

    def _is_active(self) -> bool:
        if self.puzzle_completed_at:
            return False
        return self.puzzle.enabled

    def _is_completed(self) -> bool:
        if self.puzzle_completed_at:
            return True
        return False

    def _is_verified(self) -> bool:
        if self.verification_photo and self.verification_photo.approved or \
           not self.puzzle.require_photo_upload and self.is_completed:
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

        logger.info(f"Marking puzzle {self.puzzle} completed for team {self.team}")

        if self.puzzle_completed_at:
            logger.warning(f"Puzzle {self.puzzle} already completed for team {self.team}")
            return

        self.puzzle_completed_at = datetime.datetime.now()
        self.save()
        self.team.invalidate_tree = True
        self.team.save()

        logger.info(f"Puzzle {self.puzzle} marked as completed for team {self.team} at {self.puzzle_completed_at}")

    @property
    def completed_answers(self) -> bool:
        answers = self.puzzle.answer.split(",")
        comp = []
        for i in range(0, 32):
            mask = 1 << i
            if self.completed_bitmask & mask:
                comp += [answers[i]]
        return comp

    def complete_answer(self, answer: str) -> bool:
        answers = self.puzzle.answer.split(",")
        missing = False
        correct = False
        for i in range(len(answers)):
            a = answers[i]
            if answer.lower() == a.lower():
                if self.completed_bitmask & (1 << i):
                    return False
                self.completed_bitmask |= 1 << i
                self.save()
                logger.info(f"Marking puzzle {self.puzzle}" +
                            f"partially completed with answer {answer} for team {self.team}")
                correct = True
            if not self.completed_bitmask & (1 << i):
                missing = True
        if not missing:
            self.mark_completed()
        return correct

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


class QRCode(models.Model):
    puzzle = models.ForeignKey("Puzzle", on_delete=CASCADE)
    qr_code = models.ImageField(upload_to=md.scavenger_qr_code_path, blank=True, null=True)

    def generate_qr_code(self, answer: str) -> None:

        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
        qr.add_data(
            "https://" + settings.ALLOWED_HOSTS[0] + "/scavenger/puzzle/" + self.puzzle.secret_id + "?answer=" + answer)
        qr.make(fit=True)

        blob = BytesIO()
        STYLE_IMAGE_PATH = "SpiritX.png"
        USE_IMAGE = True
        if USE_IMAGE:
            img = qr.make_image(image_factory=StyledPilImage, embeded_image_path=STYLE_IMAGE_PATH)
        else:
            img = qr.make_image()

        orig_width = img.size[0]
        height = img.size[1]
        font = ImageFont.truetype(settings.STATICFILES_DIRS[0]+"/font.ttf", 40)
        text_len = font.getlength(answer)
        width = int(max(orig_width + 50, text_len + 50))
        offset = 25
        if text_len + 50 > orig_width:
            offset = int((text_len + 50 - orig_width)/2)
        with_text = Image.new(mode="RGB", size=(width, height + 50))
        draw = ImageDraw.Draw(with_text)
        draw.rectangle([(0, 0), with_text.size], fill=(255, 255, 255))
        with_text.paste(img, (offset, 0))
        draw.rectangle([(offset, 0), (offset + img.width, img.height)], fill=(255, 255, 255))
        draw.text((width/2-text_len/2, height - 30),
                  answer, align="center", fill=(0, 0, 0), font=font)

        with_text.save(blob, "PNG")

        self.qr_code.save("QRCode.png", File(blob))
        self.save()


class Puzzle(models.Model):
    """Puzzles in scavenger"""

    id = models.AutoField(unique=True, primary_key=True)
    name = models.CharField(max_length=200, unique=True)

    answer = models.CharField(max_length=400)
    require_photo_upload = models.BooleanField(default=settings.DEFAULT_SCAVENGER_PUZZLE_REQUIRE_PHOTO_UPLOAD)

    secret_id = models.SlugField(max_length=64, unique=True, default=md.random_puzzle_secret_id)

    enabled = models.BooleanField(default=True)

    order = models.DecimalField(max_digits=8, decimal_places=3)
    stream = models.ForeignKey(PuzzleStream, on_delete=PROTECT)

    puzzle_text = models.CharField("Text", blank=True, max_length=2000)
    puzzle_file = models.FileField(upload_to=md.puzzle_path, blank=True)
    puzzle_file_display_filename = models.CharField(max_length=256, blank=True)
    puzzle_file_download = models.BooleanField(default=False)
    puzzle_file_is_image = models.BooleanField(default=False)
    puzzle_is_link = models.BooleanField(default=False)

    created_at = UnixDateTimeField(auto_now_add=True)
    updated_at = UnixDateTimeField(auto_now=True)

    stream_branch = models.ForeignKey(PuzzleStream, on_delete=CASCADE, null=True, blank=True, default=None, related_name='branch_puzzle')  # noqa: E501
    stream_puzzle = models.ForeignKey("Puzzle", on_delete=SET_NULL, blank=True, null=True, related_name='puzzle_opener')
    # teams = models.ManyToManyField(Team, through="TeamPuzzleActivity")

    class Meta:
        verbose_name = "Scavenger Puzzle"
        verbose_name_plural = "Scavenger Puzzles"

        permissions = [
            ("guess_scavenger_puzzle", "Can guess for scavenger puzzle"),
            ("manage_scav", "Can manage scav"),
            ("bypass_scav_rules", "Bypasses all scav rules"),
            ("lock_scav", "Can lock scav")
        ]

        unique_together = [["order", "stream"]]

    def __str__(self) -> str:
        return f"Puzzle: {self.name} [{self.id}]"

    @property
    def last_puzzle_in_stream(self):
        last = Puzzle.objects.filter(stream=self.stream).order_by('-order').first()
        if last == self:
            return True
        return False

    @property
    def answers(self):
        return self.answer.split(",")

    def puzzle_activity_from_team(self, team: md.Team) -> Optional[TeamPuzzleActivity]:
        try:
            return TeamPuzzleActivity.objects.get(puzzle=self.id, team=team.id)
        except TeamPuzzleActivity.DoesNotExist:
            return None

    def is_viewable_for_team(self, team: md.Team) -> bool:
        if not self.enabled:
            return False
        return TeamPuzzleActivity.objects.filter(puzzle=self.id, team=team.id).exists()

    def is_active_for_team(self, team: md.Team) -> bool:
        if not self.enabled:
            return False

        pa: Union[TeamPuzzleActivity, None] = TeamPuzzleActivity.objects.get(puzzle=self.id, team=team.id)
        if pa:
            return pa.is_active

        else:
            return False

    def is_completed_for_team(self, team: md.Team) -> bool:
        if not self.enabled:
            return False

        pa: Union[TeamPuzzleActivity, None] = TeamPuzzleActivity.objects.get(puzzle=self.id, team=team.id)
        if pa:
            return pa.is_completed

        else:
            return False

    def requires_verification_photo_by_team(self, team: md.Team) -> bool:
        if not self.enabled:
            return False

        pa = self.puzzle_activity_from_team(team)
        if not pa:
            return False

        return pa.requires_verification_photo_upload

    def check_team_guess(self, team: md.Team, guess: str, bypass=False) -> Tuple:
        """
        Checks if a team's guess is correct. First is if correct, second if stream complete,
        third the new puzzle if unlocked, fourth if a verification picture is required.

        Will move team to next question if it is correct or complete scavenger if appropriate.
        """

        logger.info(f"Checking team guess for team {team} with guess: {guess}")

        activity = TeamPuzzleActivity.objects.get(team=team.id, puzzle=self.id)
        logger.info(f"Got current puzzle activity for team {team}: {activity}")

        # Create a guess object
        pg = PuzzleGuess(value=guess, activity=activity)
        pg.save()
        logger.info(f"Saved puzzle guess for team {team} on puzzle {self}: {pg}")

        # Check the answer
        correct = activity.complete_answer(guess)

        if not correct:
            answer = self.answer.lower()
            logger.info(f"Team {team} guess {guess} is not the answer to puzzle {self}, {answer}")
            return (correct, False, None, False)

        # Mark the question as correct
        logger.info(f"Team {team} guess {guess} is correct for puzzle {self}")

        md.ChannelTag.objects.get_or_create(name="SCAVENGER_MANAGEMENT_UPDATES_CHANNEL")
        discord_channels = md.DiscordChannel.objects.filter(tags__name="SCAVENGER_MANAGEMENT_UPDATES_CHANNEL")

        if activity.is_completed:

            # If verification is required,
            if self.require_photo_upload and not bypass:
                for ch in discord_channels:
                    ch.send(f"{team.display_name} has completed question {self.name}, awaiting a photo upload.")

                return (correct, False, None, True)
            else:
                photo = VerificationPhoto(approved=True, photo=None)
                photo.save()
                activity.verification_photo = photo
                activity.save()

            # Otherwise if correct check if done scavenger and if not increment question
            next_puzzle = self.stream.get_next_enabled_puzzle(self)
            if self.stream_branch is not None:
                branch_activity = TeamPuzzleActivity(team=team, puzzle=self.stream_branch.first_enabled_puzzle)
                branch_activity.save()
            if self.stream_puzzle is not None:
                try:
                    branch_activity = TeamPuzzleActivity(team=team, puzzle=self.stream_puzzle)
                    branch_activity.save()
                except Exception:
                    pass
            logger.info(f"Next puzzle for team {team} is {next_puzzle}")

            if not next_puzzle:
                team.free_hints += 1
                team.save()
                team.check_if_finished_scavenger()

                for ch in discord_channels:
                    ch.send(f"{team.display_name} has completed scavenger stream {self.stream.name}" +
                            ", awaiting a photo upload.")

                return (correct, True, None, False)
            try:
                TeamPuzzleActivity(team=team, puzzle=next_puzzle).save()
            except Exception:
                pass
            for ch in discord_channels:
                ch.send(f"{team.display_name} has completed puzzle {self.name}, moving on to puzzle {next_puzzle.name}")

            return (correct, False, next_puzzle, False)
        else:
            for ch in discord_channels:
                ch.send(f"{team.display_name} has partially completed puzzle {self.name} with {guess}")
            return (True, False, self, False)

    def _generate_qr_code(self) -> None:
        codes = QRCode.objects.filter(puzzle=self)
        for qr in codes:
            qr.delete()
        for a in self.answer.split(","):
            qr = QRCode(puzzle=self)
            qr.generate_qr_code(a)

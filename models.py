"""


Some inspiration from: https://github.com/Palindrome-Puzzles/2022-hunt/blob/main/hunt/app/models.py
"""

from __future__ import annotations

import string
import os
import random

from common_models.common_models_setup import init_django
init_django()

from django.db import models  # noqa: E402
from django.contrib.auth.models import Group  # noqa: E402
from django.db.models.deletion import CASCADE, PROTECT  # noqa: E402


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
    finished = models.BooleanField("Finished Scavenger", default=False)

    class Meta:
        verbose_name = "Scavenger Team"
        verbose_name_plural = "Scavenger Teams"

    def __str__(self) -> str:
        return self.group.name

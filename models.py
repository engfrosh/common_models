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
from typing import Optional

from common_models.common_models_setup import init_django  # noqa: E402
init_django()
from django.utils import timezone  # noqa: E402
# This function is above the imports as its needed by some of the modules it imports


def random_path(instance, filename, base="", *, length: Optional[int] = None):
    if length is None:
        length = FILE_RANDOM_LENGTH
    _, ext = os.path.splitext(filename)
    rnd = "".join(random.choice(string.ascii_letters + string.digits) for i in range(length))
    return base + rnd + ext


def puzzle_path(instance, filename):
    return random_path(instance, filename, SCAVENGER_DIR + PUZZLE_DIR)


def scavenger_qr_code_path(instance, filename):
    return random_path(instance, filename, SCAVENGER_DIR + QR_CODE_DIR)


def magic_link_qr_code_path(instance, filename):
    return random_path(instance, filename, "magic_links/" + QR_CODE_DIR)


def random_puzzle_secret_id():
    return "".join(random.choice(string.ascii_lowercase) for i in range(PUZZLE_SECRET_ID_LENGTH))


def hint_path(instance, filename):
    return random_path(instance, filename, SCAVENGER_DIR + "hints/")


def question_path(instance, filename):
    return puzzle_path(instance, filename)


# region Authentication


def days5():
    return timezone.now() + datetime.timedelta(days=5)


def random_token():
    return secrets.token_urlsafe(42)


# endregion

# All of the subclasses of models used because this file was >1k lines

from .teams_models import Team, VirtualTeam  # noqa: E402, F401
from .scav_models import PuzzleStream, Puzzle, VerificationPhoto  # noqa: E402, F401
from .scav_models import _puzzle_verification_photo_upload_path  # noqa: E402, F401
from .scav_models import PuzzleGuess, TeamPuzzleActivity  # noqa: E402, F401
from .discord_models import DiscordUser, RoleInvite, DiscordChannel, get_client  # noqa: E402, F401
from .discord_models import DiscordOverwrite, ChannelTag, DiscordRole, DiscordGuild  # noqa: E402, F401
from .data_models import UniversityProgram, UserDetails, FroshRole, BooleanSetting  # noqa: E402, F401
from .auth_models import MagicLink  # noqa: E402, F401
from .trade_models import TeamTradeUpActivity  # noqa: E402, F401
from .ticket_models import Ticket, TicketComment  # noqa: E402, F401
from .euchre_models import EuchrePlayer, EuchreTrick, EuchreTeam, EuchreCard  # noqa: E402, F401
from .euchre_models import EuchreGame  # noqa: E402, F401
logger = logging.getLogger("common_models.models")


SCAVENGER_DIR = "scavenger/"
PUZZLE_DIR = "puzzles/"
QR_CODE_DIR = "qr_codes/"

FILE_RANDOM_LENGTH = 128

PUZZLE_SECRET_ID_LENGTH = 16

# region Database Setup


def initialize_database() -> None:
    ChannelTag.objects.get_or_create(name="SCAVENGER_MANAGEMENT_UPDATES_CHANNEL")
    ChannelTag.objects.get_or_create(name="TRADE_UP_MANAGEMENT_UPDATES_CHANNEL")
    BooleanSetting.objects.get_or_create(id="SCAVENGER_ENABLED")
    BooleanSetting.objects.get_or_create(id="TRADE_UP_ENABLED")


def initialize_scav() -> None:
    for team in Team.objects.all():
        streams = PuzzleStream.objects.filter(enabled=True)

        for s in streams:
            puz = s.first_enabled_puzzle
            pa = TeamPuzzleActivity(team=team, puzzle=puz)
            pa.save()

# endregion

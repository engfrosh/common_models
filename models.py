"""


Some inspiration from: https://github.com/Palindrome-Puzzles/2022-hunt/blob/main/hunt/app/models.py
"""


from django.db import models
from common_models.common_modules_setup import init_django

init_django()


class NewModel(models.Model):

    id = models.AutoField(primary_key=True)
    name = models.TextField(max_length=40)


# region Scavenger

class Puzzle(models.Model):
    """Puzzles in scavenger"""

    id = models.IntegerField(unique=True, primary_key=True)
    name = models.CharField(max_length=200, unique=True)
    answer = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Puzzle: {self.name} [{self.id}]"

    class Meta:
        verbose_name = "Scavenger Puzzle"
        verbose_name_plural = "Scavenger Puzzles"

# endregion

from django.db import models
from django.db.models.deletion import CASCADE
from django.contrib.auth.models import User, Group
from django_unixdatetimefield import UnixDateTimeField


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
    invite_email_sent = models.BooleanField("Invite Email Sent", default=False)
    checked_in = models.BooleanField("Checked In", default=False)
    shirt_size = models.CharField("Shirt Size", max_length=5, blank=True)

    class Meta:
        """User Details Meta information."""

        verbose_name = "User Details"
        verbose_name_plural = "Users' Details"
        permissions = [
            ("check_in", "Can manage user check in"),
            ("pronoun_group", "Indicated that a group is a pronoun")
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.user.username})"

    @property
    def pronouns(self) -> list[Group]:
        groups = self.user.groups
        pronouns = []
        for group in groups:
            for p in group.permissions:
                if p.codename == "common_models.pronoun_group":
                    pronouns += [group]
                    break
        return pronouns


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


class BooleanSetting(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    value = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Boolean Setting"
        verbose_name_plural = "Boolean Settings"

    def __str__(self) -> str:
        return f"<Setting {self.id}: {self.value} >"


class Announcement(models.Model):
    id = models.AutoField("Announcement ID", primary_key=True)
    created = UnixDateTimeField(auto_now=True)
    title = models.CharField(max_length=200)
    body = models.TextField()

from django.db import models
from django.db.models.deletion import CASCADE
from django.contrib.auth.models import User, Group
from django_unixdatetimefield import UnixDateTimeField
import common_models.models as md


class InclusivityPage(models.Model):
    name = models.CharField("Name", max_length=128)
    permissions = models.IntegerField()
    open_time = UnixDateTimeField()
    file = models.FileField(upload_to=md.inclusivity_path)


class FacilShift(models.Model):
    id = models.AutoField("Shift ID", primary_key=True)
    name = models.CharField("Name", max_length=128)
    desc = models.CharField("Description", max_length=1000)
    flags = models.CharField("Flags", max_length=5)
    start = UnixDateTimeField(null=True)
    end = UnixDateTimeField(null=True)
    max_facils = models.IntegerField()

    class Meta:
        """Facil Shift Meta information."""

        verbose_name = "Facil Shift"
        verbose_name_plural = "Facil Shifts"
        permissions = [
            ("facil_signup", "Can sign up for shifts"),
        ]

    @property
    def facil_count(self) -> int:
        return len(FacilShiftSignup.objects.filter(shift=self))


class FacilShiftSignup(models.Model):
    user = models.ForeignKey(User, on_delete=CASCADE)
    shift = models.ForeignKey(FacilShift, on_delete=CASCADE)


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


class PronounOption(models.Model):
    emote = models.CharField("Emote", max_length=64)
    name = models.CharField("Name", max_length=64)


class Pronoun(models.Model):
    """Map a pronoun to a user"""
    name = models.CharField("Pronoun", max_length=64)
    user = models.ForeignKey(User, on_delete=CASCADE)
    order = models.IntegerField()

    class Meta:
        unique_together = [["user", "order"]]


class UserDetails(models.Model):
    """Details pertaining to users without fields in the default User."""

    user = models.OneToOneField(User, on_delete=CASCADE, primary_key=True)
    name = models.CharField("Name", max_length=64)
    invite_email_sent = models.BooleanField("Invite Email Sent", default=False)
    checked_in = models.BooleanField("Checked In", default=False)
    shirt_size = models.CharField("Shirt Size", max_length=5, blank=True)
    override_nick = models.CharField("Name Override", max_length=64, null=True, default=None, blank=True)
    int_frosh_id = models.IntegerField(unique=False, default=0)
    waiver_completed = models.BooleanField("Waiver Completed", default=False)
    prc_completed = models.BooleanField("PRC Completed", default=False)
    brightspace_completed = models.BooleanField("Brightspace Training Completed", default=False)
    training_completed = models.BooleanField("In Person Training Completed", default=False)
    hardhat = models.BooleanField("Hardhat Requested", default=False)
    hardhat_paid = models.BooleanField("Hardhat Paid", default=False)
    breakfast = models.BooleanField("Breakfast Requested", default=False)
    breakfast_paid = models.BooleanField("Breakfast Paid", default=False)
    rafting = models.BooleanField("Rafting Requested", default=False)
    rafting_paid = models.BooleanField("Rafting Paid", default=False)
    contract = models.BooleanField("Contract Signed", default=False)

    class Meta:
        """User Details Meta information."""

        verbose_name = "User Details"
        verbose_name_plural = "Users' Details"
        permissions = [
            ("check_in", "Can manage user check in"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.user.username})"

    @property
    def pronouns(self) -> list[Pronoun]:
        return list(Pronoun.objects.filter(user=self.user).order_by('order'))

    @property
    def next_pronoun(self) -> int:
        if len(self.pronouns) == 0:
            return 0
        return self.pronouns[-1].order + 1

    @property
    def can_check_in(self) -> bool:
        groups = self.user.groups
        frosh_groups = FroshRole.objects.all()
        names = []
        for g in frosh_groups:
            names += [g.name]
        role = groups.filter(name__in=names).first()
        if role is None:
            return False
        if role.name == "Frosh":
            if not self.waiver_completed:
                return False
            return True
        else:
            if not self.waiver_completed or not self.prc_completed or not self.contract:
                return False
            elif not self.brightspace_completed or not self.training_completed:
                return False
            elif self.hardhat and not self.hardhat_paid:
                return False
            elif self.breakfast and not self.breakfast_paid:
                return False
            elif self.rafting and not self.rafting_paid:
                return False
            return True

    @property
    def check_in_reason(self) -> bool:
        groups = self.user.groups
        frosh_groups = FroshRole.objects.all()
        names = []
        for g in frosh_groups:
            names += [g.name]
        role = groups.filter(name__in=names).first()
        if role is None:
            return "ERROR"
        reason = ""
        if role.name == "Frosh":
            if not self.waiver_completed:
                reason += "Waiver "
        else:
            if not self.waiver_completed:
                reason += "Waiver  "
            elif not self.prc_completed:
                reason += "PRC  "
            elif not self.contract:
                reason += "Contract "
            elif not self.brightspace_completed:
                reason += "Brightspace "
            elif not self.training_completed:
                reason += "Training "
            elif self.hardhat and not self.hardhat_paid:
                reason += "Hardhat "
            elif self.breakfast and not self.breakfast_paid:
                reason += "Breakfast "
            elif self.rafting and not self.rafting_paid:
                reason += "Rafting "
        return reason

    @property
    def frosh_id(self) -> int:
        if self.int_frosh_id == 0:
            self.generate_frosh_id()
        return self.int_frosh_id

    def generate_checksum(self, id) -> int:
        checksum = 0  # Basically just a Luhn checksum
        double = True
        while id > 0:
            if double:
                checksum += (id % 10) * 2
            else:
                checksum += id % 10
            id = id // 10
            double = not double
        return checksum % 10

    def generate_frosh_id(self) -> None:
        id = 70000 + self.user.id
        checksum = self.generate_checksum(id)
        id = id * 10 + checksum
        self.int_frosh_id = id
        self.save()


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

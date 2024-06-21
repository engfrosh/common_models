from django.db import models
from django.db.models.deletion import CASCADE
from django.contrib.auth.models import User, Group
from django_unixdatetimefield import UnixDateTimeField
import common_models.models as md
import datetime
from django.utils.html import escape


class SiteImage(models.Model):
    name = models.CharField("Name", max_length=100)
    image = models.ImageField(upload_to=md.img_path, null=True)


class FAQPage(models.Model):
    id = models.AutoField("Page ID", primary_key=True)
    title = models.CharField("Title", max_length=500)
    body = models.TextField()
    restricted = models.ManyToManyField(Group, blank=True)

    @property
    def html_body(self):
        esc = escape(self.body)
        spl = esc.split("**")
        bolded = ""
        bold = False
        for s in spl:
            if not bold:
                bolded += s
            else:
                bolded += "<b>" + s + "</b>"
            bold = not bold
        result = bolded.replace('\n', "<br>")
        spl = result.split("[")
        result = spl[0]
        for i in range(1, len(spl)):
            s = spl[i]
            index = s.find("]")
            if index == -1:
                result += "[" + s
            else:
                img = s[:index]
                image = SiteImage.objects.filter(name=img).first()
                if image is None:
                    img_url = "broken_link.png"
                else:
                    img_url = image.image.url
                result += "<img src=\""+img_url+"\"/>" + s[index+1:]
        spl = result.split("$")
        result = spl[0]
        inside = True
        for i in range(1, len(spl)):
            s = spl[i]
            if inside:
                if s == "":
                    result += "$"
                else:
                    result += "<a href=\"" + s + "\">" + s + "</a>"
            else:
                result += s
            inside = not inside
        spl = result.split("--")
        result = spl[0]
        inside = True
        for i in range(1, len(spl)):
            s = spl[i]
            if inside:
                table_html = "<table>"
                rows = s.split(".")
                first = True
                for row in rows:
                    table_html += "<tr>"
                    for col in row.split(","):
                        if first:
                            table_html += "<th>" + col + "</th>"
                        else:
                            table_html += "<td>" + col + "</td>"
                    table_html += "</tr>"
                    first = False
                table_html += "</table>"
                result += table_html
            else:
                result += s
            inside = not inside

        return result


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
            ("calendar_manage", "Can manage calendars"),
            ("shift_manage", "Can manage facil shifts"),
            ("attendance_manage", "Can manage facil shift attendance"),
            ("report_manage", "Can manage reports"),
        ]

    @property
    def facil_count(self) -> int:
        return len(FacilShiftSignup.objects.filter(shift=self))

    @property
    def is_cutoff(self) -> bool:
        # Defaults to 72h
        window = int(md.Setting.objects.get_or_create(id="Facil Shift Cutoff",
                                                      defaults={"value": 259200})[0].value)
        if (self.start - datetime.timedelta(seconds=window)).timestamp() >= datetime.datetime.now().timestamp():
            return False
        return True

    @property
    def is_passed(self) -> bool:
        return self.start.timestamp() <= datetime.datetime.now().timestamp()


class FacilShiftSignup(models.Model):
    user = models.ForeignKey(User, on_delete=CASCADE)
    shift = models.ForeignKey(FacilShift, on_delete=CASCADE)
    attendance = models.BooleanField(default=False)


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


class RoleOption(models.Model):
    emote = models.CharField("Emote", max_length=64)
    role = models.PositiveBigIntegerField("Role id")
    message = models.PositiveBigIntegerField("Message id")


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
    allergies = models.CharField("Allergies", max_length=128, null=True, blank=True)
    sweater_size = models.CharField("Sweater Size", max_length=5, blank=True)
    discord_allowed = models.BooleanField("Discord Allowed", default=True)

    charter = models.FileField(upload_to='charter/', null=True, blank=True)

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
    def role(self) -> str:
        groups = self.user.groups
        frosh_groups = FroshRole.objects.all()
        names = []
        for g in frosh_groups:
            names += [g.name]
        role = groups.filter(name__in=names).first()
        if role is None:
            return None
        return role.name

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
        role = self.role
        if role is None:
            return False
        if self.checked_in:
            return False
        if role == "Frosh":
            req = md.Setting.objects.get_or_create(id="Frosh_Checkin_Req",
                                                   defaults={"value": "waiver"})[0].value.split(",")
            if "waiver" in req and not self.waiver_completed:
                return False
            return True
        else:
            req = md.Setting.objects.get_or_create(id="Facil_Checkin_Req",
                                                   defaults={"value": "waiver,brightspace,prc,contract,paid"})[0]
            req = req.value.split(",")
            if "waiver" in req and not self.waiver_completed:
                return False
            if "brightspace" in req and not self.brightspace_completed:
                return False
            if "prc" in req and not self.prc_completed:
                return False
            if "contract" in req and not self.contract:
                return False
            if "paid" in req:
                if self.hardhat and not self.hardhat_paid:
                    return False
                elif self.breakfast and not self.breakfast_paid:
                    return False
                elif self.rafting and not self.rafting_paid:
                    return False
            return True

    @property
    def check_in_reason(self) -> bool:
        role = self.role
        if role is None:
            return "ERROR"
        reason = ""
        if self.checked_in:
            reason += "Checked-in "
        if role == "Frosh":
            req = md.Setting.objects.get_or_create(id="Frosh_Checkin_Req",
                                                   defaults={"value": "waiver"})[0].value.split(",")
            if "waiver" in req and not self.waiver_completed:
                reason += "Waiver "
        else:
            req = md.Setting.objects.get_or_create(id="Facil_Checkin_Req",
                                                   defaults={"value": "waiver,brightspace,prc,contract,paid"})[0]
            req = req.value.split(",")
            if "waiver" in req and not self.waiver_completed:
                reason += "Waiver "
            if "brightspace" in req and not self.brightspace_completed:
                reason += "Brightspace "
            if "prc" in req and not self.prc_completed:
                reason += "PRC "
            if "contract" in req and not self.contract:
                reason += "Contract "
            if "paid" in req:
                if self.hardhat and not self.hardhat_paid:
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

    @property
    def team(self) -> md.Team:
        return md.Team.from_user(self.user)


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


class Setting(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    value = models.CharField(max_length=255, default=None, blank=True, null=True)


class Announcement(models.Model):
    id = models.AutoField("Announcement ID", primary_key=True)
    created = UnixDateTimeField(auto_now=True)
    title = models.CharField(max_length=200)
    body = models.TextField()

    class Meta:
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"
        permissions = [
            ("announcement_manage", "Can manage announcements"),
        ]

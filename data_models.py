from django.db import models
from django.db.models.deletion import CASCADE, SET_NULL
from django.contrib.auth.models import User, Group
import common_models.models as md
import datetime
from django.utils.html import escape
import random
import string


class SiteImage(models.Model):
    name = models.CharField("Name", max_length=100)
    image = models.ImageField(upload_to=md.img_path, null=True)

class SponsorLogo(models.Model):
    name = models.CharField("Name", max_length=100)
    image = models.ImageField(upload_to=md.img_path, null=True)
    footer = models.BooleanField(default=False)
    link = models.CharField("Link", max_length=256, null=True, blank=True)

class FAQPage(models.Model):
    id = models.AutoField("Page ID", primary_key=True)
    title = models.CharField("Title", max_length=500)
    body = models.TextField()
    restricted = models.ManyToManyField(Group, blank=True)
    img = models.ImageField(upload_to=md.img_path, null=True)

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
    open_time = models.DateTimeField()
    file = models.FileField(upload_to=md.inclusivity_path)


class FacilShift(models.Model):
    id = models.AutoField("Shift ID", primary_key=True)
    name = models.CharField("Name", max_length=128)
    desc = models.CharField("Description", max_length=1000)
    flags = models.CharField("Flags", max_length=5)
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)
    max_facils = models.IntegerField()
    max_facils_per_team = models.IntegerField(default=0)
    signups_start = models.DateTimeField(null=True, blank=True)
    administrative = models.BooleanField("Administrative", blank=True, default=False)
    checkin_user = models.ForeignKey(User, null=True, blank=True, on_delete=SET_NULL)
    type = models.CharField("Type", max_length=50, blank=True, null=True)

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
            ("attendance_admin", "Can manage attendance for restricted shifts")
        ]

    @property
    def facil_count(self) -> int:
        return len(self.signups.all())

    def facil_count_on_team(self, team: md.Team) -> int:
        signups = self.signups.all().select_related("user__details")
        count = 0
        for s in signups:
            if s.user.details.team == team:
                count += 1
        return count

    def can_sign_up(self, userdetails):
        if self.administrative:
            return False
        if self.is_cutoff:
            return False
        if self.is_passed:
            return False
        if self.max_facils != 0 and self.facil_count >= self.max_facils:
            return False
        if self.max_facils_per_team != 0 and self.facil_count_on_team(userdetails.team) >= self.max_facils_per_team:
            return False
        return True

    @property
    def is_cutoff(self) -> bool:
        if self.administrative:
            return True
        if self.signups_start is not None and datetime.datetime.now().timestamp() < self.signups_start.timestamp():
            return True
        # Defaults to 72h
        window = int(md.Setting.objects.get_or_create(id="Facil Shift Cutoff",
                                                      defaults={"value": 259200})[0].value)
        if (self.start - datetime.timedelta(seconds=window)).timestamp() >= datetime.datetime.now().timestamp():
            return False
        return True

    @property
    def is_passed(self) -> bool:
        if self.administrative:
            return True
        return self.start.timestamp() <= datetime.datetime.now().timestamp()


class FacilShiftSignup(models.Model):
    user = models.ForeignKey(User, on_delete=CASCADE)
    shift = models.ForeignKey(FacilShift, on_delete=CASCADE, related_name="signups")
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

    user = models.OneToOneField(User, on_delete=CASCADE, primary_key=True, related_name="details")
    name = models.CharField("Name", max_length=64)
    invite_email_sent = models.BooleanField("Invite Email Sent", default=False)
    checked_in = models.BooleanField("Checked In", default=False)
    shirt_size = models.CharField("Shirt Size", max_length=50, blank=True)
    override_nick = models.CharField("Name Override", max_length=64, null=True, default=None, blank=True)
    int_frosh_id = models.CharField(unique=False, default=None, null=True, blank=True, max_length=8)
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
    sweater_size = models.CharField("Sweater Size", max_length=50, blank=True)
    discord_allowed = models.BooleanField("Discord Allowed", default=True)
    wt_waiver_completed = models.BooleanField("WT Waiver Completed", default=False)

    charter = models.FileField(upload_to='charter/', null=True, blank=True)

    class Meta:
        """User Details Meta information."""

        verbose_name = "User Details"
        verbose_name_plural = "Users' Details"
        permissions = [
            ("check_in", "Can manage user check in"),
            ("frosh_list", "Can access frosh list")
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
            if "wt" in req and not self.wt_waiver_completed:
                return False
            return True
        else:
            req = md.Setting.objects.get_or_create(id="Facil_Checkin_Req",
                                                   defaults={"value": "waiver,brightspace,prc,contract,paid"})[0]
            req = req.value.split(",")
            if "waiver" in req and not self.waiver_completed:
                return False
            if "wt" in req and not self.wt_waiver_completed:
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
            if "wt" in req and not self.wt_waiver_completed:
                reason += "WT Waiver "
        else:
            req = md.Setting.objects.get_or_create(id="Facil_Checkin_Req",
                                                   defaults={"value": "waiver,brightspace,prc,contract,paid"})[0]
            req = req.value.split(",")
            if "waiver" in req and not self.waiver_completed:
                reason += "Waiver "
            if "wt" in req and not self.wt_waiver_completed:
                reason += "WT Waiver "
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
        if self.int_frosh_id is None:
            self.generate_frosh_id()
        return self.int_frosh_id

    def generate_frosh_id(self) -> None:
        alphabet = string.ascii_lowercase + string.digits
        self.int_frosh_id = ''.join(random.choices(alphabet, k=8))
        self.save()

    @property
    def team(self) -> md.Team:
        return md.Team.from_user(self.user)

    @property
    def num_shifts(self) -> int:
        return len(FacilShiftSignup.objects.filter(user=self.user))


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
    created = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=200)
    body = models.TextField()

    class Meta:
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"
        permissions = [
            ("announcement_manage", "Can manage announcements"),
        ]

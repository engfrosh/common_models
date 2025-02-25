from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from typing import Optional
import datetime
from django.utils import timezone
import qrcode
import qrcode.constants
import qrcode.image.svg
import logging
from io import BytesIO
from django.utils.encoding import iri_to_uri
from django.core.files import File
import common_models.models as md
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("common_models.auth_models")


class MagicLink(models.Model):
    token = models.CharField(max_length=64, default=md.random_token)
    user = models.OneToOneField(User, models.CASCADE)
    expiry = models.DateTimeField(default=md.days5)
    delete_immediately = models.BooleanField(default=True)

    qr_code = models.ImageField(upload_to=md.magic_link_qr_code_path, blank=True)

    class Meta:
        """Magic Link Meta information."""

        permissions = [
            ("view_links", "Can view magic links"),
        ]

    def link_used(self) -> bool:
        """Returns True if link can still be used, or False if not."""
        if self.delete_immediately:
            self.delete()
            return False

        if self.expiry < timezone.now() + datetime.timedelta(days=1):
            # Only 1 day left, do nothing
            return True

        else:
            self.expiry = timezone.now() + datetime.timedelta(days=1)
            self.save()
            return True

    def full_link(
            self, hostname: Optional[str] = None, login_path: Optional[str] = None, redirect: Optional[str] = None):

        if hostname is None:
            hostname_s = "https://" + settings.ALLOWED_HOSTS[0]
        else:
            hostname_s = hostname

        DEFAULT_LOGIN_PATH = "/accounts/login"

        if login_path is None:
            login_path = DEFAULT_LOGIN_PATH

        if redirect is not None:
            redirect_str = f"&redirect={iri_to_uri(redirect)}"
        else:
            redirect_str = ""

        if hostname_s[:8] != "https://" or hostname_s[:7] != "http://":
            # TODO clean this up to make it better
            hostname_s = "http://" + hostname_s

        return f"{hostname_s}{login_path}?auth={self.token}{redirect_str}"

    def _generate_qr_code(
            self, hostname: Optional[str] = None, login_path: Optional[str] = None,
            redirect: Optional[str] = None) -> None:

        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
        qr.add_data(self.full_link(hostname=hostname, login_path=login_path, redirect=redirect))
        qr.make(fit=True)

        blob = BytesIO()
        img = qr.make_image()

        orig_width = img.size[0]
        height = img.size[1]
        font = ImageFont.truetype(settings.STATICFILES_DIRS[0]+"/font.ttf", 40)
        name = self.user.first_name + " " + self.user.last_name
        text_len = font.getlength(name)
        width = int(max(orig_width, text_len + 50))
        offset = 0
        if text_len + 50 > orig_width:
            offset = int((text_len + 50 - orig_width)/2)
        with_text = Image.new(mode="RGB", size=(width, height + 50))
        draw = ImageDraw.Draw(with_text)
        draw.rectangle([(0, 0), with_text.size], fill=(255, 255, 255))
        with_text.paste(img, (offset, 0))
        draw.text((width/2-text_len/2, height - 30),
                  name, align="center", fill=(0, 0, 0), font=font)

        with_text.save(blob, "PNG")
        self.qr_code.save("QRCode.png", File(blob))
        self.save()

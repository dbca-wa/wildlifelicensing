import mimetypes

from django.conf import settings
from django.urls import reverse
from wagov_utils.components.utils.email import (
    TemplateEmailBase as WAGovUtilsTemplateEmailBase,
)

from wildlifelicensing.apps.main.models import Document

MAX_SUBJECT_LENGTH = 76


def host_reverse(name, args=None, kwargs=None):
    return f"{settings.NOTIFICATION_HOST}{reverse(name, args=args, kwargs=kwargs)}"


# Every Wildlife Licensing email must be sent by wagov_utils TemplateEmailBase.send()
# (EMAIL_DELIVERY switch, logs/email.log, System-Environment header).
class TemplateEmailBase(WAGovUtilsTemplateEmailBase):
    subject = ""
    html_template = "wl/emails/base_email.html"
    # txt_template can be None, in this case a 'tag-stripped' version of the html will be sent. (see send)
    txt_template = "wl/emails/base_email.txt"

    def send_to_user(self, user, context=None):
        return self.send(user.email, context=context)

    def send(
        self,
        to_addresses,
        from_address=None,
        context=None,
        attachments=None,
        cc=None,
        bcc=None,
    ):
        """
        Prepare the arguments, then send with wagov_utils TemplateEmailBase.send().
        :param to_addresses: a string or a list of addresses
        :param from_address: if None the settings.DEFAULT_FROM_EMAIL is used
        :param context: a dictionary or a Context object used for rendering the templates.
        :param attachments: a list of (filepath, content, mimetype) triples
               (see https://docs.djangoproject.com/en/1.9/topics/email/)
               or Documents
        :param bcc:
        :param cc:
        :return: the message, None when sending failed, False when EMAIL_DELIVERY is not 'on'
        """
        # subject can be no longer than MAX_SUBJECT_LENGTH
        if len(self.subject) > MAX_SUBJECT_LENGTH:
            self.subject = f"{self.subject[:MAX_SUBJECT_LENGTH - 2]}.."

        if attachments is None:
            attachments = []
        if not isinstance(attachments, list):
            attachments = list(attachments)

        # Convert Documents to (filename, content, mime) attachment
        _attachments = []
        for attachment in attachments:
            if isinstance(attachment, Document):
                filename = str(attachment)
                content = attachment.file.read()
                mime = mimetypes.guess_type(attachment.filename)[0]
                _attachments.append((filename, content, mime))
            else:
                _attachments.append(attachment)

        return super().send(
            to_addresses,
            from_address=from_address,
            context=context,
            attachments=_attachments,
            cc=cc,
            bcc=bcc,
        )

from wildlifelicensing.apps.emails.emails import TemplateEmailBase, host_reverse


class LicenceRenewalNotificationEmail(TemplateEmailBase):
    subject = "Your wildlife licence is due for renewal."
    html_template = "wl/emails/renew_licence_notification.html"
    txt_template = "wl/emails/renew_licence_notification.txt"


def send_licence_renewal_email_notification(licence):
    email = LicenceRenewalNotificationEmail()
    url = host_reverse("wl_home")

    context = {"url": url, "licence": licence}

    # send() returns False when EMAIL_DELIVERY is not 'on' and None when sending failed:
    # only a sent message counts, so the cron does not set renewal_sent for an email that was not sent
    return bool(email.send(licence.profile.email, context=context))

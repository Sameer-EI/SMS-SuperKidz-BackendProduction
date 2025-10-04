from django.core.mail import send_mail
from django.conf import settings

# def send_email_notification(subject, message, recipients):
#     """
#     Generic email sender for any type of notification.
    
#     :param subject: Email subject line
#     :param message: Email body (plain text)
#     :param recipients: List of email addresses
#     :return: dict with status and recipients info
#     """
#     if not recipients:
#         return {"status": "failed", "reason": "No recipients provided"}

#     try:
#         send_mail(
#             subject=subject,
#             message=message,
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             recipient_list=recipients,
#             fail_silently=False,
#         )
#         return {"status": "sent", "recipients": recipients}
#     except Exception as e:
#         return {"status": "failed", "error": str(e)}

from django.core.mail import EmailMessage

def send_email_notification(subject, message, recipients):
    if not recipients:
        return {"status": "failed", "reason": "No recipients provided"}
    try:
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients
        )
        email.send(fail_silently=False)
        return {"status": "sent", "recipients": recipients}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

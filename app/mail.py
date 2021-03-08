from app import mail
from flask_mail import Message


def send_mail(subject, html, recipients):
    message = Message(subject=subject,
                      body=body,
                      recipients=recipients)
    msg = Message(
        subject,
        html=html,
        recipients=recipients,
        sender=app.config['MAIL_DEFAULT_SENDER'],
    )
    mail.send(msg)

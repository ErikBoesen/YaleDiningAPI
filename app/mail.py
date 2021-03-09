from flask import render_template
from flask_mail import Message
from app import app, mail

DATE_FMT = '%Y-%m-%d'
TIME_FMT = '%H:%M'
DATETIME_FMT = DATE_FMT + ' ' + TIME_FMT

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


def send_scraper_report(stats):
    with app.app_context():
        html = render_template('mail/scraper_report.html', stats=stats,
                               DATE_FMT=DATE_FMT, TIME_FMT=TIME_FMT, DATETIME_FMT=DATETIME_FMT)
    send_mail(subject='YaleDine Scraper Report ' + stats['end_time'].strftime(DATETIME_FMT),
              html=html,
              recipients=app.config['ADMIN_EMAILS'])


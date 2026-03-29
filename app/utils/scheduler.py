import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)
_scheduler = BackgroundScheduler()


def check_and_send_reminders(app):
    with app.app_context():
        from datetime import date, datetime
        from app.models import Settings, Session
        from flask_mail import Message
        from app import mail

        settings = Settings.query.first()
        if not settings or not settings.reminder_active:
            return
        if not settings.email or not settings.reminder_time:
            return

        now = datetime.utcnow()
        if now.hour != settings.reminder_time.hour:
            return

        today = date.today()
        session_today = Session.query.filter(Session.logged_at == today).first()
        if session_today is not None:
            return  # Already logged something today

        try:
            msg = Message(
                subject="Your curriculum awaits — no session logged today",
                recipients=[settings.email],
                body=(
                    "Hey,\n\n"
                    "You haven't logged any time today. Keep the streak alive!\n\n"
                    "Open the app: http://localhost:5000/log\n\n"
                    "— The Curriculum"
                )
            )
            mail.send(msg)
            logger.info("Sent daily reminder to %s", settings.email)
        except Exception as exc:
            logger.error("Failed to send reminder: %s", exc)


def start_scheduler(app):
    _scheduler.add_job(
        func=lambda: check_and_send_reminders(app),
        trigger=CronTrigger(minute=0),   # Every hour on the hour
        id='reminder_check',
        replace_existing=True
    )
    if not _scheduler.running:
        _scheduler.start()
        logger.info("APScheduler started")

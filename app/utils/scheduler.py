import logging
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.utils.dates import local_today, normalize_timezone_name

logger = logging.getLogger(__name__)
_scheduler = BackgroundScheduler()


def check_and_send_reminders(app):
    with app.app_context():
        from datetime import datetime
        from app.models import Settings, Session, Curriculum
        from flask_mail import Message
        from app import mail
        import os

        base_url = os.environ.get('PUBLIC_BASE_URL') or os.environ.get('RENDER_EXTERNAL_URL') or ''
        if base_url.endswith('/'):
            base_url = base_url[:-1]

        now = datetime.utcnow()
        rows = Settings.query.filter_by(reminder_active=True).all()
        for settings in rows:
            if not settings.email or not settings.reminder_time:
                continue
            timezone_name = normalize_timezone_name(settings.timezone)
            local_now = now.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo(timezone_name))
            if local_now.hour != settings.reminder_time.hour:
                continue
            today = local_today(timezone_name, now=now)

            session_today = (
                Session.query
                .join(Curriculum, Session.curriculum_id == Curriculum.id)
                .filter(Session.logged_at == today, Curriculum.user_id == settings.user_id)
                .first()
            )
            if session_today is not None:
                continue  # Already logged something today

            url = f"{base_url}/log" if base_url else "/log"
            try:
                msg = Message(
                    subject="Your curriculum awaits — no session logged today",
                    recipients=[settings.email],
                    body=(
                        "Hey,\n\n"
                        "You haven't logged any time today. Keep the streak alive!\n\n"
                        f"Open the app: {url}\n\n"
                        "— The Curriculum"
                    )
                )
                mail.send(msg)
                logger.info("Sent daily reminder to %s", settings.email)
            except Exception as exc:
                logger.error("Failed to send reminder for %s: %s", settings.email, exc)


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

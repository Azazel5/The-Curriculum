from datetime import date, datetime
from zoneinfo import ZoneInfo


def normalize_timezone_name(timezone_name):
    timezone_name = (timezone_name or 'UTC').strip() or 'UTC'
    try:
        ZoneInfo(timezone_name)
    except Exception:
        return 'UTC'
    return timezone_name


def local_today(timezone_name='UTC', now=None):
    tz_name = normalize_timezone_name(timezone_name)
    now = now or datetime.utcnow()
    return now.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo(tz_name)).date()


def user_timezone_name(user=None):
    settings = getattr(user, 'settings', None) if user is not None else None
    return normalize_timezone_name(getattr(settings, 'timezone', None))


def local_today_for_user(user=None, now=None):
    return local_today(user_timezone_name(user), now=now)


def date_to_html_value(d):
    if isinstance(d, date):
        return d.isoformat()
    return ''

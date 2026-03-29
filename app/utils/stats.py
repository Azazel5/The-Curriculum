from datetime import date, timedelta
from sqlalchemy import func
from app import db
from app.models import Session, Curriculum


def get_heatmap_data(curriculum_id=None):
    """Returns {date_str: total_minutes} for the last 365 days."""
    end = date.today()
    start = end - timedelta(days=364)

    q = (
        db.session.query(
            Session.logged_at,
            func.sum(Session.duration_minutes).label('total')
        )
        .filter(Session.logged_at >= start, Session.logged_at <= end)
    )
    if curriculum_id is not None:
        q = q.filter(Session.curriculum_id == curriculum_id)
    q = q.group_by(Session.logged_at)

    return {row.logged_at.strftime('%Y-%m-%d'): row.total for row in q.all()}


def get_streak():
    today = date.today()
    has_today = db.session.query(Session.id).filter(Session.logged_at == today).first() is not None
    current = today if has_today else today - timedelta(days=1)
    streak = 0
    while True:
        has = db.session.query(Session.id).filter(Session.logged_at == current).first() is not None
        if has:
            streak += 1
            current -= timedelta(days=1)
        else:
            break
    return streak


def get_today_minutes():
    result = (
        db.session.query(func.coalesce(func.sum(Session.duration_minutes), 0))
        .filter(Session.logged_at == date.today())
        .scalar()
    )
    return result or 0


def get_velocity(curriculum, days=30):
    """Average hours per day over last N days."""
    end = date.today()
    start = end - timedelta(days=days)
    total_minutes = (
        db.session.query(func.coalesce(func.sum(Session.duration_minutes), 0))
        .filter(Session.curriculum_id == curriculum.id, Session.logged_at >= start)
        .scalar()
    ) or 0
    return (total_minutes / 60.0) / days


def get_projected_completion(curriculum):
    velocity = get_velocity(curriculum)
    if velocity <= 0:
        return None
    remaining = max(curriculum.mastery_hours - curriculum.total_hours, 0)
    if remaining <= 0:
        return date.today()
    return date.today() + timedelta(days=int(remaining / velocity))


def get_curriculum_time_distribution():
    curricula = Curriculum.query.filter_by(archived=False).all()
    result = []
    for c in curricula:
        total = (
            db.session.query(func.coalesce(func.sum(Session.duration_minutes), 0))
            .filter(Session.curriculum_id == c.id)
            .scalar()
        ) or 0
        if total > 0:
            result.append({'name': c.name, 'color': c.color, 'minutes': total})
    return result


def get_daily_breakdown(days=30):
    end = date.today()
    start = end - timedelta(days=days - 1)
    rows = (
        db.session.query(Session.logged_at, func.sum(Session.duration_minutes).label('total'))
        .filter(Session.logged_at >= start, Session.logged_at <= end)
        .group_by(Session.logged_at).all()
    )
    data = {row.logged_at: row.total for row in rows}
    result = []
    cur = start
    while cur <= end:
        result.append({'date': cur.strftime('%b %d'), 'minutes': data.get(cur, 0)})
        cur += timedelta(days=1)
    return result


def get_weekly_breakdown(weeks=12):
    result = []
    end = date.today()
    for i in range(weeks - 1, -1, -1):
        week_end = end - timedelta(weeks=i)
        week_start = week_end - timedelta(days=6)
        total = (
            db.session.query(func.coalesce(func.sum(Session.duration_minutes), 0))
            .filter(Session.logged_at >= week_start, Session.logged_at <= week_end)
            .scalar()
        ) or 0
        result.append({'week': week_start.strftime('%b %d'), 'minutes': total})
    return result

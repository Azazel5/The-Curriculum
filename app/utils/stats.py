from datetime import date, timedelta
from sqlalchemy import func, and_
from app import db
from app.models import Session, Curriculum, CurriculumItem


def _curriculum_has_active_items(curriculum_id):
    return (
        db.session.query(CurriculumItem.id)
        .filter(
            CurriculumItem.curriculum_id == curriculum_id,
            CurriculumItem.deleted.is_(False),
        )
        .first()
        is not None
    )


def _sum_and_active_days_minutes(curriculum_id, start, end, item_tagged_only):
    """Total minutes and count of distinct days with sessions in [start, end]."""
    filters = [
        Session.curriculum_id == curriculum_id,
        Session.logged_at >= start,
        Session.logged_at <= end,
    ]
    if item_tagged_only:
        filters.append(Session.item_id.isnot(None))

    total = (
        db.session.query(func.coalesce(func.sum(Session.duration_minutes), 0))
        .filter(and_(*filters))
        .scalar()
    )
    total = total or 0

    active_days = (
        db.session.query(func.count(func.distinct(Session.logged_at)))
        .filter(and_(*filters))
        .scalar()
    )
    active_days = active_days or 0
    return total, active_days


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
    """
    Average hours **per day you actually logged time** in the trailing window.

    Total hours in the window ÷ number of distinct calendar days with ≥1 session.
    When the curriculum has roadmap items, uses **item-tagged** sessions first;
    if none in the window, uses all sessions for that curriculum.
    Idle days do not pull this average toward zero.
    """
    end = date.today()
    start = end - timedelta(days=days)

    if _curriculum_has_active_items(curriculum.id):
        total_minutes, active_days = _sum_and_active_days_minutes(
            curriculum.id, start, end, item_tagged_only=True
        )
        if total_minutes == 0:
            total_minutes, active_days = _sum_and_active_days_minutes(
                curriculum.id, start, end, item_tagged_only=False
            )
    else:
        total_minutes, active_days = _sum_and_active_days_minutes(
            curriculum.id, start, end, item_tagged_only=False
        )

    if active_days == 0:
        return 0.0
    return (total_minutes / 60.0) / active_days


def get_projected_completion(curriculum):
    velocity = get_velocity(curriculum)
    if velocity <= 0:
        return None
    remaining = max(curriculum.mastery_hours - curriculum.total_hours, 0)
    if remaining <= 0:
        return date.today()
    days_needed = int(remaining / velocity)
    return date.today() + timedelta(days=max(days_needed, 0))


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

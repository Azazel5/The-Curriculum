"""Shared validation and persistence for manual and API time logging."""
from datetime import date

from app import db
from app.models import Curriculum, CurriculumItem, Session
from app.utils.dates import local_today_for_user


def curriculum_has_time_loggable_items(curriculum_id):
    return (
        db.session.query(CurriculumItem.id)
        .filter(
            CurriculumItem.curriculum_id == curriculum_id,
            CurriculumItem.deleted.is_(False),
        )
        .first()
        is not None
    )


def create_time_session(
    user,
    *,
    curriculum_id,
    item_id=None,
    duration_minutes,
    logged_at=None,
    note=None,
    source='manual',
):
    """
    Create a Session row. Returns (session, curriculum) on success.
    Raises ValueError with a user-facing message on validation failure.
    """
    today = local_today_for_user(user)
    if logged_at is None:
        logged_at = today
    elif isinstance(logged_at, str):
        try:
            logged_at = date.fromisoformat(logged_at)
        except ValueError:
            logged_at = today

    try:
        duration_minutes = int(duration_minutes)
    except (TypeError, ValueError):
        raise ValueError('Duration must be greater than 0') from None
    if duration_minutes <= 0:
        raise ValueError('Duration must be greater than 0')

    curriculum = Curriculum.query.filter_by(
        id=curriculum_id, user_id=user.id, archived=False
    ).first()
    if not curriculum:
        raise ValueError('Invalid curriculum')

    resolved_item_id = None
    needs_item = curriculum_has_time_loggable_items(curriculum.id)

    if item_id:
        try:
            item_id = int(item_id)
        except (TypeError, ValueError):
            item_id = None

    if needs_item:
        if not item_id:
            raise ValueError(
                'Select an item to credit the time precisely (recurring or one-time).'
            )
        item = CurriculumItem.query.filter_by(
            id=item_id, curriculum_id=curriculum.id, deleted=False
        ).first()
        if not item or not item.accepts_time_logging():
            raise ValueError('Invalid item for this curriculum')
        resolved_item_id = item.id
    elif item_id:
        raise ValueError('This curriculum has no time-tracked items; log without an item tag.')

    session = Session(
        curriculum_id=curriculum.id,
        item_id=resolved_item_id,
        duration_minutes=duration_minutes,
        logged_at=logged_at,
        note=(note or None) or None,
        source=source,
    )
    db.session.add(session)
    db.session.commit()
    return session, curriculum

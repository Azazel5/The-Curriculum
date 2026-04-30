import csv
import io
from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from app import db
from app.models import Session, Curriculum, CurriculumItem
from app.forms import SessionForm
from app.utils.dates import local_today_for_user

sessions_bp = Blueprint('sessions', __name__)


def _curriculum_has_time_loggable_items(cid):
    """Any active roadmap row can receive direct time logs."""
    return (
        db.session.query(CurriculumItem.id)
        .filter(
            CurriculumItem.curriculum_id == cid,
            CurriculumItem.deleted.is_(False),
        )
        .first()
        is not None
    )


def _item_choices_for_curriculum(cid):
    if not _curriculum_has_time_loggable_items(cid):
        return [(0, '— no items: log to curriculum only —')]
    items = (
        CurriculumItem.query
        .filter(
            CurriculumItem.curriculum_id == cid,
            CurriculumItem.deleted.is_(False),
        )
        .all()
    )
    far_future = date.max
    items = sorted(
        items,
        key=lambda item: (
            item.deadline or far_future,
            item.sort_order if item.sort_order is not None else 10**9,
            item.id,
        ),
    )
    return [(i.id, i.title) for i in items]


def _populate_form(form):
    curricula = Curriculum.query.filter_by(user_id=current_user.id, archived=False).order_by(Curriculum.name).all()
    form.curriculum_id.choices = [(c.id, c.name) for c in curricula]
    cid = form.curriculum_id.data
    if cid:
        form.item_id.choices = _item_choices_for_curriculum(cid)
    else:
        form.item_id.choices = [(0, '— select a curriculum —')]
    return curricula


def _history_rows_for_user(user_id, start_date=None, end_date=None):
    sessions = (
        Session.query
        .join(Curriculum, Session.curriculum_id == Curriculum.id)
        .filter(Curriculum.user_id == user_id)
        .order_by(Session.logged_at.asc(), Session.created_at.asc(), Session.id.asc())
        .all()
    )
    if start_date or end_date:
        filtered = []
        for s in sessions:
            if start_date and s.logged_at < start_date:
                continue
            if end_date and s.logged_at > end_date:
                continue
            filtered.append(s)
        sessions = filtered

    cumulative_minutes_by_curriculum = {}
    rows = []
    for session in sessions:
        curriculum = session.curriculum
        target_minutes = int((curriculum.mastery_hours or 0) * 60)
        cumulative_minutes = cumulative_minutes_by_curriculum.get(curriculum.id, 0) + session.duration_minutes
        cumulative_minutes_by_curriculum[curriculum.id] = cumulative_minutes

        progress_after_pct = 0.0
        if target_minutes > 0:
            progress_after_pct = min((cumulative_minutes / target_minutes) * 100, 100.0)
        remaining_minutes = max(target_minutes - cumulative_minutes, 0)

        rows.append({
            'date': session.logged_at,
            'project_name': curriculum.project.name if curriculum.project else 'Unassigned',
            'curriculum_name': curriculum.name,
            'item_title': session.item.title if session.item else '',
            'time_logged_minutes': session.duration_minutes,
            'time_logged_display': f'{session.duration_minutes // 60}h {session.duration_minutes % 60}m' if session.duration_minutes >= 60 and session.duration_minutes % 60 else (f'{session.duration_minutes // 60}h' if session.duration_minutes >= 60 and session.duration_minutes % 60 == 0 else f'{session.duration_minutes}m'),
            'progress_after_hours': round(cumulative_minutes / 60.0, 2),
            'progress_after_pct': round(progress_after_pct, 1),
            'remaining_hours': round(remaining_minutes / 60.0, 2),
            'note': session.note or '',
            'source': session.source or 'manual',
        })
    return list(reversed(rows))


@sessions_bp.route('/history')
@login_required
def history():
    today = local_today_for_user(current_user)
    default_start = today.replace(day=1)

    raw_start = (request.args.get('start') or '').strip()
    raw_end = (request.args.get('end') or '').strip()

    start_date = None
    end_date = None
    try:
        start_date = date.fromisoformat(raw_start) if raw_start else default_start
    except ValueError:
        start_date = default_start
    try:
        end_date = date.fromisoformat(raw_end) if raw_end else today
    except ValueError:
        end_date = today

    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date

    rows = _history_rows_for_user(current_user.id, start_date=start_date, end_date=end_date)
    if request.args.get('format') == 'csv':
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            'date',
            'project',
            'curriculum',
            'item',
            'time_logged_minutes',
            'time_logged_display',
            'progress_after_hours',
            'progress_after_pct',
            'remaining_hours',
            'note',
            'source',
        ])
        for row in rows:
            writer.writerow([
                row['date'].isoformat(),
                row['project_name'],
                row['curriculum_name'],
                row['item_title'],
                row['time_logged_minutes'],
                row['time_logged_display'],
                row['progress_after_hours'],
                row['progress_after_pct'],
                row['remaining_hours'],
                row['note'],
                row['source'],
            ])
        return Response(
            buffer.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=curriculum-history.csv'},
        )

    return render_template(
        'sessions/history.html',
        rows=rows,
        today=today,
        start_date=start_date,
        end_date=end_date,
    )


@sessions_bp.route('/log', methods=['GET', 'POST'])
@login_required
def log_session():
    form = SessionForm()
    curricula = _populate_form(form)
    today = local_today_for_user(current_user)

    if not form.is_submitted():
        form.logged_at.data = today

    pre_item = request.args.get('item', type=int)
    preselect = request.args.get('curriculum', type=int)
    if pre_item and not form.is_submitted():
        it = (
            CurriculumItem.query
            .join(Curriculum, CurriculumItem.curriculum_id == Curriculum.id)
            .filter(
                CurriculumItem.id == pre_item,
                CurriculumItem.deleted.is_(False),
                Curriculum.user_id == current_user.id,
            )
            .first()
        )
        if it and it.accepts_time_logging():
            form.curriculum_id.data = it.curriculum_id
            _populate_form(form)
            form.item_id.data = pre_item
    elif preselect and not form.is_submitted():
        c0 = Curriculum.query.filter_by(id=preselect, user_id=current_user.id, archived=False).first()
        if c0:
            form.curriculum_id.data = preselect
        _populate_form(form)

    if request.method == 'POST' and form.curriculum_id.data:
        _populate_form(form)

    if form.validate_on_submit():
        c = Curriculum.query.filter_by(id=form.curriculum_id.data, user_id=current_user.id).first()
        if not c or c.archived:
            flash('Invalid curriculum', 'error')
            return render_template('sessions/log.html', form=form, curricula=curricula)

        needs_item = _curriculum_has_time_loggable_items(c.id)
        item_id = None
        if needs_item:
            if not form.item_id.data:
                flash('Select an item to credit the time precisely (recurring or one-time).', 'error')
                return render_template('sessions/log.html', form=form, curricula=curricula)
            item = CurriculumItem.query.filter_by(
                id=form.item_id.data, curriculum_id=c.id, deleted=False
            ).first()
            if not item or not item.accepts_time_logging():
                flash('Invalid item for this curriculum', 'error')
                return render_template('sessions/log.html', form=form, curricula=curricula)
            item_id = item.id
        else:
            if form.item_id.data:
                flash('This curriculum has no time-tracked items; log without an item tag.', 'error')
                return render_template('sessions/log.html', form=form, curricula=curricula)

        total_minutes = (form.hours.data or 0) * 60 + (form.minutes.data or 0)
        if total_minutes <= 0:
            flash('Duration must be greater than 0', 'error')
        else:
            s = Session(
                curriculum_id=c.id,
                item_id=item_id,
                duration_minutes=total_minutes,
                logged_at=form.logged_at.data or today,
                note=form.note.data or None,
                source='manual',
            )
            db.session.add(s)
            db.session.commit()

            h, m = divmod(total_minutes, 60)
            dur = f'{h}h {m}m' if h and m else (f'{h}h' if h else f'{m}m')
            msg = f'Logged {dur} on {c.name}'
            if item_id:
                msg += f' (item logged)'
            flash(msg, 'success')
            q = {'log_item': item_id} if item_id else {}
            return redirect(url_for('curriculum.curriculum_detail', id=c.id, **q))

    return render_template('sessions/log.html', form=form, curricula=curricula)


@sessions_bp.route('/sessions/<int:id>/delete', methods=['POST'])
@login_required
def delete_session(id):
    s = (
        Session.query
        .join(Curriculum, Session.curriculum_id == Curriculum.id)
        .filter(Session.id == id, Curriculum.user_id == current_user.id)
        .first_or_404()
    )
    db.session.delete(s)
    db.session.commit()
    flash('Session deleted', 'success')
    return redirect(request.referrer or url_for('dashboard.index'))

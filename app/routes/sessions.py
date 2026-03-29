from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db
from app.models import Session, Curriculum, CurriculumItem
from app.forms import SessionForm

sessions_bp = Blueprint('sessions', __name__)


def _populate_form(form):
    curricula = Curriculum.query.filter_by(archived=False).order_by(Curriculum.name).all()
    form.curriculum_id.choices = [(c.id, c.name) for c in curricula]
    # Items populated via AJAX; default to empty + "No item"
    form.item_id.choices = [(0, '— no specific item —')]
    return curricula


@sessions_bp.route('/log', methods=['GET', 'POST'])
def log_session():
    form = SessionForm()
    curricula = _populate_form(form)

    # Pre-select curriculum if passed as query param
    preselect = request.args.get('curriculum', type=int)
    if preselect and not form.is_submitted():
        form.curriculum_id.data = preselect
        items = CurriculumItem.query.filter_by(curriculum_id=preselect, deleted=False).order_by('sort_order').all()
        form.item_id.choices = [(0, '— no specific item —')] + [(i.id, i.title) for i in items]

    if form.validate_on_submit():
        total_minutes = (form.hours.data or 0) * 60 + (form.minutes.data or 0)
        if total_minutes <= 0:
            flash('Duration must be greater than 0', 'error')
        else:
            item_id = form.item_id.data if form.item_id.data and form.item_id.data != 0 else None
            s = Session(
                curriculum_id=form.curriculum_id.data,
                item_id=item_id,
                duration_minutes=total_minutes,
                logged_at=form.logged_at.data or date.today(),
                note=form.note.data or None,
                source='manual'
            )
            db.session.add(s)
            db.session.commit()

            curriculum = Curriculum.query.get(form.curriculum_id.data)
            h, m = divmod(total_minutes, 60)
            dur = f'{h}h {m}m' if h and m else (f'{h}h' if h else f'{m}m')
            flash(f'Logged {dur} on {curriculum.name}', 'success')
            return redirect(url_for('sessions.log_session'))

    return render_template('sessions/log.html', form=form, curricula=curricula)


@sessions_bp.route('/sessions/<int:id>/delete', methods=['POST'])
def delete_session(id):
    s = Session.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    flash('Session deleted', 'success')
    return redirect(request.referrer or url_for('dashboard.index'))

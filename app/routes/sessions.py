from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db
from app.models import Session, Curriculum, CurriculumItem
from app.forms import SessionForm

sessions_bp = Blueprint('sessions', __name__)


def _curriculum_has_items(cid):
    return (
        db.session.query(CurriculumItem.id)
        .filter_by(curriculum_id=cid, deleted=False)
        .first()
        is not None
    )


def _item_choices_for_curriculum(cid):
    items = (
        CurriculumItem.query
        .filter_by(curriculum_id=cid, deleted=False)
        .order_by(CurriculumItem.sort_order, CurriculumItem.id)
        .all()
    )
    if not items:
        return [(0, '— no roadmap items: time applies to curriculum only —')]
    return [(i.id, i.title) for i in items]


def _populate_form(form):
    curricula = Curriculum.query.filter_by(archived=False).order_by(Curriculum.name).all()
    form.curriculum_id.choices = [(c.id, c.name) for c in curricula]
    cid = form.curriculum_id.data
    if cid:
        form.item_id.choices = _item_choices_for_curriculum(cid)
    else:
        form.item_id.choices = [(0, '— select a curriculum —')]
    return curricula


@sessions_bp.route('/log', methods=['GET', 'POST'])
def log_session():
    form = SessionForm()
    curricula = _populate_form(form)

    pre_item = request.args.get('item', type=int)
    preselect = request.args.get('curriculum', type=int)
    if pre_item and not form.is_submitted():
        it = CurriculumItem.query.filter_by(id=pre_item, deleted=False).first()
        if it:
            form.curriculum_id.data = it.curriculum_id
            _populate_form(form)
            form.item_id.data = pre_item
    elif preselect and not form.is_submitted():
        form.curriculum_id.data = preselect
        _populate_form(form)

    if request.method == 'POST' and form.curriculum_id.data:
        _populate_form(form)

    if form.validate_on_submit():
        c = Curriculum.query.get(form.curriculum_id.data)
        if not c or c.archived:
            flash('Invalid curriculum', 'error')
            return render_template('sessions/log.html', form=form, curricula=curricula)

        has_items = _curriculum_has_items(c.id)
        item_id = None
        if has_items:
            if not form.item_id.data:
                flash('Select an item. Progress on this curriculum is tracked per roadmap item.', 'error')
                return render_template('sessions/log.html', form=form, curricula=curricula)
            item = CurriculumItem.query.filter_by(
                id=form.item_id.data, curriculum_id=c.id, deleted=False
            ).first()
            if not item:
                flash('Invalid item for this curriculum', 'error')
                return render_template('sessions/log.html', form=form, curricula=curricula)
            item_id = item.id
        else:
            if form.item_id.data:
                flash('This curriculum has no items; log without an item tag.', 'error')
                return render_template('sessions/log.html', form=form, curricula=curricula)

        total_minutes = (form.hours.data or 0) * 60 + (form.minutes.data or 0)
        if total_minutes <= 0:
            flash('Duration must be greater than 0', 'error')
        else:
            s = Session(
                curriculum_id=c.id,
                item_id=item_id,
                duration_minutes=total_minutes,
                logged_at=form.logged_at.data or date.today(),
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
def delete_session(id):
    s = Session.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    flash('Session deleted', 'success')
    return redirect(request.referrer or url_for('dashboard.index'))

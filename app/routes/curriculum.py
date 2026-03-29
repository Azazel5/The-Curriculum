from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db
from app.models import Curriculum, CurriculumItem, Session
from app.forms import CurriculumForm, CurriculumItemForm
from app.utils.stats import get_velocity, get_projected_completion

curriculum_bp = Blueprint('curriculum', __name__)


@curriculum_bp.route('/curriculums')
def list_curriculums():
    curricula = Curriculum.query.filter_by(archived=False).order_by(Curriculum.created_at).all()
    return render_template('curriculum/list.html', curricula=curricula)


@curriculum_bp.route('/curriculums/new', methods=['GET', 'POST'])
def new_curriculum():
    form = CurriculumForm()
    if form.validate_on_submit():
        c = Curriculum(
            name=form.name.data,
            description=form.description.data,
            mastery_hours=form.mastery_hours.data,
            color=form.color.data or '#6366f1'
        )
        db.session.add(c)
        db.session.commit()
        flash(f'Created "{c.name}"', 'success')
        return redirect(url_for('curriculum.curriculum_detail', id=c.id))
    return render_template('curriculum/new.html', form=form)


@curriculum_bp.route('/curriculums/<int:id>', methods=['GET', 'POST'])
def curriculum_detail(id):
    c = Curriculum.query.get_or_404(id)
    form = CurriculumForm(obj=c)
    item_form = CurriculumItemForm()

    if form.validate_on_submit() and 'save_curriculum' in request.form:
        c.name = form.name.data
        c.description = form.description.data
        c.mastery_hours = form.mastery_hours.data
        c.color = form.color.data or '#6366f1'
        db.session.commit()
        flash('Saved', 'success')
        return redirect(url_for('curriculum.curriculum_detail', id=id))

    today = date.today()
    items = c.items.filter_by(deleted=False).order_by(CurriculumItem.sort_order, CurriculumItem.id).all()

    # Recent sessions (last 10)
    recent_sessions = (
        Session.query
        .filter_by(curriculum_id=id)
        .order_by(Session.logged_at.desc(), Session.created_at.desc())
        .limit(10).all()
    )

    velocity = get_velocity(c)
    projected = get_projected_completion(c)

    return render_template(
        'curriculum/detail.html',
        curriculum=c,
        form=form,
        item_form=item_form,
        items=items,
        recent_sessions=recent_sessions,
        velocity=velocity,
        projected=projected,
        today=today,
    )


@curriculum_bp.route('/curriculums/<int:id>/delete', methods=['POST'])
def delete_curriculum(id):
    c = Curriculum.query.get_or_404(id)
    c.archived = True
    db.session.commit()
    flash(f'Archived "{c.name}"', 'success')
    return redirect(url_for('curriculum.list_curriculums'))


# ── Item CRUD ────────────────────────────────────────────────────────────────

@curriculum_bp.route('/curriculums/<int:id>/items', methods=['POST'])
def add_item(id):
    c = Curriculum.query.get_or_404(id)
    title = request.form.get('title', '').strip()
    if not title:
        flash('Item title is required', 'error')
        return redirect(url_for('curriculum.curriculum_detail', id=id))

    deadline_str = request.form.get('deadline', '').strip()
    hours_str = request.form.get('hours_target', '').strip()

    deadline = None
    if deadline_str:
        try:
            deadline = date.fromisoformat(deadline_str)
        except ValueError:
            pass

    hours_target = None
    if hours_str:
        try:
            hours_target = float(hours_str)
        except ValueError:
            pass

    # Max sort_order + 1
    max_order = db.session.query(db.func.max(CurriculumItem.sort_order))\
        .filter_by(curriculum_id=id).scalar() or 0

    item = CurriculumItem(
        curriculum_id=id,
        title=title,
        description=request.form.get('description', '').strip() or None,
        deadline=deadline,
        hours_target=hours_target,
        sort_order=max_order + 1
    )
    db.session.add(item)
    db.session.commit()
    return redirect(url_for('curriculum.curriculum_detail', id=id) + '#items')


@curriculum_bp.route('/curriculums/<int:id>/items/<int:iid>/complete', methods=['POST'])
def toggle_item(id, iid):
    item = CurriculumItem.query.filter_by(id=iid, curriculum_id=id, deleted=False).first_or_404()
    item.completed = not item.completed
    item.completed_at = datetime.utcnow() if item.completed else None
    db.session.commit()
    return redirect(url_for('curriculum.curriculum_detail', id=id) + '#items')


@curriculum_bp.route('/curriculums/<int:id>/items/<int:iid>/edit', methods=['POST'])
def edit_item(id, iid):
    item = CurriculumItem.query.filter_by(id=iid, curriculum_id=id, deleted=False).first_or_404()
    title = request.form.get('title', '').strip()
    if title:
        item.title = title
    item.description = request.form.get('description', '').strip() or None

    deadline_str = request.form.get('deadline', '').strip()
    item.deadline = date.fromisoformat(deadline_str) if deadline_str else None

    hours_str = request.form.get('hours_target', '').strip()
    try:
        item.hours_target = float(hours_str) if hours_str else None
    except ValueError:
        pass

    db.session.commit()
    return redirect(url_for('curriculum.curriculum_detail', id=id) + '#items')


@curriculum_bp.route('/curriculums/<int:id>/items/<int:iid>/delete', methods=['POST'])
def delete_item(id, iid):
    item = CurriculumItem.query.filter_by(id=iid, curriculum_id=id).first_or_404()
    item.deleted = True
    db.session.commit()
    return redirect(url_for('curriculum.curriculum_detail', id=id) + '#items')

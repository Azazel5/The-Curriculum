from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db
from app.models import Curriculum, CurriculumItem, Session, Project
from app.forms import CurriculumForm, CurriculumItemForm, ProjectForm
from app.utils.stats import get_velocity, get_projected_completion

curriculum_bp = Blueprint('curriculum', __name__)


@curriculum_bp.route('/curriculums')
def list_curriculums():
    curricula = Curriculum.query.filter_by(archived=False).order_by(Curriculum.project_id, Curriculum.created_at).all()
    grouped = []
    project_map = {}
    for c in curricula:
        key = c.project or None
        if key not in project_map:
            project_map[key] = []
        project_map[key].append(c)
    for project, currs in sorted(project_map.items(), key=lambda kv: (kv[0].name if kv[0] else '')):
        grouped.append({'project': project, 'curricula': currs})
    return render_template('curriculum/list.html', grouped_curricula=grouped)


def _populate_project_choices(form):
    projects = Project.query.order_by(Project.name).all()
    form.project_id.choices = [(0, '— none —')] + [(p.id, p.name) for p in projects]
    return projects


@curriculum_bp.route('/curriculums/new', methods=['GET', 'POST'])
def new_curriculum():
    form = CurriculumForm()
    _populate_project_choices(form)
    if form.validate_on_submit():
        project_id = form.project_id.data if form.project_id.data else None
        c = Curriculum(
            project_id=project_id,
            name=form.name.data,
            description=form.description.data,
            mastery_hours=form.mastery_hours.data,
            status=form.status.data,
            start_date=form.start_date.data,
            target_completion_date=form.target_completion_date.data,
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
    _populate_project_choices(form)
    if not form.is_submitted():
        form.project_id.data = c.project_id or 0
    item_form = CurriculumItemForm()

    if form.validate_on_submit() and 'save_curriculum' in request.form:
        c.project_id = form.project_id.data if form.project_id.data else None
        c.name = form.name.data
        c.description = form.description.data
        c.mastery_hours = form.mastery_hours.data
        c.status = form.status.data
        c.start_date = form.start_date.data
        c.target_completion_date = form.target_completion_date.data
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

    highlight_item_id = request.args.get('log_item', type=int)

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
        highlight_item_id=highlight_item_id,
    )


@curriculum_bp.route('/curriculums/<int:id>/delete', methods=['POST'])
def delete_curriculum(id):
    c = Curriculum.query.get_or_404(id)
    c.archived = True
    c.status = 'archived'
    db.session.commit()
    flash(f'Archived "{c.name}"', 'success')
    return redirect(url_for('curriculum.list_curriculums'))


@curriculum_bp.route('/projects')
def list_projects():
    # The dashboard (/) is the projects home. Keep this route for backwards
    # compatibility and bookmarks, but avoid maintaining a duplicated page.
    return redirect(url_for('dashboard.index'))


@curriculum_bp.route('/projects/<int:id>')
def project_detail(id):
    project = Project.query.get_or_404(id)
    curricula = project.curricula.filter_by(archived=False).order_by(Curriculum.created_at).all()
    return render_template('project/detail.html', project=project, curricula=curricula)


@curriculum_bp.route('/projects/new', methods=['GET', 'POST'])
def new_project():
    form = ProjectForm()
    if form.validate_on_submit():
        p = Project(
            name=form.name.data,
            description=form.description.data,
            color=form.color.data or '#6366f1'
        )
        db.session.add(p)
        db.session.commit()
        flash(f'Created project "{p.name}"', 'success')
        return redirect(url_for('dashboard.index') + f'?project={p.id}')
    return render_template('project/new.html', form=form)


# ── Item CRUD ────────────────────────────────────────────────────────────────

@curriculum_bp.route('/curriculums/<int:id>/items', methods=['POST'])
def add_item(id):
    c = Curriculum.query.get_or_404(id)
    title = request.form.get('title', '').strip()
    if not title:
        flash('Item title is required', 'error')
        return redirect(url_for('curriculum.curriculum_detail', id=id))

    deadline_str = request.form.get('deadline', '').strip()

    deadline = None
    if deadline_str:
        try:
            deadline = date.fromisoformat(deadline_str)
        except ValueError:
            pass

    kind = request.form.get('item_kind', CurriculumItem.KIND_ONE_SHOT)
    if kind not in (CurriculumItem.KIND_ONE_SHOT, CurriculumItem.KIND_DAILY):
        kind = CurriculumItem.KIND_ONE_SHOT

    max_order = db.session.query(db.func.max(CurriculumItem.sort_order))\
        .filter_by(curriculum_id=id).scalar() or 0

    item = CurriculumItem(
        curriculum_id=id,
        title=title,
        description=request.form.get('description', '').strip() or None,
        deadline=deadline,
        item_kind=kind,
        sort_order=max_order + 1
    )
    db.session.add(item)
    db.session.commit()
    return redirect(url_for('curriculum.curriculum_detail', id=id) + '#items')


@curriculum_bp.route('/curriculums/<int:cid>/items/<int:item_id>/complete', methods=['GET', 'POST'])
def toggle_item(cid, item_id):
    """Use cid/item_id in the path so url_for(..., cid=, item_id=) never collides with reserved args."""
    if request.method == 'GET':
        return redirect(url_for('curriculum.curriculum_detail', id=cid) + '#items')
    item = CurriculumItem.query.filter_by(id=item_id, curriculum_id=cid, deleted=False).first_or_404()
    today = date.today()
    if item.item_kind == CurriculumItem.KIND_DAILY:
        if item.daily_completed_on == today:
            item.daily_completed_on = None
        else:
            item.daily_completed_on = today
    else:
        item.completed = not item.completed
        item.completed_at = datetime.utcnow() if item.completed else None
    db.session.commit()
    return redirect(url_for('curriculum.curriculum_detail', id=cid) + '#items')


@curriculum_bp.route('/curriculums/<int:id>/items/<int:iid>/edit', methods=['POST'])
def edit_item(id, iid):
    item = CurriculumItem.query.filter_by(id=iid, curriculum_id=id, deleted=False).first_or_404()
    title = request.form.get('title', '').strip()
    if title:
        item.title = title
    item.description = request.form.get('description', '').strip() or None

    deadline_str = request.form.get('deadline', '').strip()
    item.deadline = date.fromisoformat(deadline_str) if deadline_str else None

    prev_kind = item.item_kind
    kind = request.form.get('item_kind', item.item_kind)
    if kind in (CurriculumItem.KIND_ONE_SHOT, CurriculumItem.KIND_DAILY):
        item.item_kind = kind
    if prev_kind != item.item_kind:
        item.completed = False
        item.completed_at = None
        item.daily_completed_on = None

    db.session.commit()
    return redirect(url_for('curriculum.curriculum_detail', id=id) + '#items')


@curriculum_bp.route('/curriculums/<int:id>/items/<int:iid>/delete', methods=['POST'])
def delete_item(id, iid):
    item = CurriculumItem.query.filter_by(id=iid, curriculum_id=id).first_or_404()
    item.deleted = True
    db.session.commit()
    return redirect(url_for('curriculum.curriculum_detail', id=id) + '#items')

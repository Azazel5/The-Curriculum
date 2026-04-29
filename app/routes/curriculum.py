from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Curriculum, CurriculumItem, Session, Project, ItemActivityDay
from app.forms import CurriculumForm, CurriculumItemForm, ProjectForm
from app.utils.dates import local_today_for_user
from app.utils.stats import get_velocity, get_projected_completion

curriculum_bp = Blueprint('curriculum', __name__)


def _parse_item_completion_fields(request_form, item_kind):
    """Returns (completion_style, daily_target_minutes or None). Only meaningful for daily items."""
    style = request_form.get('completion_style', CurriculumItem.STYLE_PRESENCE)
    if style not in (CurriculumItem.STYLE_PRESENCE, CurriculumItem.STYLE_TIME_THRESHOLD):
        style = CurriculumItem.STYLE_PRESENCE
    raw = request_form.get('daily_target_minutes', '').strip()
    minutes = None
    if raw:
        try:
            minutes = max(1, int(raw))
        except ValueError:
            minutes = None
    if item_kind != CurriculumItem.KIND_DAILY:
        return CurriculumItem.STYLE_PRESENCE, None
    if style == CurriculumItem.STYLE_TIME_THRESHOLD:
        return CurriculumItem.STYLE_TIME_THRESHOLD, minutes
    return CurriculumItem.STYLE_PRESENCE, None


@curriculum_bp.route('/curriculums')
@login_required
def list_curriculums():
    curricula = Curriculum.query.filter_by(user_id=current_user.id, archived=False).order_by(
        Curriculum.project_id, Curriculum.created_at
    ).all()
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
    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.name).all()
    form.project_id.choices = [(0, '— none —')] + [(p.id, p.name) for p in projects]
    return projects


@curriculum_bp.route('/curriculums/new', methods=['GET', 'POST'])
@login_required
def new_curriculum():
    form = CurriculumForm()
    _populate_project_choices(form)
    if form.validate_on_submit():
        project_id = form.project_id.data if form.project_id.data else None
        if project_id:
            project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
            if not project:
                flash('Invalid project', 'error')
                return render_template('curriculum/new.html', form=form)
        c = Curriculum(
            user_id=current_user.id,
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
@login_required
def curriculum_detail(id):
    c = Curriculum.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = CurriculumForm(obj=c)
    _populate_project_choices(form)
    if not form.is_submitted():
        form.project_id.data = c.project_id or 0
    item_form = CurriculumItemForm()

    if form.validate_on_submit() and 'save_curriculum' in request.form:
        new_project_id = form.project_id.data if form.project_id.data else None
        if new_project_id:
            project = Project.query.filter_by(id=new_project_id, user_id=current_user.id).first()
            if not project:
                flash('Invalid project', 'error')
                return redirect(url_for('curriculum.curriculum_detail', id=id))
        c.project_id = new_project_id
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

    today = local_today_for_user(current_user)
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
@login_required
def delete_curriculum(id):
    c = Curriculum.query.filter_by(id=id, user_id=current_user.id).first_or_404()
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
@login_required
def project_detail(id):
    project = Project.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    curricula = project.curricula.filter_by(archived=False).order_by(Curriculum.created_at).all()
    return render_template('project/detail.html', project=project, curricula=curricula)


@curriculum_bp.route('/projects/new', methods=['GET', 'POST'])
@login_required
def new_project():
    form = ProjectForm()
    if form.validate_on_submit():
        p = Project(
            user_id=current_user.id,
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
@login_required
def add_item(id):
    c = Curriculum.query.filter_by(id=id, user_id=current_user.id).first_or_404()
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

    comp_style, tgt_min = _parse_item_completion_fields(request.form, kind)
    if kind == CurriculumItem.KIND_DAILY and comp_style == CurriculumItem.STYLE_TIME_THRESHOLD:
        if tgt_min is None:
            flash('Time-based daily items need a daily target (minutes).', 'error')
            return redirect(url_for('curriculum.curriculum_detail', id=id) + '#items')

    max_order = db.session.query(db.func.max(CurriculumItem.sort_order))\
        .filter_by(curriculum_id=id).scalar() or 0

    item = CurriculumItem(
        curriculum_id=id,
        title=title,
        description=request.form.get('description', '').strip() or None,
        deadline=deadline,
        item_kind=kind,
        completion_style=comp_style,
        daily_target_minutes=tgt_min,
        sort_order=max_order + 1
    )
    db.session.add(item)
    db.session.commit()
    return redirect(url_for('curriculum.curriculum_detail', id=id) + '#items')


@curriculum_bp.route('/curriculums/<int:cid>/items/<int:item_id>/complete', methods=['GET', 'POST'])
@login_required
def toggle_item(cid, item_id):
    """Use cid/item_id in the path so url_for(..., cid=, item_id=) never collides with reserved args."""
    if request.method == 'GET':
        return redirect(url_for('curriculum.curriculum_detail', id=cid) + '#items')
    item = (
        CurriculumItem.query
        .join(Curriculum, CurriculumItem.curriculum_id == Curriculum.id)
        .filter(
            CurriculumItem.id == item_id,
            CurriculumItem.curriculum_id == cid,
            CurriculumItem.deleted.is_(False),
            Curriculum.user_id == current_user.id,
        )
        .first_or_404()
    )
    today = local_today_for_user(current_user)
    if item.item_kind == CurriculumItem.KIND_DAILY and item.is_time_threshold_daily():
        flash('This item completes automatically when today’s logged time on it meets or exceeds the target.', 'info')
        return redirect(url_for('curriculum.curriculum_detail', id=cid) + '#items')
    if item.item_kind == CurriculumItem.KIND_DAILY:
        if item.daily_completed_on == today:
            item.daily_completed_on = None
            ItemActivityDay.query.filter_by(item_id=item.id, activity_date=today).delete()
        else:
            item.daily_completed_on = today
            if not ItemActivityDay.query.filter_by(item_id=item.id, activity_date=today).first():
                db.session.add(ItemActivityDay(item_id=item.id, activity_date=today))
    else:
        item.completed = not item.completed
        item.completed_at = datetime.utcnow() if item.completed else None
    db.session.commit()
    return redirect(url_for('curriculum.curriculum_detail', id=cid) + '#items')


@curriculum_bp.route('/curriculums/<int:id>/items/<int:iid>/edit', methods=['POST'])
@login_required
def edit_item(id, iid):
    item = (
        CurriculumItem.query
        .join(Curriculum, CurriculumItem.curriculum_id == Curriculum.id)
        .filter(
            CurriculumItem.id == iid,
            CurriculumItem.curriculum_id == id,
            CurriculumItem.deleted.is_(False),
            Curriculum.user_id == current_user.id,
        )
        .first_or_404()
    )
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

    comp_style, tgt_min = _parse_item_completion_fields(request.form, item.item_kind)
    if item.item_kind == CurriculumItem.KIND_DAILY:
        item.completion_style = comp_style
        if comp_style == CurriculumItem.STYLE_TIME_THRESHOLD:
            if tgt_min is not None:
                item.daily_target_minutes = tgt_min
            elif item.daily_target_minutes is None:
                flash('Set daily target minutes for time-based daily items.', 'error')
                return redirect(url_for('curriculum.curriculum_detail', id=id) + '#items')
        else:
            item.daily_target_minutes = None
    else:
        item.completion_style = CurriculumItem.STYLE_PRESENCE
        item.daily_target_minutes = None

    if prev_kind != item.item_kind:
        item.completed = False
        item.completed_at = None
        item.daily_completed_on = None

    db.session.commit()
    return redirect(url_for('curriculum.curriculum_detail', id=id) + '#items')


@curriculum_bp.route('/curriculums/<int:id>/items/<int:iid>/delete', methods=['POST'])
@login_required
def delete_item(id, iid):
    item = (
        CurriculumItem.query
        .join(Curriculum, CurriculumItem.curriculum_id == Curriculum.id)
        .filter(
            CurriculumItem.id == iid,
            CurriculumItem.curriculum_id == id,
            Curriculum.user_id == current_user.id,
        )
        .first_or_404()
    )
    item.deleted = True
    db.session.commit()
    return redirect(url_for('curriculum.curriculum_detail', id=id) + '#items')

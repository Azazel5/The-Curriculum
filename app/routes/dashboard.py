from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Curriculum, Project
from app.utils.dates import local_today_for_user
from app.utils.dashboard_view import gather_dashboard_view_context
from app.utils.stats import (
    get_daily_breakdown, get_weekly_breakdown, get_velocity, get_projected_completion
)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    legacy_pid = request.args.get('project', type=int)
    if legacy_pid:
        legacy = Project.query.filter_by(id=legacy_pid, user_id=current_user.id).first()
        if legacy:
            return redirect(url_for('curriculum.project_detail', id=legacy.id))
    ctx = gather_dashboard_view_context(current_user, None)
    return render_template('dashboard/index.html', **ctx)


@dashboard_bp.route('/insights')
@login_required
def insights():
    today = local_today_for_user(current_user)
    project_id = request.args.get('project', type=int)
    curriculum_id = request.args.get('curriculum', type=int)

    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.name).all()
    selected_project = (
        Project.query.filter_by(id=project_id, user_id=current_user.id).first()
        if project_id
        else None
    )

    curricula_q = Curriculum.query.filter_by(user_id=current_user.id, archived=False)
    if selected_project:
        curricula_q = curricula_q.filter(Curriculum.project_id == selected_project.id)
    curricula = curricula_q.order_by(Curriculum.created_at).all()

    selected_curriculum = None
    if curriculum_id:
        selected_curriculum = Curriculum.query.filter_by(id=curriculum_id, user_id=current_user.id).first()
        if selected_curriculum and selected_project and selected_curriculum.project_id != selected_project.id:
            selected_curriculum = None

    daily = get_daily_breakdown(
        30,
        user_id=current_user.id,
        project_id=selected_project.id if selected_project else None,
        curriculum_id=selected_curriculum.id if selected_curriculum else None,
        today=today,
    )
    weekly = get_weekly_breakdown(
        12,
        user_id=current_user.id,
        project_id=selected_project.id if selected_project else None,
        curriculum_id=selected_curriculum.id if selected_curriculum else None,
        today=today,
    )

    curriculum_stats = []
    for c in ([selected_curriculum] if selected_curriculum else curricula):
        if c is None:
            continue
        velocity = get_velocity(c)
        projected = get_projected_completion(c)
        curriculum_stats.append({
            'curriculum': c,
            'velocity_h': round(velocity, 2),
            'projected': projected,
        })
    curriculum_stats.sort(key=lambda x: x['curriculum'].progress_pct, reverse=True)

    return render_template(
        'dashboard/insights.html',
        projects=projects,
        selected_project=selected_project,
        curricula=curricula,
        selected_curriculum=selected_curriculum,
        daily=daily,
        weekly=weekly,
        curriculum_stats=curriculum_stats,
        today=today,
    )

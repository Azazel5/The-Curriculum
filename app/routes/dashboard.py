from datetime import date as date_type
from flask import Blueprint, render_template, request
from app import db
from app.models import Curriculum, Session, Project
from app.utils.stats import (
    get_streak, get_today_minutes, get_curriculum_time_distribution,
    get_daily_breakdown, get_weekly_breakdown, get_velocity, get_projected_completion
)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    project_id = request.args.get('project', type=int)
    selected_project = Project.query.get(project_id) if project_id else None

    projects = Project.query.order_by(Project.name).all()
    project_cards = []
    for p in projects:
        project_cards.append({
            'project': p,
            'streak': get_streak(project_id=p.id),
            'today_minutes': get_today_minutes(project_id=p.id),
        })

    streak = get_streak(project_id=selected_project.id) if selected_project else None
    today_minutes = get_today_minutes(project_id=selected_project.id) if selected_project else None

    curricula_q = Curriculum.query.filter_by(archived=False).order_by(Curriculum.created_at)
    if selected_project:
        curricula_q = curricula_q.filter(Curriculum.project_id == selected_project.id)
    curricula = curricula_q.all()

    time_dist = get_curriculum_time_distribution(project_id=selected_project.id if selected_project else None)

    today = date_type.today()
    today_sessions_q = Session.query.filter(Session.logged_at == today)
    if selected_project:
        today_sessions_q = today_sessions_q.join(Curriculum, Session.curriculum_id == Curriculum.id)\
            .filter(Curriculum.project_id == selected_project.id)
    today_sessions = today_sessions_q.order_by(Session.created_at.desc()).all()

    return render_template(
        'dashboard/index.html',
        projects=projects,
        selected_project=selected_project,
        project_cards=project_cards,
        streak=streak,
        today_minutes=today_minutes,
        curricula=curricula,
        time_dist=time_dist,
        today_sessions=today_sessions,
        today=today,
    )


@dashboard_bp.route('/insights')
def insights():
    project_id = request.args.get('project', type=int)
    curriculum_id = request.args.get('curriculum', type=int)

    projects = Project.query.order_by(Project.name).all()
    selected_project = Project.query.get(project_id) if project_id else None

    curricula_q = Curriculum.query.filter_by(archived=False)
    if selected_project:
        curricula_q = curricula_q.filter(Curriculum.project_id == selected_project.id)
    curricula = curricula_q.order_by(Curriculum.created_at).all()

    selected_curriculum = None
    if curriculum_id:
        selected_curriculum = Curriculum.query.get(curriculum_id)
        if selected_curriculum and selected_project and selected_curriculum.project_id != selected_project.id:
            selected_curriculum = None

    daily = get_daily_breakdown(
        30,
        project_id=selected_project.id if selected_project else None,
        curriculum_id=selected_curriculum.id if selected_curriculum else None,
    )
    weekly = get_weekly_breakdown(
        12,
        project_id=selected_project.id if selected_project else None,
        curriculum_id=selected_curriculum.id if selected_curriculum else None,
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
        today=date_type.today(),
    )

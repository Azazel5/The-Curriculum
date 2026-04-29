from datetime import date as date_type
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app import db
from app.models import Curriculum, Session, Project, CurriculumItem
from app.utils.dates import local_today_for_user
from app.utils.stats import (
    get_streak, get_today_minutes, get_curriculum_time_distribution,
    get_daily_breakdown, get_weekly_breakdown, get_velocity, get_projected_completion
)

dashboard_bp = Blueprint('dashboard', __name__)


def _deadline_delta(deadline, today):
    if deadline is None:
        return 10**6
    return (deadline - today).days


@dashboard_bp.route('/')
@login_required
def index():
    today = local_today_for_user(current_user)
    project_id = request.args.get('project', type=int)
    selected_project = (
        Project.query.filter_by(id=project_id, user_id=current_user.id).first()
        if project_id
        else None
    )

    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.name).all()
    project_cards = []
    for p in projects:
        project_cards.append({
            'project': p,
            'streak': get_streak(user_id=current_user.id, project_id=p.id, today=today),
            'today_minutes': get_today_minutes(user_id=current_user.id, project_id=p.id, today=today),
        })

    streak = get_streak(user_id=current_user.id, project_id=selected_project.id, today=today) if selected_project else None
    today_minutes = get_today_minutes(user_id=current_user.id, project_id=selected_project.id, today=today) if selected_project else None

    curricula_q = Curriculum.query.filter_by(user_id=current_user.id, archived=False).order_by(Curriculum.created_at)
    if selected_project:
        curricula_q = curricula_q.filter(Curriculum.project_id == selected_project.id)
    curricula = curricula_q.all()

    time_dist = get_curriculum_time_distribution(
        user_id=current_user.id,
        project_id=selected_project.id if selected_project else None,
    )

    today_sessions_q = Session.query.join(Curriculum, Session.curriculum_id == Curriculum.id).filter(
        Session.logged_at == today,
        Curriculum.user_id == current_user.id,
    )
    if selected_project:
        today_sessions_q = today_sessions_q.filter(Curriculum.project_id == selected_project.id)
    today_sessions = today_sessions_q.order_by(Session.created_at.desc()).all()

    focus_q = (
        CurriculumItem.query
        .join(Curriculum, CurriculumItem.curriculum_id == Curriculum.id)
        .filter(
            Curriculum.user_id == current_user.id,
            Curriculum.archived.is_(False),
            CurriculumItem.deleted.is_(False),
        )
    )
    if selected_project:
        focus_q = focus_q.filter(Curriculum.project_id == selected_project.id)
    focus_items = focus_q.order_by(CurriculumItem.sort_order, CurriculumItem.id).all()

    recurring_focus = []
    one_time_focus = []
    one_time_overdue = 0
    recurring_overdue = 0
    for item in focus_items:
        delta = _deadline_delta(item.deadline, today)
        if item.item_kind == CurriculumItem.KIND_DAILY:
            if item.is_daily_done_today:
                continue
            remaining = max((item.daily_target_minutes or 0) - item.minutes_logged_on(today), 0)
            recurring_focus.append({
                'item': item,
                'curriculum': item.curriculum,
                'deadline_delta': delta,
                'today_minutes': item.minutes_logged_on(today),
                'target_minutes': item.daily_target_minutes or 0,
                'remaining_minutes': remaining,
            })
            if item.deadline and delta < 0:
                recurring_overdue += 1
        else:
            if item.is_one_shot_done:
                continue
            remaining = max((item.one_time_target_minutes or 0) - item.total_minutes_logged, 0)
            one_time_focus.append({
                'item': item,
                'curriculum': item.curriculum,
                'deadline_delta': delta,
                'total_minutes': item.total_minutes_logged,
                'target_minutes': item.one_time_target_minutes or 0,
                'remaining_minutes': remaining,
            })
            if item.deadline and delta < 0:
                one_time_overdue += 1

    recurring_focus.sort(key=lambda row: (row['deadline_delta'], -row['remaining_minutes']))
    one_time_focus.sort(key=lambda row: (row['deadline_delta'], -row['remaining_minutes']))

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
        recurring_focus=recurring_focus,
        one_time_focus=one_time_focus,
        one_time_overdue=one_time_overdue,
        recurring_overdue=recurring_overdue,
    )


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

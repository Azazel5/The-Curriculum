"""Shared context for the home dashboard and per-project dashboard views."""
from app.models import Curriculum, Session, Project, CurriculumItem
from app.utils.dates import local_today_for_user
from app.utils.stats import (
    get_streak,
    get_today_minutes,
    get_curriculum_time_distribution,
)


def _deadline_delta(deadline, today):
    if deadline is None:
        return 10**6
    return (deadline - today).days


def gather_dashboard_view_context(user, selected_project=None):
    """
    Build template variables for Today Focus, heatmap data inputs, curricula list,
    time distribution, and today's sessions. When selected_project is None, all
    queries span every project the user owns.
    """
    today = local_today_for_user(user)

    projects = Project.query.filter_by(user_id=user.id).order_by(Project.name).all()
    project_cards = []
    for p in projects:
        project_cards.append({
            'project': p,
            'streak': get_streak(user_id=user.id, project_id=p.id, today=today),
            'today_minutes': get_today_minutes(user_id=user.id, project_id=p.id, today=today),
        })

    streak = get_streak(user_id=user.id, project_id=selected_project.id, today=today) if selected_project else None
    today_minutes = get_today_minutes(user_id=user.id, project_id=selected_project.id, today=today) if selected_project else None

    curricula_q = Curriculum.query.filter_by(user_id=user.id, archived=False).order_by(Curriculum.created_at)
    if selected_project:
        curricula_q = curricula_q.filter(Curriculum.project_id == selected_project.id)
    curricula = curricula_q.all()

    time_dist = get_curriculum_time_distribution(
        user_id=user.id,
        project_id=selected_project.id if selected_project else None,
    )

    today_sessions_q = Session.query.join(Curriculum, Session.curriculum_id == Curriculum.id).filter(
        Session.logged_at == today,
        Curriculum.user_id == user.id,
    )
    if selected_project:
        today_sessions_q = today_sessions_q.filter(Curriculum.project_id == selected_project.id)
    today_sessions = today_sessions_q.order_by(Session.created_at.desc()).all()

    focus_q = (
        CurriculumItem.query
        .join(Curriculum, CurriculumItem.curriculum_id == Curriculum.id)
        .filter(
            Curriculum.user_id == user.id,
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
            done = bool(item.is_one_shot_done)
            if done and delta < 0:
                continue
            remaining = max((item.one_time_target_minutes or 0) - item.total_minutes_logged, 0)
            one_time_focus.append({
                'item': item,
                'curriculum': item.curriculum,
                'deadline_delta': delta,
                'total_minutes': item.total_minutes_logged,
                'target_minutes': item.one_time_target_minutes or 0,
                'remaining_minutes': remaining,
                'focus_complete': done,
            })
            if item.deadline and delta < 0 and not done:
                one_time_overdue += 1

    recurring_focus.sort(key=lambda row: (row['deadline_delta'], -row['remaining_minutes']))

    def _one_time_focus_sort_key(row):
        if row['focus_complete']:
            return (1, -row['item'].id)
        return (0, row['deadline_delta'], -row['remaining_minutes'])

    one_time_focus.sort(key=_one_time_focus_sort_key)
    one_time_open_count = sum(1 for row in one_time_focus if not row['focus_complete'])
    one_time_done_count = sum(1 for row in one_time_focus if row['focus_complete'])

    return {
        'projects': projects,
        'project_cards': project_cards,
        'selected_project': selected_project,
        'streak': streak,
        'today_minutes': today_minutes,
        'curricula': curricula,
        'time_dist': time_dist,
        'today_sessions': today_sessions,
        'today': today,
        'recurring_focus': recurring_focus,
        'one_time_focus': one_time_focus,
        'one_time_open_count': one_time_open_count,
        'one_time_done_count': one_time_done_count,
        'one_time_overdue': one_time_overdue,
        'recurring_overdue': recurring_overdue,
    }

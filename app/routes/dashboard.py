from datetime import date as date_type
from flask import Blueprint, render_template
from app import db
from app.models import Curriculum, Session
from app.utils.stats import (
    get_streak, get_today_minutes, get_curriculum_time_distribution,
    get_daily_breakdown, get_weekly_breakdown, get_velocity, get_projected_completion
)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    streak = get_streak()
    today_minutes = get_today_minutes()
    curricula = Curriculum.query.filter_by(archived=False).order_by(Curriculum.created_at).all()
    time_dist = get_curriculum_time_distribution()

    today = date_type.today()
    today_sessions = (
        Session.query
        .filter(Session.logged_at == today)
        .order_by(Session.created_at.desc())
        .all()
    )

    return render_template(
        'dashboard/index.html',
        streak=streak,
        today_minutes=today_minutes,
        curricula=curricula,
        time_dist=time_dist,
        today_sessions=today_sessions,
        today=today,
    )


@dashboard_bp.route('/insights')
def insights():
    daily = get_daily_breakdown(30)
    weekly = get_weekly_breakdown(12)
    curricula = Curriculum.query.filter_by(archived=False).all()

    curriculum_stats = []
    for c in curricula:
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
        daily=daily,
        weekly=weekly,
        curriculum_stats=curriculum_stats,
        today=date_type.today(),
    )

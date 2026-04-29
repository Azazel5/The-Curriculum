from datetime import datetime, date
from sqlalchemy import func, and_, or_
from app import db
from app.utils.dates import local_today_for_user
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = 'app_user'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    is_guest = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    projects = db.relationship('Project', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    curricula = db.relationship('Curriculum', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    settings = db.relationship('Settings', backref='user', uselist=False, cascade='all, delete-orphan')


class Settings(db.Model):
    __tablename__ = 'settings'
    __table_args__ = (db.UniqueConstraint('user_id', name='uq_settings_user_id'),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('app_user.id', ondelete='CASCADE'), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=True)
    reminder_time = db.Column(db.Time, nullable=True)
    reminder_active = db.Column(db.Boolean, default=True)
    timezone = db.Column(db.String(50), default='UTC')


class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('app_user.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(7), default='#6366f1')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    curricula = db.relationship('Curriculum', backref='project', lazy='dynamic')

    @property
    def total_minutes(self):
        """All session minutes on curricula belonging to this project."""
        result = (
            db.session.query(func.coalesce(func.sum(Session.duration_minutes), 0))
            .join(Curriculum, Session.curriculum_id == Curriculum.id)
            .filter(Curriculum.project_id == self.id)
            .scalar()
        )
        return result or 0

    @property
    def total_hours(self):
        return self.total_minutes / 60.0


class Curriculum(db.Model):
    """The habit itself — e.g. 'Anthropic Interview Prep'. Time is tracked at this level."""
    __tablename__ = 'curriculum'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('app_user.id', ondelete='CASCADE'), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    mastery_hours = db.Column(db.Float, nullable=False, default=1000.0)
    color = db.Column(db.String(7), default='#6366f1')
    status = db.Column(db.String(20), nullable=False, default='active')
    start_date = db.Column(db.Date, nullable=True)
    target_completion_date = db.Column(db.Date, nullable=True)
    archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship(
        'CurriculumItem', backref='curriculum', lazy='dynamic',
        cascade='all, delete-orphan', order_by='CurriculumItem.sort_order, CurriculumItem.id'
    )
    sessions = db.relationship(
        'Session', backref='curriculum', lazy='dynamic',
        cascade='all, delete-orphan'
    )

    @property
    def active_items(self):
        return self.items.filter_by(deleted=False).order_by('sort_order', 'id').all()

    @property
    def total_minutes(self):
        q = (
            db.session.query(func.coalesce(func.sum(Session.duration_minutes), 0))
            .filter(Session.curriculum_id == self.id)
        )
        if curriculum_scopes_mastery_to_time_items(self.id):
            q = q.outerjoin(CurriculumItem, Session.item_id == CurriculumItem.id).filter(
                or_(
                    Session.item_id.is_(None),
                    and_(
                        CurriculumItem.deleted.is_(False),
                        CurriculumItem.item_kind == CurriculumItem.KIND_DAILY,
                        CurriculumItem.completion_style == CurriculumItem.STYLE_TIME_THRESHOLD,
                    ),
                )
            )
        result = q.scalar()
        return result or 0

    @property
    def total_hours(self):
        return self.total_minutes / 60.0

    @property
    def progress_pct(self):
        if not self.mastery_hours:
            return 0.0
        return min((self.total_hours / self.mastery_hours) * 100, 100.0)

    @property
    def completed_items_count(self):
        today = local_today_for_user(self.user)
        items = self.items.filter_by(deleted=False).all()
        return sum(1 for i in items if i.is_complete_for_stats(today))

    @property
    def total_items_count(self):
        return self.items.filter_by(deleted=False).count()


class CurriculumItem(db.Model):
    """Roadmap row: sessions log time. Daily items are either presence (manual check) or time_threshold (auto when today’s minutes ≥ target)."""

    __tablename__ = 'curriculum_item'
    KIND_ONE_SHOT = 'one_shot'
    KIND_DAILY = 'daily'
    STYLE_PRESENCE = 'presence'
    STYLE_TIME_THRESHOLD = 'time_threshold'

    id = db.Column(db.Integer, primary_key=True)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curriculum.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    hours_target = db.Column(db.Float, nullable=True)  # legacy / optional; not used for completion
    item_kind = db.Column(db.String(20), nullable=False, default=KIND_ONE_SHOT)
    completion_style = db.Column(db.String(20), nullable=False, default=STYLE_PRESENCE)
    daily_target_minutes = db.Column(db.Integer, nullable=True)  # daily + time_threshold: bar for “done today”
    completed = db.Column(db.Boolean, default=False)  # one_shot: manual done
    completed_at = db.Column(db.DateTime, nullable=True)
    daily_completed_on = db.Column(db.Date, nullable=True)  # daily + presence: manual check for today
    sort_order = db.Column(db.Integer, default=0)
    deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    activity_days = db.relationship(
        'ItemActivityDay', back_populates='item', cascade='all, delete-orphan', lazy='dynamic'
    )

    @property
    def hours_logged(self):
        result = (
            db.session.query(func.coalesce(func.sum(Session.duration_minutes), 0))
            .filter(Session.item_id == self.id)
            .scalar()
        )
        return (result or 0) / 60.0

    def minutes_logged_on(self, d):
        result = (
            db.session.query(func.coalesce(func.sum(Session.duration_minutes), 0))
            .filter(Session.item_id == self.id, Session.logged_at == d)
            .scalar()
        )
        return int(result or 0)

    @property
    def hours_logged_today(self):
        return self.minutes_logged_on(local_today_for_user(self.curriculum.user)) / 60.0

    def is_time_threshold_daily(self):
        return (
            self.item_kind == self.KIND_DAILY
            and self.completion_style == self.STYLE_TIME_THRESHOLD
        )

    def is_complete_for_stats(self, today=None):
        """Whether this item counts toward curriculum roadmap “done” count for ``today``."""
        today = today or local_today_for_user(self.curriculum.user)
        if self.item_kind == self.KIND_DAILY:
            if self.completion_style == self.STYLE_TIME_THRESHOLD:
                tgt = self.daily_target_minutes
                if tgt is None or tgt < 1:
                    return False
                return self.minutes_logged_on(today) >= tgt
            return self.daily_completed_on == today
        return bool(self.completed)

    @property
    def is_one_shot_done(self):
        if self.item_kind != self.KIND_ONE_SHOT:
            return False
        return bool(self.completed)

    @property
    def is_daily_done_today(self):
        if self.item_kind != self.KIND_DAILY:
            return False
        today = local_today_for_user(self.curriculum.user)
        if self.completion_style == self.STYLE_TIME_THRESHOLD:
            tgt = self.daily_target_minutes
            if tgt is None or tgt < 1:
                return False
            return self.minutes_logged_on(today) >= tgt
        return self.daily_completed_on == today

    @property
    def is_pending_in_roadmap(self):
        if self.deleted:
            return False
        return not self.is_complete_for_stats()

    @property
    def deadline_status(self):
        """Returns 'overdue', 'soon', 'upcoming', 'done', or None."""
        today = local_today_for_user(self.curriculum.user)
        if self.item_kind == self.KIND_DAILY:
            if self.is_daily_done_today:
                return 'done'
        elif self.is_one_shot_done:
            return 'done'
        if not self.deadline:
            return None
        delta = (self.deadline - today).days
        if delta < 0:
            return 'overdue'
        if delta <= 3:
            return 'soon'
        if delta <= 7:
            return 'upcoming'
        return None

    def accepts_time_logging(self):
        """Only recurring time-target dailies use the session ledger for this item."""
        return self.is_time_threshold_daily()


def curriculum_scopes_mastery_to_time_items(curriculum_id):
    """When True, mastery / progress counts only time-target daily sessions (and untagged sessions)."""
    return (
        db.session.query(CurriculumItem.id)
        .filter(
            CurriculumItem.curriculum_id == curriculum_id,
            CurriculumItem.deleted.is_(False),
            CurriculumItem.item_kind == CurriculumItem.KIND_DAILY,
            CurriculumItem.completion_style == CurriculumItem.STYLE_TIME_THRESHOLD,
        )
        .first()
        is not None
    )


class ItemActivityDay(db.Model):
    """Historical calendar day when a daily presence item was marked done (heatmap / streak)."""

    __tablename__ = 'item_activity_day'
    __table_args__ = (db.UniqueConstraint('item_id', 'activity_date', name='uq_item_activity_day'),)

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('curriculum_item.id', ondelete='CASCADE'), nullable=False)
    activity_date = db.Column(db.Date, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    item = db.relationship('CurriculumItem', back_populates='activity_days')


class Session(db.Model):
    """Time logged against a curriculum; tagged to a roadmap item when the curriculum has items."""
    __tablename__ = 'session'
    id = db.Column(db.Integer, primary_key=True)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curriculum.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('curriculum_item.id'), nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=False)
    logged_at = db.Column(db.Date, nullable=False, default=date.today)
    note = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(20), default='manual')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    item = db.relationship('CurriculumItem', backref='sessions', foreign_keys=[item_id])

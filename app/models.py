from datetime import datetime, date
from sqlalchemy import func
from app import db


class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=True)
    reminder_time = db.Column(db.Time, nullable=True)
    reminder_active = db.Column(db.Boolean, default=True)
    timezone = db.Column(db.String(50), default='UTC')


class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
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
        result = (
            db.session.query(func.coalesce(func.sum(Session.duration_minutes), 0))
            .filter(Session.curriculum_id == self.id)
            .scalar()
        )
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
        today = date.today()
        items = self.items.filter_by(deleted=False).all()
        return sum(1 for i in items if i.is_complete_for_stats(today))

    @property
    def total_items_count(self):
        return self.items.filter_by(deleted=False).count()


class CurriculumItem(db.Model):
    """Roadmap row: time is logged via sessions; done state is manual (check). Daily resets each calendar day."""

    __tablename__ = 'curriculum_item'
    KIND_ONE_SHOT = 'one_shot'
    KIND_DAILY = 'daily'

    id = db.Column(db.Integer, primary_key=True)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curriculum.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    hours_target = db.Column(db.Float, nullable=True)  # legacy / optional; not used for completion
    item_kind = db.Column(db.String(20), nullable=False, default=KIND_ONE_SHOT)
    completed = db.Column(db.Boolean, default=False)  # one_shot: manual done
    completed_at = db.Column(db.DateTime, nullable=True)
    daily_completed_on = db.Column(db.Date, nullable=True)  # daily: checked iff == today
    sort_order = db.Column(db.Integer, default=0)
    deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
        return self.minutes_logged_on(date.today()) / 60.0

    def is_complete_for_stats(self, today=None):
        """Whether this item counts toward curriculum roadmap “done” count for ``today``."""
        today = today or date.today()
        if self.item_kind == self.KIND_DAILY:
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
        return self.daily_completed_on == date.today()

    @property
    def is_pending_in_roadmap(self):
        if self.deleted:
            return False
        return not self.is_complete_for_stats()

    @property
    def deadline_status(self):
        """Returns 'overdue', 'soon', 'upcoming', 'done', or None."""
        if self.item_kind == self.KIND_DAILY:
            if self.is_daily_done_today:
                return 'done'
        elif self.is_one_shot_done:
            return 'done'
        if not self.deadline:
            return None
        delta = (self.deadline - date.today()).days
        if delta < 0:
            return 'overdue'
        if delta <= 3:
            return 'soon'
        if delta <= 7:
            return 'upcoming'
        return None


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

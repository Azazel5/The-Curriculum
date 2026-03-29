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


class Curriculum(db.Model):
    """The habit itself — e.g. 'Anthropic Interview Prep'. Time is tracked at this level."""
    __tablename__ = 'curriculum'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    mastery_hours = db.Column(db.Float, nullable=False, default=1000.0)
    color = db.Column(db.String(7), default='#6366f1')
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
        return self.items.filter_by(completed=True, deleted=False).count()

    @property
    def total_items_count(self):
        return self.items.filter_by(deleted=False).count()


class CurriculumItem(db.Model):
    """
    A sub-task / milestone inside a curriculum.
    Think: 'Read Attention paper', 'Do 10 mock interviews', 'Build toy transformer'.
    Items are a roadmap — they can be checked off. Time is NOT tracked per item by default,
    but sessions can optionally be tagged to an item.
    """
    __tablename__ = 'curriculum_item'
    id = db.Column(db.Integer, primary_key=True)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curriculum.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    hours_target = db.Column(db.Float, nullable=True)  # optional per-item goal
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def hours_logged(self):
        """Minutes logged in sessions tagged to this item."""
        result = (
            db.session.query(func.coalesce(func.sum(Session.duration_minutes), 0))
            .filter(Session.item_id == self.id)
            .scalar()
        )
        return (result or 0) / 60.0

    @property
    def deadline_status(self):
        """Returns 'overdue', 'soon', 'upcoming', 'done', or None."""
        if self.completed:
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
    """Time logged against a curriculum (the habit). Optionally tagged to an item."""
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

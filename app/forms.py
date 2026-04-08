from datetime import date
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, FloatField, IntegerField,
    SelectField, DateField, HiddenField
)
from wtforms.validators import DataRequired, Optional, NumberRange


class CurriculumForm(FlaskForm):
    project_id = SelectField('Project', coerce=int, validators=[Optional()])
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    mastery_hours = FloatField(
        'Mastery Target (hours)',
        validators=[DataRequired(), NumberRange(min=1)],
        default=1000.0
    )
    status = SelectField(
        'Status',
        choices=[('active', 'Active'), ('paused', 'Paused'), ('completed', 'Completed'), ('archived', 'Archived')],
        default='active',
        validators=[DataRequired()]
    )
    start_date = DateField('Start date', validators=[Optional()])
    target_completion_date = DateField('Target completion', validators=[Optional()])
    color = StringField('Color', default='#6366f1')


class ProjectForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    color = StringField('Color', default='#6366f1')


class CurriculumItemForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    deadline = DateField('Deadline', validators=[Optional()])
    item_kind = SelectField(
        'Item type',
        choices=[
            ('one_shot', 'One-time'),
            ('daily', 'Daily (check resets each day)'),
        ],
        default='one_shot',
        validators=[DataRequired()],
    )


class SessionForm(FlaskForm):
    curriculum_id = SelectField('Curriculum', coerce=int, validators=[DataRequired()])
    item_id = SelectField('Item', coerce=int, validators=[Optional()])
    hours = IntegerField('Hours', validators=[Optional(), NumberRange(min=0)], default=0)
    minutes = IntegerField('Minutes', validators=[Optional(), NumberRange(min=0, max=59)], default=0)
    logged_at = DateField('Date', validators=[Optional()], default=date.today)
    note = StringField('Note (optional)', validators=[Optional()])


class SettingsForm(FlaskForm):
    email = StringField('Email for reminders', validators=[Optional()])
    reminder_time = StringField('Remind me at (HH:MM, 24h)', validators=[Optional()])
    reminder_active = SelectField('Reminders', choices=[('1', 'Enabled'), ('0', 'Disabled')], default='1')
    timezone = StringField('Timezone', default='UTC', validators=[Optional()])

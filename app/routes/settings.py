from datetime import time as time_type
from flask import Blueprint, render_template, redirect, url_for, flash
from app import db
from app.models import Settings
from app.forms import SettingsForm

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    s = Settings.query.first()
    if not s:
        s = Settings()
        db.session.add(s)
        db.session.commit()

    form = SettingsForm()

    if form.validate_on_submit():
        s.email = form.email.data or None
        s.reminder_active = form.reminder_active.data == '1'
        s.timezone = form.timezone.data or 'UTC'

        time_str = (form.reminder_time.data or '').strip()
        if time_str:
            try:
                parts = time_str.split(':')
                s.reminder_time = time_type(int(parts[0]), int(parts[1]))
            except (ValueError, IndexError):
                flash('Invalid time format — use HH:MM (e.g. 20:00)', 'error')
                return render_template('settings.html', form=form, settings=s)
        else:
            s.reminder_time = None

        db.session.commit()
        flash('Settings saved', 'success')
        return redirect(url_for('settings.settings'))

    # Pre-populate
    form.email.data = s.email or ''
    form.reminder_time.data = s.reminder_time.strftime('%H:%M') if s.reminder_time else ''
    form.reminder_active.data = '1' if s.reminder_active else '0'
    form.timezone.data = s.timezone or 'UTC'

    return render_template('settings.html', form=form, settings=s)

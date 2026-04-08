from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from app import db
from app.models import User, Settings
from app.forms import LoginForm, RegisterForm, SetupForm


auth_bp = Blueprint('auth', __name__)


def _ensure_settings_for_user(user_id):
    if not Settings.query.filter_by(user_id=user_id).first():
        db.session.add(Settings(user_id=user_id))
        db.session.commit()


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip(), is_guest=False).first()
        if not user or not user.password_hash:
            flash('Invalid email or password', 'error')
        elif not check_password_hash(user.password_hash, form.password.data):
            flash('Invalid email or password', 'error')
        else:
            login_user(user)
            _ensure_settings_for_user(user.id)
            nxt = request.args.get('next') or url_for('dashboard.index')
            return redirect(nxt)
    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        if User.query.filter_by(email=email).first():
            flash('That email is already registered', 'error')
            return render_template('auth/register.html', form=form)

        user = User(
            email=email,
            password_hash=generate_password_hash(form.password.data),
            is_guest=False,
        )
        db.session.add(user)
        db.session.commit()
        _ensure_settings_for_user(user.id)
        login_user(user)
        return redirect(url_for('dashboard.index'))
    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout', methods=['POST'])
def logout():
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/guest', methods=['POST'])
def guest():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    user = User(is_guest=True, email=None, password_hash=None)
    db.session.add(user)
    db.session.commit()
    _ensure_settings_for_user(user.id)
    login_user(user)
    return redirect(url_for('dashboard.index'))


@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """
    Claim the legacy user created in migration (id=1).
    This route is only usable while the legacy user has no email/password.
    """
    legacy = User.query.get(1)
    if not legacy or legacy.is_guest or legacy.email or legacy.password_hash:
        return redirect(url_for('auth.login'))

    form = SetupForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        if User.query.filter(User.email == email, User.id != legacy.id).first():
            flash('That email is already registered', 'error')
            return render_template('auth/setup.html', form=form)
        legacy.email = email
        legacy.password_hash = generate_password_hash(form.password.data)
        legacy.is_guest = False
        db.session.commit()
        _ensure_settings_for_user(legacy.id)
        login_user(legacy)
        flash('Account set up. Your existing data is now protected.', 'success')
        return redirect(url_for('dashboard.index'))
    return render_template('auth/setup.html', form=form)


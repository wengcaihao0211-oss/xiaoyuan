from flask import flash, redirect, render_template, request, session, url_for
from flask_login import login_user, logout_user, login_required, current_user
from app.blueprints.auth import auth_bp
from app.blueprints.auth.forms import (
    LoginForm, RegisterForm, ForgotPasswordForm,
    ResetPasswordForm, ChangePasswordForm
)
from app.services import auth_service


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('browse.home'))
    form = LoginForm()
    if form.validate_on_submit():
        success, message, user = auth_service.authenticate_user(
            form.username.data,
            form.password.data,
            login_ip=request.headers.get('X-Forwarded-For', request.remote_addr)
        )
        if success:
            session.permanent = True
            login_user(user, remember=False)
            session['session_version'] = user.session_version
            flash(message, 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            if user.is_admin():
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('browse.home'))
        flash(message, 'danger')
    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('browse.home'))
    form = RegisterForm()
    action = request.form.get('action')
    if request.method == 'POST' and action == 'send_otp':
        success, message = auth_service.send_register_otp(
            phone=form.phone.data,
            email=form.email.data
        )
        flash(message, 'success' if success else 'danger')
    elif form.validate_on_submit():
        success, message, user = auth_service.register_user(
            username=form.username.data,
            password=form.password.data,
            phone=form.phone.data,
            email=form.email.data,
            nickname=form.nickname.data,
            otp=form.otp.data
        )
        if success:
            flash(message, 'success')
            return redirect(url_for('auth.login'))
        flash(message, 'danger')
    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('reset_username', None)
    session.pop('reset_identifier', None)
    session.pop('session_version', None)
    logout_user()
    flash('您已退出登录。', 'info')
    return redirect(url_for('browse.home'), code=303)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('browse.home'))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        success, message = auth_service.send_password_reset_otp(form.username.data)
        flash(message, 'success' if success else 'warning')
        session['reset_identifier'] = form.username.data
        return redirect(url_for('auth.reset_password'))
    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('browse.home'))
    identifier = session.get('reset_identifier') or session.get('reset_username', '')
    if not identifier:
        flash('请先输入账号获取验证码。', 'warning')
        return redirect(url_for('auth.forgot_password'))
    form = ResetPasswordForm(username=identifier)
    if form.validate_on_submit():
        success, message = auth_service.reset_password(
            identifier,
            form.otp.data,
            form.new_password.data
        )
        if success:
            session.pop('reset_username', None)
            session.pop('reset_identifier', None)
            flash(message, 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'danger')
    return render_template('auth/reset_password.html', form=form)


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        success, message = auth_service.change_password(
            current_user, form.old_password.data, form.new_password.data
        )
        flash(message, 'success' if success else 'danger')
        if success:
            session['session_version'] = current_user.session_version
            return redirect(url_for('user.profile'))
    return render_template('auth/change_password.html', form=form)

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.blueprints.user import user_bp
from app.services import user_service


@user_bp.route('/profile')
@login_required
def profile():
    stats = user_service.get_user_stats(current_user)
    return render_template('user/profile.html', user=current_user, stats=stats)


@user_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form_data = {
        'nickname': current_user.nickname or '',
        'phone': current_user.phone or '',
        'email': current_user.email or '',
        'introduction': current_user.introduction or '',
        'contact_otp': '',
    }
    if request.method == 'POST':
        action = request.form.get('action', 'save')
        avatar = request.files.get('avatar')
        nickname = request.form.get('nickname', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        introduction = request.form.get('introduction', '')
        contact_otp = request.form.get('contact_otp', '')
        form_data = {
            'nickname': nickname,
            'phone': phone,
            'email': email,
            'introduction': introduction,
            'contact_otp': contact_otp,
        }
        if action == 'send_contact_otp':
            success, message = user_service.send_profile_contact_otp(
                current_user,
                phone=phone,
                email=email
            )
        else:
            success, message = user_service.update_profile(
                current_user,
                nickname=nickname,
                phone=phone,
                email=email,
                introduction=introduction,
                avatar_file=avatar if avatar and avatar.filename else None,
                contact_otp=contact_otp
            )
        flash(message, 'success' if success else 'danger')
        if success and action != 'send_contact_otp':
            return redirect(url_for('user.profile'))
    return render_template('user/edit_profile.html', user=current_user, form_data=form_data)

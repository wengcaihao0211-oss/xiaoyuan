from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.blueprints.user import user_bp
from app.services import user_service
from app.extensions import db
from app.models.user import User
from app.models.product import Product
from app.utils.pagination import paginate


@user_bp.route('/profile')
@login_required
def profile():
    stats = user_service.get_user_stats(current_user)
    return render_template('user/profile.html', user=current_user, stats=stats)


@user_bp.route('/view/<int:user_id>')
def view_profile(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('用户不存在', 'danger')
        return redirect(url_for('browse.home'))
    
    products = Product.on_sale().filter_by(seller_id=user_id).order_by(Product.created_at.desc())
    pagination = paginate(products)
    
    # 获取用户统计数据
    stats = user_service.get_user_stats(user)
    
    return render_template('user/view_profile.html', user=user, products=pagination.items, pagination=pagination, stats=stats)


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


@user_bp.route('/report/<int:report_id>')
@login_required
def report_result(report_id):
    from app.models.report import Report
    report = Report.query.get_or_404(report_id)
    if report.reporter_id != current_user.user_id:
        abort(403)
    return render_template('user/report_detail.html', report=report)

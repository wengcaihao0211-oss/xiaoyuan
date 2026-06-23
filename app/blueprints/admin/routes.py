from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.blueprints.admin import admin_bp
from app.blueprints.admin.forms import (
    AdminLoginForm, RejectProductForm, CategoryForm, HandleReportForm
)
from app.models.user import User
from app.models.product import Product
from app.models.category import Category
from app.models.orders import Order
from app.models.report import Report
from app.models.notification import Notification
from app.services import auth_service, admin_service, report_service
from app.utils.decorators import admin_required
from app.utils.helpers import mask_phone
from app.utils.pagination import paginate


# ---- Admin Login (F43) ----
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and current_user.is_admin():
        return redirect(url_for('admin.dashboard'))
    form = AdminLoginForm()
    if form.validate_on_submit():
        success, message, user = auth_service.authenticate_user(
            form.username.data,
            form.password.data,
            login_ip=request.headers.get('X-Forwarded-For', request.remote_addr)
        )
        if success and user.is_admin():
            session.permanent = True
            login_user(user, remember=False)
            session['session_version'] = user.session_version
            flash('管理员登录成功。', 'success')
            return redirect(url_for('admin.dashboard'))
        if success and not user.is_admin():
            flash('该账号不是管理员。', 'danger')
        else:
            flash(message, 'danger')
    return render_template('admin/login.html', form=form)


@admin_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('reset_username', None)
    session.pop('reset_identifier', None)
    session.pop('session_version', None)
    logout_user()
    return redirect(url_for('admin.login'), code=303)


# ---- Dashboard (F50 partial) ----
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    stats = admin_service.get_dashboard_stats()
    return render_template('admin/dashboard.html', stats=stats)


# ---- User Management (F44-F45) ----
@admin_bp.route('/users')
@admin_required
def user_list():
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '')
    query = User.active()
    if q:
        query = query.filter(User.username.contains(q))
    if status:
        query = query.filter_by(status=status)
    query = query.order_by(User.created_at.desc())
    pagination = paginate(query, per_page=20)
    return render_template('admin/user_list.html',
                         users=pagination.items, pagination=pagination,
                         query=q, status=status, mask_phone=mask_phone)


@admin_bp.route('/users/<int:id>')
@admin_required
def user_detail(id):
    user = db.session.get(User, id)
    if not user:
        flash('用户不存在。', 'danger')
        return redirect(url_for('admin.user_list'))
    from app.services.user_service import get_user_stats
    stats = get_user_stats(user)
    return render_template('admin/user_detail.html', user=user, stats=stats,
                         mask_phone=mask_phone)


@admin_bp.route('/users/<int:id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user(id):
    success, message = admin_service.toggle_user_status(id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin.user_list'))


# ---- Product Review (F46-F47) ----
@admin_bp.route('/products/review')
@admin_required
def product_review():
    products = Product.active().filter_by(product_status='PENDING_REVIEW').order_by(
        Product.created_at.desc()).all()
    return render_template('admin/product_review.html', products=products)


@admin_bp.route('/products/<int:id>/approve', methods=['POST'])
@admin_required
def approve_product(id):
    success, message = admin_service.review_product(id, 'approve')
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin.product_review'))


@admin_bp.route('/products/<int:id>/reject', methods=['POST'])
@admin_required
def reject_product(id):
    reason = request.form.get('reason', '').strip()
    success, message = admin_service.review_product(id, 'reject', reason)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin.product_review'))


@admin_bp.route('/products/list')
@admin_required
def product_list():
    status = request.args.get('status', '')
    query = Product.active()
    if status:
        query = query.filter_by(product_status=status)
    query = query.order_by(Product.created_at.desc())
    pagination = paginate(query, per_page=20)
    return render_template('admin/product_list.html',
                         products=pagination.items, pagination=pagination,
                         current_filter=status)


@admin_bp.route('/products/<int:id>/takedown', methods=['POST'])
@admin_required
def takedown_product(id):
    permanent = request.form.get('permanent') == '1'
    success, message = admin_service.admin_takedown_product(id, permanent)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin.product_list'))


# ---- Category Management (F48) ----
@admin_bp.route('/categories', methods=['GET', 'POST'])
@admin_required
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        success, message = admin_service.manage_category(
            'create', name=form.category_name.data,
            description=form.description.data
        )
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('admin.categories'))

    categories = Category.query.order_by(Category.created_at.desc()).all()
    return render_template('admin/category_manage.html',
                         categories=categories, form=form)


@admin_bp.route('/categories/<int:id>/update', methods=['POST'])
@admin_required
def update_category(id):
    name = request.form.get('category_name', '').strip()
    description = request.form.get('description', '').strip()
    success, message = admin_service.manage_category(
        'update', category_id=id, name=name, description=description
    )
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/categories/<int:id>/toggle', methods=['POST'])
@admin_required
def toggle_category(id):
    success, message = admin_service.manage_category('toggle', category_id=id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/categories/<int:id>/delete', methods=['POST'])
@admin_required
def delete_category(id):
    success, message = admin_service.manage_category('delete', category_id=id)
    flash(message, 'warning' if not success else 'success')
    return redirect(url_for('admin.categories'))


# ---- Report Handling (F49) ----
@admin_bp.route('/reports')
@admin_required
def report_list():
    status = request.args.get('status', '')
    query = Report.query
    if status:
        query = query.filter_by(report_status=status)
    query = query.order_by(
        db.case((Report.report_status == 'PENDING', 0), else_=1),
        Report.created_at.desc()
    )
    pagination = paginate(query, per_page=20)
    return render_template('admin/report_list.html',
                         reports=pagination.items, pagination=pagination,
                         current_filter=status)


@admin_bp.route('/reports/<int:id>')
@admin_required
def report_detail(id):
    report = db.session.get(Report, id)
    if not report:
        flash('举报不存在。', 'danger')
        return redirect(url_for('admin.report_list'))
    target = None
    if report.target_type == 'PRODUCT':
        target = db.session.get(Product, report.target_id)
    elif report.target_type == 'USER':
        target = db.session.get(User, report.target_id)
    form = HandleReportForm()
    return render_template('admin/report_detail.html',
                         report=report, target=target, form=form)


@admin_bp.route('/reports/<int:id>/handle', methods=['POST'])
@admin_required
def handle_report(id):
    action = request.form.get('action', 'DISMISSED')
    handle_result = request.form.get('handle_result', '').strip()
    success, message = report_service.handle_report(
        report_id=id, handler_id=current_user.user_id,
        action=action, handle_result=handle_result or None
    )

    # Create notification for reporter
    report = db.session.get(Report, id)
    if report:
        notif = Notification(
            receiver_id=report.reporter_id,
            notification_type='REPORT',
            title='举报处理结果',
            content=f'您的举报已被处理。结果：{report.status_display}',
            related_id=report.report_id
        )
        db.session.add(notif)
        db.session.commit()

    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin.report_list'))


# ---- Statistics (F50) ----
@admin_bp.route('/statistics')
@admin_required
def statistics():
    try:
        end_str = request.args.get('end', '')
        start_str = request.args.get('start', '')
        end_date = datetime.strptime(end_str, '%Y-%m-%d') if end_str else datetime.utcnow()
        start_date = datetime.strptime(start_str, '%Y-%m-%d') if start_str else end_date - timedelta(days=30)
    except ValueError:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

    stats = admin_service.get_dashboard_stats(start_date, end_date)
    cat_dist = admin_service.get_category_distribution()
    return render_template('admin/statistics.html', stats=stats,
                         cat_dist=cat_dist,
                         start_date=start_date.strftime('%Y-%m-%d'),
                         end_date=end_date.strftime('%Y-%m-%d'))

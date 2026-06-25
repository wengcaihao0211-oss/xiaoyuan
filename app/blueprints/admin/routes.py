from datetime import datetime, timedelta
import json
import uuid
import urllib.request
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
from app.services import auth_service, admin_service, report_service, message_service
from app.services.notification_service import create_notification
from app.utils.decorators import admin_required
from app.utils.helpers import mask_phone
from app.utils.pagination import paginate


# #region debug-point A:admin-review-route
def _report_admin_review_route(hypothesis_id, location, message, data=None, trace_id=None):
    _u = 'http://127.0.0.1:7777/event'
    _s = 'admin-review-500'
    try:
        with open('.dbg/admin-review-500.env', encoding='utf-8') as _f:
            for _line in _f:
                if _line.startswith('DEBUG_SERVER_URL='):
                    _u = _line.split('=', 1)[1].strip() or _u
                elif _line.startswith('DEBUG_SESSION_ID='):
                    _s = _line.split('=', 1)[1].strip() or _s
        _payload = {
            'sessionId': _s,
            'runId': 'pre-fix',
            'hypothesisId': hypothesis_id,
            'location': location,
            'msg': f'[DEBUG] {message}',
            'data': data or {},
        }
        if trace_id:
            _payload['traceId'] = trace_id
        urllib.request.urlopen(urllib.request.Request(
            _u,
            data=json.dumps(_payload).encode(),
            headers={'Content-Type': 'application/json'}
        ), timeout=1).read()
    except Exception:
        pass
# #endregion


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
    phone = request.args.get('phone', '').strip()
    status = request.args.get('status', '')
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    query = User.active()
    if q:
        query = query.filter(User.username.contains(q))
    if phone:
        query = query.filter(User.phone.contains(phone))
    if status:
        query = query.filter_by(status=status)
    if date_from:
        try:
            dt_from = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(User.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(User.created_at < dt_to)
        except ValueError:
            pass
    query = query.order_by(User.created_at.desc())
    pagination = paginate(query, per_page=20)
    return render_template('admin/user_list.html',
                         users=pagination.items, pagination=pagination,
                         query=q, phone=phone, status=status,
                         date_from=date_from, date_to=date_to,
                         mask_phone=mask_phone)


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
    trace_id = uuid.uuid4().hex
    _report_admin_review_route(
        'A',
        'app/blueprints/admin/routes.py:approve_product',
        'approve request received',
        {'product_id': id, 'method': request.method, 'user_id': getattr(current_user, 'user_id', None)},
        trace_id
    )
    try:
        success, message = admin_service.review_product(id, 'approve', trace_id=trace_id)
        _report_admin_review_route(
            'A',
            'app/blueprints/admin/routes.py:approve_product',
            'approve request completed',
            {'product_id': id, 'success': success, 'message': message},
            trace_id
        )
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('admin.product_review'))
    except Exception as error:
        _report_admin_review_route(
            'B',
            'app/blueprints/admin/routes.py:approve_product',
            'approve request raised exception',
            {'product_id': id, 'error_type': type(error).__name__, 'error': str(error)},
            trace_id
        )
        raise


@admin_bp.route('/products/<int:id>/reject', methods=['POST'])
@admin_required
def reject_product(id):
    reason = request.form.get('reason', '').strip()
    trace_id = uuid.uuid4().hex
    _report_admin_review_route(
        'A',
        'app/blueprints/admin/routes.py:reject_product',
        'reject request received',
        {'product_id': id, 'method': request.method, 'user_id': getattr(current_user, 'user_id', None), 'reason_len': len(reason)},
        trace_id
    )
    try:
        success, message = admin_service.review_product(id, 'reject', reason, trace_id=trace_id)
        _report_admin_review_route(
            'A',
            'app/blueprints/admin/routes.py:reject_product',
            'reject request completed',
            {'product_id': id, 'success': success, 'message': message},
            trace_id
        )
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('admin.product_review'))
    except Exception as error:
        _report_admin_review_route(
            'B',
            'app/blueprints/admin/routes.py:reject_product',
            'reject request raised exception',
            {'product_id': id, 'error_type': type(error).__name__, 'error': str(error)},
            trace_id
        )
        raise


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
        create_notification(
            receiver_id=report.reporter_id, ntype='REPORT',
            title='举报处理结果',
            content=f'您的举报已被处理。结果：{report.status_display}',
            related_id=report.report_id
        )
        db.session.commit()

    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin.report_list'))


# ---- AI Review (F51) ----
@admin_bp.route('/ai-review/dashboard')
@admin_required
def ai_review_dashboard():
    """AI审核仪表板"""
    stats = admin_service.get_ai_review_stats()
    return render_template('admin/ai_review_dashboard.html', stats=stats)


@admin_bp.route('/ai-review/pending-human')
@admin_required
def pending_human_review():
    """需要人工审核的举报列表"""
    page = request.args.get('page', 1, type=int)
    reports, total, total_pages = admin_service.get_pending_human_review_reports(page, per_page=20)
    return render_template('admin/pending_human_review.html',
                         reports=reports, total=total, total_pages=total_pages,
                         current_page=page)


@admin_bp.route('/ai-review/reviewed')
@admin_required
def ai_reviewed_reports():
    """AI已审核的举报列表"""
    page = request.args.get('page', 1, type=int)
    reports, total, total_pages = admin_service.get_ai_reviewed_reports(page, per_page=20)
    return render_template('admin/ai_reviewed_reports.html',
                         reports=reports, total=total, total_pages=total_pages,
                         current_page=page)


# ---- Appeal Handling ----
@admin_bp.route('/appeals')
@admin_required
def appeal_list():
    """申诉列表"""
    reports = report_service.get_appealed_reports()
    return render_template('admin/appeal_list.html', reports=reports)


@admin_bp.route('/appeals/<int:id>/handle', methods=['POST'])
@admin_required
def handle_appeal(id):
    """处理申诉"""
    action = request.form.get('action', 'UPHELD')
    handle_result = request.form.get('handle_result', '').strip()
    success, message = report_service.handle_appeal(
        report_id=id, handler_id=current_user.user_id,
        action=action, handle_result=handle_result or None
    )
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin.appeal_list'))


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


# ---- Admin Context Processor ----
@admin_bp.context_processor
def admin_context():
    pending_count = Product.active().filter_by(product_status='PENDING_REVIEW').count()
    pending_reports_count = Report.query.filter_by(report_status='PENDING').count()
    unread_message_count = message_service.get_unread_count(current_user.user_id) if current_user.is_authenticated and current_user.is_admin() else 0
    return dict(
        pending_count=pending_count,
        pending_reports_count=pending_reports_count,
        unread_message_count=unread_message_count
    )

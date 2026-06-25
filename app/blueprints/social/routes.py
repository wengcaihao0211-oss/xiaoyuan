from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.social import social_bp
from app.blueprints.social.forms import MessageForm, ReviewForm, ReportForm, AppealForm
from app.models.product import Product
from app.models.orders import Order
from app.models.user import User
from app.models.report import Report
from app.services import message_service
from app.services import review_service
from app.services import report_service
from app.utils.pagination import paginate

# ---- Messages ----

@social_bp.route('/messages')
@login_required
def chat_list():
    # Get request parameters
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword', '')
    # 注意：如果 'unread' 参数不存在，默认为 false
    # 如果 'unread' 参数存在，无论值是什么，只要不是 'false' 或 '' 就视为 true
    unread_param = request.args.get('unread', None)
    unread_only = False
    if unread_param is not None:
        unread_only = unread_param.lower() not in ['false', '0', '']
    
    # Get conversations with pagination, search and filter
    conversations, total_unread, total_pages = message_service.get_conversations(
        user_id=current_user.user_id,
        page=page,
        per_page=20,
        keyword=keyword if keyword else None,
        unread_only=unread_only
    )
    
    # 根据用户角色选择使用哪个模板
    if current_user.is_admin():
        template_name = 'admin/chat_list.html'
    else:
        template_name = 'social/chat_list.html'
    
    return render_template(
        template_name,
        conversations=conversations,
        total_unread=total_unread,
        total_pages=total_pages,
        current_page=page,
        keyword=keyword,
        unread_only=unread_only
    )


@social_bp.route('/messages/contact-admin')
@login_required
def contact_admin():
    admin_user = User.active().filter(
        User.role == 'ADMIN',
        User.status == 'ACTIVE',
        User.user_id != current_user.user_id
    ).order_by(User.user_id.asc()).first()

    if not admin_user:
        flash('暂无可联系的管理员。', 'warning')
        return redirect(request.referrer or url_for('notification.list'))

    return redirect(url_for('social.chat_detail', user_id=admin_user.user_id))


@social_bp.route('/messages/<int:user_id>', defaults={'product_id': None}, methods=['GET', 'POST'])
@social_bp.route('/messages/<int:user_id>/<int:product_id>', methods=['GET', 'POST'])
@login_required
def chat_detail(user_id, product_id):
    other_user = db.session.get(User, user_id)
    product = db.session.get(Product, product_id) if product_id is not None else None
    if not other_user or (product_id is not None and not product):
        flash('用户或商品不存在。', 'danger')
        return redirect(url_for('social.chat_list'))

    existing_messages = message_service.get_chat_messages(current_user.user_id, user_id, product_id)

    if product_id is None and not (other_user.is_admin() or current_user.is_admin() or existing_messages):
        flash('该会话不存在。', 'danger')
        return redirect(url_for('social.chat_list'))

    # Verify current user is a participant (buyer or seller related to this product)
    is_participant = product_id is None or (
        current_user.user_id == product.seller_id or
        Order.active().filter_by(
            product_id=product_id, buyer_id=current_user.user_id
        ).first() is not None or
        existing_messages
    )
    if not is_participant and current_user.user_id != user_id:
        pass  # Allow access if they have messages

    form = MessageForm()
    if form.validate_on_submit():
        success, msg, msg_obj = message_service.send_message(
            sender_id=current_user.user_id,
            receiver_id=user_id,
            product_id=product_id,
            content=form.content.data
        )
        if success:
            return redirect(url_for('social.chat_detail', user_id=user_id, product_id=product_id))
        flash(msg, 'danger')

    # Mark messages as read
    message_service.mark_messages_read(current_user.user_id, user_id, product_id)

    messages = message_service.get_chat_messages(current_user.user_id, user_id, product_id)
    
    # 根据用户角色选择使用哪个模板
    if current_user.is_admin():
        template_name = 'admin/chat_detail.html'
    else:
        template_name = 'social/chat_detail.html'
    
    return render_template(template_name,
                         messages=messages, other_user=other_user,
                         product=product, form=form)


@social_bp.route('/message/send/<int:product_id>')
@login_required
def send_message(product_id):
    """Redirect to chat with the seller of this product."""
    product = db.session.get(Product, product_id)
    if not product or product.deleted:
        flash('商品不存在。', 'danger')
        return redirect(url_for('browse.home'))
    if product.seller_id == current_user.user_id:
        flash('不能给自己发消息。', 'warning')
        return redirect(url_for('browse.detail', id=product_id))
    return redirect(url_for('social.chat_detail',
                          user_id=product.seller_id, product_id=product_id))


# ---- Reviews ----

@social_bp.route('/review/<int:order_id>', methods=['GET', 'POST'])
@login_required
def review(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.deleted:
        flash('订单不存在。', 'danger')
        return redirect(url_for('browse.home'))
    if current_user.user_id not in (order.buyer_id, order.seller_id):
        flash('无权评价此订单。', 'danger')
        return redirect(url_for('browse.home'))

    if review_service.has_reviewed(order_id, current_user.user_id):
        flash('您已经评价过此订单。', 'info')
        return redirect(url_for('order.detail', id=order_id))

    form = ReviewForm()
    if form.validate_on_submit():
        success, message = review_service.submit_review(
            order_id=order_id,
            reviewer_id=current_user.user_id,
            score=form.score.data,
            content=form.review_content.data
        )
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('order.detail', id=order_id))

    product = db.session.get(Product, order.product_id)
    other_user = order.buyer if current_user.user_id == order.seller_id else order.seller_ref
    return render_template('social/review_form.html',
                         order=order, product=product,
                         other_user=other_user, form=form)


# ---- Reports ----

@social_bp.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    form = ReportForm()
    if request.method == 'GET':
        form.target_type.data = request.args.get('type', 'PRODUCT')
        form.target_id.data = request.args.get('id', '')
    if form.validate_on_submit():
        success, message = report_service.submit_report(
            reporter_id=current_user.user_id,
            target_type=form.target_type.data,
            target_id=int(form.target_id.data),
            reason=form.report_reason.data,
            description=form.description.data
        )
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('browse.home'))

    target_type = form.target_type.data or request.args.get('type', 'PRODUCT')
    target_id = int(form.target_id.data or request.args.get('id', 0))
    target = None
    if target_type == 'PRODUCT':
        target = db.session.get(Product, target_id)
    elif target_type == 'USER':
        target = db.session.get(User, target_id)

    return render_template('social/report_form.html',
                         form=form, target_type=target_type, target=target)


@social_bp.route('/my-reports')
@login_required
def my_reports():
    """
    我的举报列表
    """
    reports = report_service.get_user_reports(current_user.user_id)
    return render_template('social/my_reports.html', reports=reports)


@social_bp.route('/reports-against-me')
@login_required
def reports_against_me():
    """
    针对我的举报列表（作为被举报人）
    """
    reports = report_service.get_reports_against_user(current_user.user_id)
    return render_template('social/reports_against_me.html', reports=reports)


@social_bp.route('/report/<int:report_id>/appeal', methods=['GET', 'POST'])
@login_required
def appeal_report(report_id):
    """
    申诉举报
    """
    from app.blueprints.social.forms import AppealForm
    
    report = db.session.get(Report, report_id)
    if not report:
        flash('举报不存在。', 'danger')
        return redirect(url_for('social.reports_against_me'))
    
    # 检查权限
    if not report_service.is_target_owner(current_user.user_id, report):
        flash('您无权对此举报进行申诉。', 'danger')
        return redirect(url_for('social.reports_against_me'))
    
    # 检查是否已申诉
    if report.is_appealed:
        flash('您已对此举报进行过申诉。', 'info')
        return redirect(url_for('social.reports_against_me'))
    
    # 检查是否已处理
    if report.report_status == 'PENDING':
        flash('该举报尚未处理，无需申诉。', 'info')
        return redirect(url_for('social.reports_against_me'))
    
    form = AppealForm()
    if form.validate_on_submit():
        success, message = report_service.submit_appeal(
            report_id=report_id,
            user_id=current_user.user_id,
            appeal_content=form.appeal_content.data
        )
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('social.reports_against_me'))
    
    return render_template('social/appeal_form.html', report=report, form=form)

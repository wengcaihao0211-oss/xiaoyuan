from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.order import order_bp
from app.blueprints.order.forms import OrderForm, RejectForm
from app.models.product import Product
from app.models.orders import Order
from app.services import order_service
from app.utils.pagination import paginate


@order_bp.route('/submit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def submit(product_id):
    product = db.session.get(Product, product_id)
    if not product or product.deleted:
        flash('商品不存在或已下架。', 'danger')
        return redirect(url_for('browse.home'))
    if product.seller_id == current_user.user_id:
        flash('不能购买自己的商品。', 'warning')
        return redirect(url_for('browse.detail', id=product_id))

    form = OrderForm()
    if form.validate_on_submit():
        success, message, order = order_service.submit_order(
            buyer_id=current_user.user_id,
            product_id=product_id,
            trade_type=form.trade_type.data,
            buyer_message=form.buyer_message.data
        )
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('order.buyer_list'))
    return render_template('order/submit.html', product=product, form=form)


@order_bp.route('/buyer')
@login_required
def buyer_list():
    status = request.args.get('status', '')
    keyword = request.args.get('keyword', '')
    orders = order_service.get_buyer_orders(
        current_user.user_id, 
        status_filter=status or None,
        keyword=keyword or None
    )
    pagination = paginate(orders, per_page=20)
    return render_template('order/buyer_list.html',
                         orders=pagination.items, pagination=pagination,
                         current_filter=status, keyword=keyword)


@order_bp.route('/seller')
@login_required
def seller_list():
    status = request.args.get('status', '')
    keyword = request.args.get('keyword', '')
    pending_count = order_service.get_pending_count(current_user.user_id)
    orders = order_service.get_seller_orders(
        current_user.user_id, 
        status_filter=status or None,
        keyword=keyword or None
    )
    pagination = paginate(orders, per_page=20)
    return render_template('order/seller_list.html',
                         orders=pagination.items, pagination=pagination,
                         current_filter=status, keyword=keyword,
                         pending_count=pending_count)


@order_bp.route('/<int:id>')
@login_required
def detail(id):
    order = db.session.get(Order, id)
    if not order or order.deleted:
        flash('订单不存在。', 'danger')
        return redirect(url_for('browse.home'))
    if current_user.user_id not in (order.buyer_id, order.seller_id):
        flash('无权查看此订单。', 'danger')
        return redirect(url_for('browse.home'))

    product = db.session.get(Product, order.product_id)
    buyer = order.buyer
    seller = order.seller_ref
    reject_form = RejectForm()
    return render_template('order/detail.html', order=order, product=product,
                         buyer=buyer, seller=seller, reject_form=reject_form)


@order_bp.route('/<int:id>/confirm', methods=['POST'])
@login_required
def confirm(id):
    order = db.session.get(Order, id)
    if not order:
        flash('订单不存在。', 'danger')
        return redirect(url_for('browse.home'))
    success, message = order_service.seller_confirm_order(order, current_user.user_id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('order.detail', id=id))


@order_bp.route('/<int:id>/reject', methods=['POST'])
@login_required
def reject(id):
    order = db.session.get(Order, id)
    if not order:
        flash('订单不存在。', 'danger')
        return redirect(url_for('browse.home'))
    reason = request.form.get('reason', '').strip()
    success, message = order_service.seller_reject_order(order, current_user.user_id, reason)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('order.detail', id=id))


@order_bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
def cancel(id):
    order = db.session.get(Order, id)
    if not order:
        flash('订单不存在。', 'danger')
        return redirect(url_for('browse.home'))
    success, message = order_service.buyer_cancel_order(order, current_user.user_id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('order.detail', id=id))


@order_bp.route('/<int:id>/pay', methods=['POST'])
@login_required
def pay(id):
    order = db.session.get(Order, id)
    if not order:
        flash('订单不存在。', 'danger')
        return redirect(url_for('browse.home'))
    success, message = order_service.simulate_payment(order, current_user.user_id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('order.detail', id=id))


@order_bp.route('/<int:id>/complete', methods=['POST'])
@login_required
def complete(id):
    order = db.session.get(Order, id)
    if not order:
        flash('订单不存在。', 'danger')
        return redirect(url_for('browse.home'))
    success, message = order_service.buyer_complete_order(order, current_user.user_id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('order.detail', id=id))

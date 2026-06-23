import secrets
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.product import product_bp
from app.blueprints.product.forms import ProductForm
from app.models.product import Product
from app.models.category import Category
from app.services import product_service
from app.utils.pagination import paginate
from app.utils.decorators import active_user_required


def get_product_submission_token():
    token = session.get('product_submission_token')
    if not token:
        token = secrets.token_hex(16)
        session['product_submission_token'] = token
    return token


def rotate_product_submission_token():
    token = secrets.token_hex(16)
    session['product_submission_token'] = token
    return token


@product_bp.route('/publish', methods=['GET', 'POST'])
@login_required
@active_user_required
def publish():
    form = ProductForm()
    form.category_id.choices = [
        (c.category_id, c.category_name)
        for c in Category.enabled().order_by(Category.category_name).all()
    ]
    if not form.category_id.choices:
        flash('当前没有可用商品分类，暂时无法发布商品。', 'warning')
        return redirect(url_for('browse.home'))
    if not form.is_submitted():
        form.submission_token.data = get_product_submission_token()
    if form.validate_on_submit():
        if form.submission_token.data != session.get('product_submission_token'):
            flash('请勿重复提交商品。', 'warning')
            form.submission_token.data = get_product_submission_token()
            return render_template('product/publish.html', form=form, categories=form.category_id.choices)
        images = request.files.getlist('images')
        submit = form.submit_publish.data
        success, message, product = product_service.create_product(
            seller_id=current_user.user_id,
            name=form.product_name.data,
            category_id=form.category_id.data,
            price=form.price.data,
            condition_level=form.condition_level.data,
            description=form.description.data,
            trade_location=form.trade_location.data,
            images=images if any(f and f.filename for f in images) else None,
            submit=bool(submit)
        )
        flash(message, 'success' if success else 'danger')
        if success:
            rotate_product_submission_token()
            return redirect(url_for('product.my_products'))
    form.submission_token.data = get_product_submission_token()
    return render_template('product/publish.html', form=form, categories=form.category_id.choices)


@product_bp.route('/my')
@login_required
@active_user_required
def my_products():
    status = request.args.get('status', '')
    products = product_service.get_my_products(current_user.user_id, status_filter=status or None)
    pagination = paginate(products)
    return render_template('product/my_products.html',
                         products=pagination.items, pagination=pagination,
                         current_filter=status)


@product_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@active_user_required
def edit(id):
    product = db.session.get(Product, id)
    if not product or product.deleted:
        flash('商品不存在。', 'danger')
        return redirect(url_for('product.my_products'))
    if product.seller_id != current_user.user_id:
        flash('无权编辑此商品。', 'danger')
        return redirect(url_for('product.my_products'))

    form = ProductForm(obj=product)
    form.category_id.choices = [
        (c.category_id, c.category_name)
        for c in Category.enabled().order_by(Category.category_name).all()
    ]
    if not form.is_submitted():
        form.category_id.data = product.category_id
        form.condition_level.data = product.condition_level

    if form.validate_on_submit():
        images = request.files.getlist('images')
        submit = form.submit_publish.data
        image_orders = {
            key.removeprefix('image_order_'): value
            for key, value in request.form.items()
            if key.startswith('image_order_')
        }
        delete_image_ids = [
            value for value in request.form.getlist('delete_image_ids')
            if value and value.isdigit()
        ]
        success, message = product_service.update_product(
            product=product,
            name=form.product_name.data,
            category_id=form.category_id.data,
            price=form.price.data,
            condition_level=form.condition_level.data,
            description=form.description.data,
            trade_location=form.trade_location.data,
            images=images if any(f and f.filename for f in images) else None,
            submit=bool(submit),
            image_orders=image_orders,
            delete_image_ids=delete_image_ids
        )
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('product.my_products'))
    return render_template('product/edit.html', form=form, product=product)


@product_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@active_user_required
def delete(id):
    product = db.session.get(Product, id)
    if not product or product.deleted:
        flash('商品不存在。', 'danger')
        return redirect(url_for('product.my_products'))
    if product.seller_id != current_user.user_id:
        flash('无权操作。', 'danger')
        return redirect(url_for('product.my_products'))
    success, message = product_service.delete_product(product)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('product.my_products'))


@product_bp.route('/toggle/<int:id>', methods=['POST'])
@login_required
@active_user_required
def toggle(id):
    product = db.session.get(Product, id)
    if not product or product.deleted:
        flash('商品不存在。', 'danger')
        return redirect(url_for('product.my_products'))
    if product.seller_id != current_user.user_id:
        flash('无权操作。', 'danger')
        return redirect(url_for('product.my_products'))
    success, message = product_service.toggle_product_status(product)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('product.my_products'))

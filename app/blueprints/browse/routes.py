from datetime import datetime, timedelta
from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload
from app.extensions import db
from app.blueprints.browse import browse_bp
from app.models.product import Product
from app.models.favorite import Favorite
from app.models.product_comment import ProductComment
from app.services import browse_service, favorite_service
from app.services.notification_service import create_notification


@browse_bp.route('/')
def home():
    try:
        candidates = Product.on_sale().options(
            selectinload(Product.images),
            selectinload(Product.seller)
        ).order_by(Product.created_at.desc()).limit(100).all()
    except Exception:
        db.session.rollback()
        candidates = []

    newest = candidates[:12]
    week_ago = datetime.utcnow() - timedelta(days=7)
    hottest = sorted(
        (product for product in candidates if product.created_at >= week_ago),
        key=lambda product: product.view_count or 0,
        reverse=True,
    )[:12]
    return render_template('browse/home.html',
                         newest_products=newest, 
                         hot_products=hottest,
                         query=request.args.get('q', ''))


@browse_bp.route('/category/<int:id>')
def category(id):
    success, message, payload = browse_service.get_category_browse_payload(
        category_id=id,
        sort=request.args.get('sort'),
        page=request.args.get('page'),
    )
    if not success:
        flash(message, 'warning')
        return redirect(url_for('browse.home'))

    return render_template('browse/category.html',
                         category=payload['category'],
                         products=payload['products'],
                         pagination=payload['pagination'],
                         current_sort=payload['current_sort'])


@browse_bp.route('/search')
def search():
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    condition = request.args.get('condition', '')
    success, message, payload = browse_service.get_search_payload(
        keyword=request.args.get('q', ''),
        sort=request.args.get('sort'),
        page=request.args.get('page'),
        min_price=min_price,
        max_price=max_price,
        condition=condition,
    )
    if not success:
        flash(message, 'warning')

    return render_template('browse/search.html',
                         products=payload['products'],
                         pagination=payload['pagination'],
                         query=payload['query'],
                         min_price=payload['min_price'],
                         max_price=payload['max_price'],
                         condition=payload['condition'],
                         sort=payload['sort'])


@browse_bp.route('/product/<int:id>', methods=['GET', 'POST'])
def detail(id):
    product = db.session.get(Product, id)
    if not product or product.deleted:
        flash('商品不存在或已下架。', 'warning')
        return redirect(url_for('browse.home'))
    if product.product_status != 'ON_SALE':
        can_view_unlisted = (
            current_user.is_authenticated and (
                current_user.user_id == product.seller_id or current_user.is_admin()
            )
        )
        if not can_view_unlisted:
            flash('商品不存在或已下架。', 'warning')
            return redirect(url_for('browse.home'))

    # 提交留言
    if request.method == 'POST' and current_user.is_authenticated:
        content = request.form.get('comment_content', '').strip()
        if content:
            comment = ProductComment(
                product_id=product.product_id,
                user_id=current_user.user_id,
                comment_content=content
            )
            db.session.add(comment)
            db.session.commit()
            flash('留言成功！', 'success')
            return redirect(url_for('browse.detail', id=id))

    product.view_count = (product.view_count or 0) + 1
    db.session.commit()

    seller = product.seller
    is_favorited = False
    favorite_count = 0
    if current_user.is_authenticated:
        is_favorited = favorite_service.check_is_favorited(
            current_user.user_id, product.product_id
        )
        favorite_count = favorite_service.get_favorite_count(
            current_user.user_id
        )
    
    # 获取留言列表
    comments = ProductComment.active().filter_by(
        product_id=product.product_id
    ).options(
        selectinload(ProductComment.user)
    ).order_by(ProductComment.created_at.desc()).all()

    return render_template('browse/detail.html',
                         product=product, seller=seller,
                         is_favorited=is_favorited,
                         favorite_count=favorite_count,
                         comments=comments)


@browse_bp.route('/favorite/toggle/<int:product_id>', methods=['POST'])
@login_required
def toggle_favorite(product_id):
    """收藏或取消收藏商品"""
    success, message, data = favorite_service.toggle_favorite(
        user_id=current_user.user_id,
        product_id=product_id,
        allow_own_product=False
    )

    # 收藏时通知卖家
    if success and data.get('is_favorited'):
        product = db.session.get(Product, product_id)
        if product and product.seller_id != current_user.user_id:
            create_notification(
                receiver_id=product.seller_id, ntype='FAVORITE',
                title='商品被收藏',
                content=f'用户 {current_user.nickname or current_user.username} 收藏了您的商品「{product.product_name}」。',
                related_id=product_id, sender_id=current_user.user_id
            )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': success,
            'message': message,
            'is_favorited': data.get('is_favorited', False),
            'favorite_count': data.get('favorite_count', 0)
        })

    if success:
        flash(message, 'success')
    else:
        flash(message, 'warning')

    return redirect(request.referrer or url_for('browse.detail', id=product_id))


@browse_bp.route('/favorites')
@login_required
def favorites():
    """收藏列表页面"""
    success, message, data = favorite_service.get_favorite_list(
        user_id=current_user.user_id,
        page=request.args.get('page')
    )

    return render_template('browse/favorites.html',
                         products=data.get('products', []),
                         pagination=data.get('pagination'))

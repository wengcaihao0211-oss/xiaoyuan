from datetime import datetime, timedelta
from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload
from app.extensions import db
from app.blueprints.browse import browse_bp
from app.models.product import Product
from app.models.category import Category
from app.models.favorite import Favorite
from app.utils.pagination import paginate


@browse_bp.route('/')
def home():
    try:
        candidates = Product.on_sale().options(
            selectinload(Product.images)
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
                         newest_products=newest, hot_products=hottest)


@browse_bp.route('/category/<int:id>')
def category(id):
    cat = db.session.get(Category, id)
    if not cat or cat.status != 'ENABLED':
        flash('分类不存在或已禁用。', 'warning')
        return redirect(url_for('browse.home'))
    products = Product.on_sale().filter_by(category_id=id).order_by(Product.created_at.desc())
    pagination = paginate(products)
    return render_template('browse/category.html',
                         category=cat, products=pagination.items,
                         pagination=pagination)


@browse_bp.route('/search')
def search():
    q = request.args.get('q', '').strip()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    condition = request.args.get('condition', '')
    sort = request.args.get('sort', 'newest')

    query = Product.on_sale()
    if q:
        query = query.filter(Product.product_name.contains(q))
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if condition:
        query = query.filter_by(condition_level=condition)

    if sort == 'price_low':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_high':
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    pagination = paginate(query)
    return render_template('browse/search.html',
                         products=pagination.items, pagination=pagination,
                         query=q, min_price=min_price, max_price=max_price,
                         condition=condition, sort=sort)


@browse_bp.route('/product/<int:id>')
def detail(id):
    product = db.session.get(Product, id)
    if not product or product.deleted:
        flash('商品不存在或已下架。', 'warning')
        return redirect(url_for('browse.home'))

    product.view_count = (product.view_count or 0) + 1
    db.session.commit()

    seller = product.seller
    is_favorited = False
    if current_user.is_authenticated:
        fav = Favorite.query.filter_by(
            user_id=current_user.user_id, product_id=product.product_id
        ).first()
        is_favorited = fav is not None

    return render_template('browse/detail.html',
                         product=product, seller=seller,
                         is_favorited=is_favorited)


@browse_bp.route('/favorite/toggle/<int:product_id>', methods=['POST'])
@login_required
def toggle_favorite(product_id):
    product = db.session.get(Product, product_id)
    if not product or product.deleted:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': '商品不存在'})
        flash('商品不存在。', 'danger')
        return redirect(request.referrer or url_for('browse.home'))

    fav = Favorite.query.filter_by(
        user_id=current_user.user_id, product_id=product_id
    ).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
        msg = '已取消收藏'
        is_fav = False
    else:
        fav = Favorite(user_id=current_user.user_id, product_id=product_id)
        db.session.add(fav)
        db.session.commit()
        msg = '已添加收藏'
        is_fav = True

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': msg, 'is_favorited': is_fav})
    flash(msg, 'success')
    return redirect(request.referrer or url_for('browse.detail', id=product_id))


@browse_bp.route('/favorites')
@login_required
def favorites():
    favs = Favorite.query.filter_by(user_id=current_user.user_id).order_by(
        Favorite.created_at.desc()
    ).all()
    products = []
    for fav in favs:
        p = db.session.get(Product, fav.product_id)
        if p and not p.deleted:
            products.append(p)
    return render_template('browse/favorites.html', products=products)

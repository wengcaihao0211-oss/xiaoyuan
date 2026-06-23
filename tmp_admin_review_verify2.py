# -*- coding: utf-8 -*-
from decimal import Decimal
from flask_login.utils import _create_identifier
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.category import Category
from app.models.product import Product

app = create_app()
app.config['TESTING'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True

with app.app_context():
    admin = User.query.filter_by(role='ADMIN', deleted=False, status='ACTIVE').order_by(User.user_id.asc()).first()
    seller = User.query.filter(User.role != 'ADMIN').first()
    category = Category.enabled().first()
    product = Product(
        seller_id=seller.user_id,
        category_id=category.category_id,
        product_name='DEBUG-ADMIN-REVIEW-VERIFY2',
        price=Decimal('78.90'),
        condition_level='九成新',
        description='这是用于验证管理员审核修复的临时商品描述。',
        trade_location='测试地点',
        product_status='PENDING_REVIEW'
    )
    db.session.add(product)
    db.session.commit()
    product_id = product.product_id
    admin_id = admin.user_id
    session_version = admin.session_version
    print({'created_product_id': product_id, 'admin_id': admin_id, 'admin_username': admin.username})

with app.test_request_context('/'):
    session_id = _create_identifier()

client = app.test_client()
with client.session_transaction() as sess:
    sess['_user_id'] = str(admin_id)
    sess['_fresh'] = True
    sess['_id'] = session_id
    sess['session_version'] = session_version

approve_response = client.post(f'/admin/products/{product_id}/approve', follow_redirects=False)
review_response = client.get('/admin/products/review', follow_redirects=False)
review_text = review_response.get_data(as_text=True)
print({'approve_status_code': approve_response.status_code, 'approve_location': approve_response.headers.get('Location')})
print({'review_status_code': review_response.status_code, 'contains_review_title': '商品审核' in review_text, 'contains_success_message': '商品已通过审核并上架。' in review_text})

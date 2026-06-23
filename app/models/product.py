from datetime import datetime
from app.extensions import db
from sqlalchemy import CheckConstraint
from app.models.product_image import ProductImage


class Product(db.Model):
    __tablename__ = 'product'
    __table_args__ = (
        CheckConstraint('price >= 0', name='chk_product_price'),
    )

    product_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='商品编号')
    seller_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment='卖家编号')
    category_id = db.Column(db.Integer, db.ForeignKey('category.category_id'), nullable=False, comment='分类编号')
    product_name = db.Column(db.String(150), nullable=False, comment='商品名称')
    price = db.Column(db.Numeric(10, 2), nullable=False, comment='商品价格')
    condition_level = db.Column(db.String(30), nullable=False, comment='商品成色')
    description = db.Column(db.Text, nullable=False, comment='商品描述')
    trade_location = db.Column(db.String(255), nullable=False, comment='交易地点')
    product_status = db.Column(db.String(30), nullable=False, default='DRAFT', comment='商品状态')
    view_count = db.Column(db.Integer, nullable=False, default=0, comment='浏览次数')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted = db.Column(db.Boolean, nullable=False, default=False, comment='逻辑删除标志')

    # Relationships
    images = db.relationship(
        'ProductImage',
        backref='product',
        lazy='selectin',
        order_by='ProductImage.sort_order',
    )
    favorites = db.relationship('Favorite', backref='product', lazy='dynamic')
    orders = db.relationship('Order', backref='product', lazy='dynamic')
    messages = db.relationship('Message', backref='product', lazy='dynamic')
    comments = db.relationship('ProductComment', back_populates='product', lazy='dynamic')

    @classmethod
    def active(cls):
        return cls.query.filter_by(deleted=False)

    @classmethod
    def on_sale(cls):
        return cls.active().filter_by(product_status='ON_SALE')

    @property
    def cover_image(self):
        img = self.images[0] if self.images else None
        return img.image_url if img else None

    @property
    def image_list(self):
        return [img.image_url for img in self.images]

    @property
    def favorite_count(self):
        return self.favorites.count()

    def __repr__(self):
        return f'<Product {self.product_name}>'

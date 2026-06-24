from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    __table_args__ = (
        db.Index('idx_users_status_deleted', 'status', 'deleted'),
    )

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='用户编号')
    username = db.Column(db.String(50), unique=True, nullable=False, comment='用户名')
    password_hash = db.Column(db.String(255), nullable=False, comment='密码哈希')
    avatar = db.Column(db.String(500), nullable=True, comment='头像地址')
    phone = db.Column(db.String(30), nullable=True, comment='手机号')
    email = db.Column(db.String(255), nullable=True, comment='邮箱')
    nickname = db.Column(db.String(50), nullable=True, comment='昵称')
    introduction = db.Column(db.String(500), nullable=True, comment='个人简介')
    role = db.Column(db.String(20), nullable=False, default='USER', comment='用户角色')
    status = db.Column(db.String(20), nullable=False, default='ACTIVE', comment='账号状态')
    last_login_at = db.Column(db.DateTime, nullable=True, comment='最后登录时间')
    last_login_ip = db.Column(db.String(45), nullable=True, comment='最后登录IP')
    password_changed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, comment='密码最近修改时间')
    session_version = db.Column(db.Integer, nullable=False, default=1, comment='会话版本号')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    deleted = db.Column(db.Boolean, nullable=False, default=False, comment='逻辑删除标志')

    # Relationships
    products = db.relationship('Product', backref='seller', lazy='dynamic', foreign_keys='Product.seller_id')
    orders_as_buyer = db.relationship('Order', backref='buyer', lazy='dynamic', foreign_keys='Order.buyer_id')
    orders_as_seller = db.relationship('Order', backref='seller_ref', lazy='dynamic', foreign_keys='Order.seller_id')
    favorites = db.relationship('Favorite', backref='user', lazy='dynamic')
    messages_sent = db.relationship('Message', backref='sender', lazy='dynamic', foreign_keys='Message.sender_id')
    messages_received = db.relationship('Message', backref='receiver', lazy='dynamic', foreign_keys='Message.receiver_id')
    reviews_given = db.relationship('Review', backref='reviewer', lazy='dynamic', foreign_keys='Review.reviewer_id')
    reviews_received = db.relationship('Review', backref='reviewed_user', lazy='dynamic', foreign_keys='Review.reviewed_user_id')
    reports_filed = db.relationship('Report', backref='reporter', lazy='dynamic', foreign_keys='Report.reporter_id')
    notifications = db.relationship('Notification', backref='receiver_ref', lazy='dynamic', foreign_keys='Notification.receiver_id')

    def get_id(self):
        return str(self.user_id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.password_changed_at = datetime.utcnow()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @classmethod
    def active(cls):
        return cls.query.filter_by(deleted=False)

    def is_admin(self):
        return self.role == 'ADMIN'

    def __repr__(self):
        return f'<User {self.username}>'

    @property
    def avg_rating(self):
        from app.models.review import Review
        result = db.session.query(
            db.func.avg(Review.score)
        ).filter(
            Review.reviewed_user_id == self.user_id,
            Review.deleted == False
        ).scalar()
        return round(float(result), 1) if result else None

    @property
    def sold_count(self):
        from app.models.product import Product
        return Product.active().filter(
            Product.seller_id == self.user_id,
            Product.product_status == 'SOLD'
        ).count()

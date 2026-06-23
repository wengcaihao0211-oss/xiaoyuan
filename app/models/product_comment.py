from datetime import datetime
from app.extensions import db


class ProductComment(db.Model):
    __tablename__ = 'product_comment'
    
    comment_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='留言编号')
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False, comment='商品编号')
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment='发布者编号')
    comment_content = db.Column(db.Text, nullable=False, comment='留言内容')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    deleted = db.Column(db.Boolean, nullable=False, default=False, comment='逻辑删除标志')
    
    # Relationships
    product = db.relationship('Product', back_populates='comments')
    user = db.relationship('User', backref='comments')
    
    @classmethod
    def active(cls):
        return cls.query.filter_by(deleted=False)

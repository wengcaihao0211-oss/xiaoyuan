from datetime import datetime
from app.extensions import db
from sqlalchemy import CheckConstraint


class Review(db.Model):
    __tablename__ = 'review'
    __table_args__ = (
        db.UniqueConstraint('order_id', 'reviewer_id', name='uk_review_order_reviewer'),
        CheckConstraint('score BETWEEN 1 AND 5', name='chk_review_score'),
        CheckConstraint('reviewer_id <> reviewed_user_id', name='chk_review_users'),
    )

    review_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='评价编号')
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False, comment='订单编号')
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment='评价人编号')
    reviewed_user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment='被评价人编号')
    score = db.Column(db.SmallInteger, nullable=False, comment='评分')
    review_content = db.Column(db.String(500), nullable=True, comment='评价内容')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    deleted = db.Column(db.Boolean, nullable=False, default=False, comment='逻辑删除标志')

    @classmethod
    def active(cls):
        return cls.query.filter_by(deleted=False)

    def __repr__(self):
        return f'<Review {self.review_id} score={self.score}>'

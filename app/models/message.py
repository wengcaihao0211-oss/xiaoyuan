from datetime import datetime
from app.extensions import db
from sqlalchemy import CheckConstraint


class Message(db.Model):
    __tablename__ = 'message'
    __table_args__ = (
        CheckConstraint('sender_id <> receiver_id', name='chk_message_users'),
    )

    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='消息编号')
    sender_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment='发送者编号')
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment='接收者编号')
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=True, comment='关联商品编号')
    message_content = db.Column(db.Text, nullable=False, comment='消息内容')
    read_status = db.Column(db.Boolean, nullable=False, default=False, comment='阅读状态')
    read_time = db.Column(db.DateTime, nullable=True, comment='阅读时间')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    deleted = db.Column(db.Boolean, nullable=False, default=False, comment='逻辑删除标志')

    @classmethod
    def active(cls):
        return cls.query.filter_by(deleted=False)
    
    @classmethod
    def get_unread_count(cls, user_id):
        """获取用户总未读消息数"""
        return cls.active().filter(
            cls.receiver_id == user_id,
            cls.read_status == False
        ).count()
    
    @classmethod
    def get_conversation_unread_count(cls, user_id, other_user_id, product_id):
        """获取特定会话的未读消息数"""
        return cls.active().filter(
            cls.sender_id == other_user_id,
            cls.receiver_id == user_id,
            cls.product_id == product_id,
            cls.read_status == False
        ).count()

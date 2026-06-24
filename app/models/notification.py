from datetime import datetime
from app.extensions import db


class Notification(db.Model):
    __tablename__ = 'notification'

    notification_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='通知编号')
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment='接收者编号')
    sender_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True, comment='触发者编号')
    notification_type = db.Column(db.String(30), nullable=False, comment='通知类型')
    title = db.Column(db.String(200), nullable=False, comment='通知标题')
    content = db.Column(db.Text, nullable=False, comment='通知内容')
    related_id = db.Column(db.Integer, nullable=True, comment='关联业务编号')
    read_status = db.Column(db.Boolean, nullable=False, default=False, comment='阅读状态')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    deleted = db.Column(db.Boolean, nullable=False, default=False, comment='逻辑删除标志')

    TYPE_DISPLAY = {
        'SYSTEM': '系统通知',
        'ORDER': '订单通知',
        'AUDIT': '审核通知',
        'ACCOUNT': '账号通知',
        'REPORT': '举报通知',
        'REVIEW': '评价通知',
        'FAVORITE': '收藏通知',
    }

    _ENDPOINT_MAP = {
        'ORDER': ('order.detail', 'id'),
        'AUDIT': ('browse.detail', 'id'),
        'REPORT': ('user.report_result', 'report_id'),
    }

    _RELATED_CLASS = {
        'ORDER': ('app.models.orders', 'Order'),
        'AUDIT': ('app.models.product', 'Product'),
        'REPORT': ('app.models.report', 'Report'),
    }

    @classmethod
    def active(cls):
        return cls.query.filter_by(deleted=False)

    @property
    def type_display(self):
        return self.TYPE_DISPLAY.get(self.notification_type, self.notification_type)

    @property
    def related_exists(self):
        spec = self._RELATED_CLASS.get(self.notification_type)
        if not spec or not self.related_id:
            return True
        module_path, class_name = spec
        import importlib
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        return db.session.get(cls, self.related_id) is not None

    @property
    def target_url(self):
        spec = self._ENDPOINT_MAP.get(self.notification_type)
        if not spec or not self.related_id:
            return None
        if not self.related_exists:
            return None
        endpoint, param_name = spec
        from flask import url_for
        try:
            return url_for(endpoint, **{param_name: self.related_id})
        except Exception:
            return None

    @property
    def sender_name(self):
        if not self.sender_id:
            return None
        from app.models.user import User
        sender = db.session.get(User, self.sender_id)
        return sender.nickname or sender.username if sender else None

    def __repr__(self):
        return f'<Notification {self.notification_id} type={self.notification_type}>'

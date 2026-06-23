from datetime import datetime
from app.extensions import db


class Report(db.Model):
    __tablename__ = 'report'

    report_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='举报编号')
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment='举报人编号')
    target_type = db.Column(db.String(30), nullable=False, comment='举报对象类型')
    target_id = db.Column(db.Integer, nullable=False, comment='举报对象编号')
    report_reason = db.Column(db.String(100), nullable=False, comment='举报原因')
    description = db.Column(db.String(500), nullable=True, comment='举报说明')
    target_snapshot = db.Column(db.JSON, nullable=True, comment='举报目标快照')
    report_status = db.Column(db.String(30), nullable=False, default='PENDING', comment='处理状态')
    handle_result = db.Column(db.String(1000), nullable=True, comment='处理结果')
    handler_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True, comment='管理员编号')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    handled_at = db.Column(db.DateTime, nullable=True, comment='处理时间')

    # Relationships
    handler = db.relationship('User', foreign_keys=[handler_id])

    STATUS_DISPLAY = {
        'PENDING': '待处理',
        'DISMISSED': '已驳回',
        'TAKEDOWN': '已下架',
        'DISABLED': '已封禁用户',
    }

    @property
    def status_display(self):
        return self.STATUS_DISPLAY.get(self.report_status, self.report_status)

    def __repr__(self):
        return f'<Report {self.report_id} type={self.target_type}>'

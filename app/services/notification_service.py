from app.extensions import db
from app.models.notification import Notification


def create_notification(receiver_id, ntype, title, content, related_id=None, sender_id=None):
    notif = Notification(
        receiver_id=receiver_id, sender_id=sender_id,
        notification_type=ntype, title=title, content=content,
        related_id=related_id
    )
    db.session.add(notif)
    db.session.commit()
    return True, '通知已创建', notif


def get_user_notifications(user_id, type_filter=None, page=1, per_page=20):
    q = Notification.active().filter_by(receiver_id=user_id)
    if type_filter:
        q = q.filter_by(notification_type=type_filter)
    return q.order_by(Notification.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)


def get_notification_by_id(notification_id, user_id):
    notif = Notification.active().filter_by(
        notification_id=notification_id, receiver_id=user_id).first()
    if not notif:
        return False, '通知不存在或无权访问', None
    return True, '', notif


def get_unread_count(user_id):
    return Notification.active().filter_by(
        receiver_id=user_id, read_status=False).count()


def mark_all_read(user_id):
    Notification.active().filter_by(
        receiver_id=user_id, read_status=False
    ).update({'read_status': True}, synchronize_session='fetch')
    db.session.commit()


def mark_read(notification_id, user_id):
    notif = Notification.active().filter_by(
        notification_id=notification_id, receiver_id=user_id).first()
    if not notif:
        return False, '通知不存在或无权访问', None
    if not notif.read_status:
        notif.read_status = True
        db.session.commit()
    return True, '已标记为已读', notif


def delete_notification(notification_id, user_id):
    notif = Notification.active().filter_by(
        notification_id=notification_id, receiver_id=user_id).first()
    if not notif:
        return False, '通知不存在或无权访问', None
    notif.deleted = True
    db.session.commit()
    return True, '已删除', notif


def delete_all(user_id):
    Notification.active().filter_by(receiver_id=user_id).update(
        {'deleted': True}, synchronize_session='fetch')
    db.session.commit()
    return True, '所有通知已删除'


def restore_notification(notification_id, user_id):
    notif = Notification.query.filter_by(
        notification_id=notification_id, receiver_id=user_id, deleted=True).first()
    if not notif:
        return False, '通知不存在或无权访问', None
    notif.deleted = False
    db.session.commit()
    return True, '已恢复', notif


def notify_admins(title, content, related_id=None, sender_id=None):
    from app.models.user import User
    admins = User.active().filter_by(role='ADMIN').all()
    for admin in admins:
        create_notification(
            receiver_id=admin.user_id, ntype='SYSTEM',
            title=title, content=content,
            related_id=related_id, sender_id=sender_id
        )

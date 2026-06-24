from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.blueprints.notification import notification_bp
from app.services import notification_service


@notification_bp.route('/')
@login_required
def list():
    ntype = request.args.get('type', '')
    page = request.args.get('page', 1, type=int)
    notifications = notification_service.get_user_notifications(
        current_user.user_id, type_filter=ntype or None, page=page
    )
    return render_template('notification/list.html',
                         notifications=notifications.items,
                         pagination=notifications,
                         current_filter=ntype)


@notification_bp.route('/<int:nid>')
@login_required
def detail(nid):
    success, msg, notif = notification_service.get_notification_by_id(nid, current_user.user_id)
    if not success:
        flash(msg, 'danger')
        return redirect(url_for('notification.list'))
    if not notif.read_status:
        notification_service.mark_read(nid, current_user.user_id)
    return render_template('notification/detail.html', notification=notif)


@notification_bp.route('/<int:nid>/read', methods=['POST'])
@login_required
def read_single(nid):
    success, msg, notif = notification_service.mark_read(nid, current_user.user_id)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': msg})
    flash(msg, 'success' if success else 'warning')
    return redirect(url_for('notification.list'))


@notification_bp.route('/<int:nid>/delete', methods=['POST'])
@login_required
def delete(nid):
    success, msg, notif = notification_service.delete_notification(nid, current_user.user_id)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': msg})
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('notification.list'))


@notification_bp.route('/read-all', methods=['POST'])
@login_required
def read_all():
    notification_service.mark_all_read(current_user.user_id)
    flash('所有通知已标记为已读。', 'success')
    return redirect(url_for('notification.list'))


@notification_bp.route('/delete-all', methods=['POST'])
@login_required
def delete_all():
    success, msg = notification_service.delete_all(current_user.user_id)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': msg})
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('notification.list'))

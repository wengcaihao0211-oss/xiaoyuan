from datetime import datetime, timedelta
import json
import urllib.request
from app.extensions import db
from app.models.user import User
from app.models.product import Product
from app.models.orders import Order
from app.models.category import Category
from app.models.report import Report
from app.models.notification import Notification
from app.services.ai_review_service import AIReviewService
from app.services.notification_service import create_notification


# #region debug-point B:admin-review-service
def _report_admin_review_service(hypothesis_id, location, message, data=None, trace_id=None):
    _u = 'http://127.0.0.1:7777/event'
    _s = 'admin-review-500'
    try:
        with open('.dbg/admin-review-500.env', encoding='utf-8') as _f:
            for _line in _f:
                if _line.startswith('DEBUG_SERVER_URL='):
                    _u = _line.split('=', 1)[1].strip() or _u
                elif _line.startswith('DEBUG_SESSION_ID='):
                    _s = _line.split('=', 1)[1].strip() or _s
        _payload = {
            'sessionId': _s,
            'runId': 'pre-fix',
            'hypothesisId': hypothesis_id,
            'location': location,
            'msg': f'[DEBUG] {message}',
            'data': data or {},
        }
        if trace_id:
            _payload['traceId'] = trace_id
        urllib.request.urlopen(urllib.request.Request(
            _u,
            data=json.dumps(_payload).encode(),
            headers={'Content-Type': 'application/json'}
        ), timeout=1).read()
    except Exception:
        pass
# #endregion


def get_dashboard_stats(start_date=None, end_date=None):
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    total_users = User.active().count()
    active_users = User.active().filter_by(status='ACTIVE').count()
    total_products = Product.active().count()
    on_sale_products = Product.on_sale().count()

    total_orders = Order.active().filter(
        Order.created_at >= start_date, Order.created_at <= end_date).count()
    completed_orders = Order.active().filter(
        Order.order_status == 'COMPLETED',
        Order.created_at >= start_date, Order.created_at <= end_date).count()
    completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0

    return {
        'total_users': total_users, 'active_users': active_users,
        'disabled_users': total_users - active_users,
        'total_products': total_products, 'on_sale_products': on_sale_products,
        'total_orders': total_orders, 'completed_orders': completed_orders,
        'completion_rate': round(completion_rate, 1),
        'pending_reports': Report.query.filter_by(report_status='PENDING').count(),
        'pending_products': Product.active().filter_by(product_status='PENDING_REVIEW').count(),
    }


def get_category_distribution():
    results = db.session.query(
        Category.category_name,
        db.func.count(Product.product_id)
    ).outerjoin(Product, db.and_(
        Product.category_id == Category.category_id, Product.deleted == False)
    ).group_by(Category.category_id).all()
    return [{'name': name, 'count': count} for name, count in results]


def toggle_user_status(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return False, '用户不存在。'
    if user.role == 'ADMIN':
        return False, '不能禁用管理员账号。'
    if user.status == 'ACTIVE':
        user.status = 'DISABLED'
        Product.active().filter_by(seller_id=user_id).update(
            {'product_status': 'OFF_SHELF'}, synchronize_session='fetch')
        db.session.commit()
        return True, f'用户 {user.username} 已被禁用。'
    else:
        user.status = 'ACTIVE'
        db.session.commit()
        return True, f'用户 {user.username} 已启用。'


def review_product(product_id, action, reason=None, trace_id=None):
    _report_admin_review_service(
        'B',
        'app/services/admin_service.py:review_product',
        'review product entered',
        {'product_id': product_id, 'action': action, 'has_reason': bool(reason and reason.strip())},
        trace_id
    )
    product = db.session.get(Product, product_id)
    if not product:
        _report_admin_review_service(
            'E',
            'app/services/admin_service.py:review_product',
            'product not found during review',
            {'product_id': product_id, 'action': action},
            trace_id
        )
        return False, '商品不存在。'
    if product.product_status != 'PENDING_REVIEW':
        _report_admin_review_service(
            'E',
            'app/services/admin_service.py:review_product',
            'product is not pending review',
            {'product_id': product_id, 'action': action, 'product_status': product.product_status},
            trace_id
        )
        return False, '该商品不在待审核状态。'

    try:
        if action == 'approve':
            product.product_status = 'ON_SALE'
            create_notification(
                receiver_id=product.seller_id, ntype='AUDIT',
                title='商品审核通过',
                content=f'您的商品「{product.product_name}」已通过审核，已自动上架。',
                related_id=product.product_id)
            _report_admin_review_service(
                'B',
                'app/services/admin_service.py:review_product',
                'approve before commit',
                {'product_id': product_id, 'seller_id': product.seller_id, 'new_status': product.product_status},
                trace_id
            )
            db.session.commit()
            _report_admin_review_service(
                'B',
                'app/services/admin_service.py:review_product',
                'approve commit succeeded',
                {'product_id': product_id, 'new_status': product.product_status},
                trace_id
            )
            return True, '商品已通过审核并上架。'
        if not reason or len(reason.strip()) < 2:
            _report_admin_review_service(
                'A',
                'app/services/admin_service.py:review_product',
                'reject blocked by invalid reason',
                {'product_id': product_id, 'reason_len': len((reason or '').strip())},
                trace_id
            )
            return False, '驳回原因至少需要2个字符。'
        product.product_status = 'REJECTED'
        create_notification(
            receiver_id=product.seller_id, ntype='AUDIT',
            title='商品审核未通过',
            content=f'您的商品「{product.product_name}」未通过审核。原因：{reason}',
            related_id=product.product_id)
        _report_admin_review_service(
            'B',
            'app/services/admin_service.py:review_product',
            'reject before commit',
            {'product_id': product_id, 'seller_id': product.seller_id, 'new_status': product.product_status, 'reason_len': len(reason.strip())},
            trace_id
        )
        db.session.commit()
        _report_admin_review_service(
            'B',
            'app/services/admin_service.py:review_product',
            'reject commit succeeded',
            {'product_id': product_id, 'new_status': product.product_status},
            trace_id
        )
        return True, '商品已驳回。'
    except Exception as error:
        db.session.rollback()
        _report_admin_review_service(
            'B',
            'app/services/admin_service.py:review_product',
            'review commit raised exception',
            {'product_id': product_id, 'action': action, 'error_type': type(error).__name__, 'error': str(error)},
            trace_id
        )
        raise


def admin_takedown_product(product_id, permanent=False):
    product = db.session.get(Product, product_id)
    if not product:
        return False, '商品不存在。'
    if product.product_status == 'OFF_SHELF' and not permanent:
        return False, '该商品已是下架状态。'
    if permanent:
        active_order = Order.active().filter(
            Order.product_id == product_id,
            Order.order_status.in_(['PENDING', 'CONFIRMED', 'PAID'])).first()
        if active_order:
            return False, '存在进行中的订单，无法永久删除。'
        product.deleted = True
        product.product_status = 'OFF_SHELF'
        db.session.commit()
        # 通知卖家商品已被永久删除
        _notify_seller_takedown(product, '您的商品已被管理员永久删除。')
        return True, '商品已永久删除。'
    else:
        product.product_status = 'OFF_SHELF'
        db.session.commit()
        # 通知卖家商品已被下架
        _notify_seller_takedown(product, '您的商品已被管理员下架。如有疑问请联系管理员。')
        return True, '商品已下架。'


def _notify_seller_takedown(product, msg):
    """通知卖家商品被管理员下架/删除。"""
    try:
        from app.models.notification import Notification
        notice = Notification(
            receiver_id=product.seller_id,
            notification_type='SYSTEM',
            title='商品管理通知',
            content=f'您的商品「{product.product_name}」{msg}',
            related_id=product.product_id,
        )
        db.session.add(notice)
        db.session.commit()
    except Exception:
        db.session.rollback()


def manage_category(action, category_id=None, name=None, description=None):
    if action == 'create':
        if not name or not name.strip():
            return False, '分类名称不能为空。'
        existing = Category.query.filter_by(category_name=name.strip()).first()
        if existing:
            return False, '分类名称已存在。'
        cat = Category(category_name=name.strip(), description=description)
        db.session.add(cat)
        db.session.commit()
        return True, f'分类「{name}」已创建。'

    cat = db.session.get(Category, category_id)
    if not cat:
        return False, '分类不存在。'

    if action == 'update':
        if name:
            cat.category_name = name.strip()
        if description is not None:
            cat.description = description
        db.session.commit()
        return True, '分类已更新。'
    elif action == 'toggle':
        cat.status = 'DISABLED' if cat.status == 'ENABLED' else 'ENABLED'
        db.session.commit()
        return True, f'分类已{"禁用" if cat.status == "DISABLED" else "启用"}。'
    elif action == 'delete':
        product_count = Product.active().filter_by(category_id=category_id).count()
        if product_count > 0:
            cat.status = 'DISABLED'
            db.session.commit()
            return False, f'该分类下有{product_count}个商品，已禁用而非删除。'
        db.session.delete(cat)
        db.session.commit()
        return True, '分类已删除。'

    return False, '无效操作。'


def get_pending_human_review_reports(page=1, per_page=20):
    """
    获取需要人工审核的举报列表
    """
    return AIReviewService.get_pending_human_reviews(page, per_page)


def get_ai_reviewed_reports(page=1, per_page=20):
    """
    获取AI已审核的举报列表
    """
    return AIReviewService.get_ai_reviewed_reports(page, per_page)


def get_ai_review_stats():
    """
    获取AI审核统计数据
    """
    total_reports = Report.query.count()
    ai_reviewed = Report.query.filter_by(ai_reviewed=True).count()
    pending_human = Report.query.filter_by(needs_human_review=True, report_status='PENDING').count()
    auto_handled = Report.query.filter(
        Report.ai_reviewed == True,
        Report.needs_human_review == False,
        Report.report_status != 'PENDING'
    ).count()
    
    # 按结果统计
    safe_count = Report.query.filter_by(ai_review_result='SAFE').count()
    violation_count = Report.query.filter_by(ai_review_result='VIOLATION').count()
    uncertain_count = Report.query.filter_by(ai_review_result='UNCERTAIN').count()
    
    return {
        'total_reports': total_reports,
        'ai_reviewed': ai_reviewed,
        'pending_human_review': pending_human,
        'auto_handled': auto_handled,
        'ai_review_rate': round(ai_reviewed / total_reports * 100, 1) if total_reports > 0 else 0,
        'results': {
            'safe': safe_count,
            'violation': violation_count,
            'uncertain': uncertain_count
        }
    }

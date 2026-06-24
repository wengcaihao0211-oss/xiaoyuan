from datetime import datetime
from app.extensions import db
from app.models.report import Report
from app.models.product import Product
from app.models.user import User
from app.services.ai_review_service import AIReviewService
from app.services.notification_service import notify_admins


def submit_report(reporter_id, target_type, target_id, reason, description=None):
    """
    提交举报
    """
    # 1. 校验举报人账号状态
    reporter = db.session.get(User, reporter_id)
    if not reporter or reporter.status != 'ACTIVE':
        return False, '举报人账号异常。'
    
    # 2. 校验举报目标
    target = _validate_target(target_type, target_id)
    if not target:
        return False, '举报目标不存在。'
    
    # 3. 检查是否举报自己
    if _is_self_report(reporter_id, target_type, target):
        return False, '不能举报自己。'
    
    # 4. 校验说明长度
    if description:
        desc_length = len(description.strip())
        if desc_length < 10:
            return False, '说明至少需要10个字符。'
        if desc_length > 500:
            return False, '说明不能超过500个字符。'
    
    # 5. 检查重复待处理举报
    existing = Report.query.filter_by(
        reporter_id=reporter_id, target_type=target_type,
        target_id=target_id, report_status='PENDING'
    ).first()
    if existing:
        return False, '您已有一个待处理的举报，请等待管理员处理。'
    
    # 6. 生成目标快照
    snapshot = _generate_snapshot(target_type, target)
    
    # 7. 保存举报
    report = Report(
        reporter_id=reporter_id,
        target_type=target_type,
        target_id=target_id,
        report_reason=reason.strip(),
        description=description.strip()[:500] if description else None,
        target_snapshot=snapshot,
        report_status='PENDING'
    )
    db.session.add(report)
    db.session.commit()
    
    # 通知管理员
    notify_admins(
        title='新举报待处理',
        content=f'收到新的{target_type}举报，原因：{reason}',
        related_id=report.report_id, sender_id=reporter_id
    )

    # 触发AI审核
    ai_result = AIReviewService.process_report(report)
    
    # 9. 根据AI审核结果返回不同的消息
    if ai_result['needs_human_review']:
        message = f'举报提交成功，举报编号：{report.report_id}，已由AI初步审核，需要人工复核。'
    elif ai_result['auto_handled']:
        message = f'举报提交成功，举报编号：{report.report_id}，已由AI自动处理完成。'
    else:
        message = f'举报提交成功，举报编号：{report.report_id}，管理员将尽快处理。'
    
    return True, message


def handle_report(report_id, handler_id, action, handle_result=None):
    report = db.session.get(Report, report_id)
    if not report:
        return False, '举报不存在。'
    if report.report_status != 'PENDING':
        return False, '该举报已被处理。'

    report.report_status = action
    report.handler_id = handler_id
    report.handled_at = datetime.utcnow()
    report.handle_result = handle_result

    if action == 'TAKEDOWN' and report.target_type == 'PRODUCT':
        product = db.session.get(Product, report.target_id)
        if product:
            product.product_status = 'OFF_SHELF'
    elif action == 'DISABLED' and report.target_type == 'USER':
        user = db.session.get(User, report.target_id)
        if user:
            user.status = 'DISABLED'
            Product.active().filter_by(seller_id=user.user_id).update(
                {'product_status': 'OFF_SHELF'}, synchronize_session='fetch')

    db.session.commit()
    return True, '举报已处理。'


def get_user_reports(user_id):
    """
    获取用户提交的举报列表
    """
    return Report.query.filter_by(reporter_id=user_id).order_by(
        Report.created_at.desc()).all()


def get_report_detail(report_id, user_id):
    """
    获取举报详情（仅允许举报人查看）
    """
    report = db.session.get(Report, report_id)
    if report and report.reporter_id == user_id:
        return report
    return None


def _validate_target(target_type, target_id):
    """
    校验举报目标是否存在
    """
    if target_type == 'PRODUCT':
        return db.session.get(Product, target_id)
    elif target_type == 'USER':
        return db.session.get(User, target_id)
    return None


def _is_self_report(reporter_id, target_type, target):
    """
    检查是否举报自己
    """
    if target_type == 'USER':
        return target.user_id == reporter_id
    elif target_type == 'PRODUCT':
        return target.seller_id == reporter_id
    return False


def _generate_snapshot(target_type, target):
    """
    生成目标快照
    """
    if target_type == 'PRODUCT':
        return {
            'product_name': target.product_name,
            'price': float(target.price) if target.price else None,
            'description': target.description,
            'seller_id': target.seller_id,
            'product_status': target.product_status
        }
    elif target_type == 'USER':
        return {
            'username': target.username,
            'nickname': target.nickname,
            'introduction': target.introduction,
            'role': target.role
        }
    return None


def is_target_owner(user_id, report):
    """
    检查用户是否是被举报的对象
    """
    if report.target_type == 'PRODUCT':
        product = db.session.get(Product, report.target_id)
        return product and product.seller_id == user_id
    elif report.target_type == 'USER':
        return report.target_id == user_id
    return False


def submit_appeal(report_id, user_id, appeal_content):
    """
    提交申诉
    """
    report = db.session.get(Report, report_id)
    if not report:
        return False, '举报不存在。'
    
    if not is_target_owner(user_id, report):
        return False, '您无权对此举报进行申诉。'
    
    if report.is_appealed:
        return False, '您已对此举报进行过申诉。'
    
    if report.report_status == 'PENDING':
        return False, '该举报尚未处理，无需申诉。'
    
    # 验证申诉内容长度
    appeal_content = appeal_content.strip()
    if len(appeal_content) < 10:
        return False, '申诉内容至少需要10个字符。'
    if len(appeal_content) > 1000:
        return False, '申诉内容不能超过1000个字符。'
    
    # 提交申诉
    report.is_appealed = True
    report.appeal_content = appeal_content
    report.appealed_at = datetime.utcnow()
    report.appeal_handled = False
    
    # 标记需要人工审核
    report.needs_human_review = True
    report.report_status = 'PENDING'
    
    db.session.commit()
    return True, '申诉提交成功，请等待管理员审核。'


def get_reports_against_user(user_id):
    """
    获取针对某个用户的举报列表（作为被举报人）
    """
    # 1. 获取针对该用户的举报
    user_reports = Report.query.filter_by(target_type='USER', target_id=user_id).all()
    
    # 2. 获取该用户商品的举报
    # 先获取用户的商品
    user_products = Product.query.filter_by(seller_id=user_id).all()
    user_product_ids = [p.product_id for p in user_products]
    
    # 然后获取这些商品的举报
    product_reports = []
    if user_product_ids:
        product_reports = Report.query.filter(
            Report.target_type == 'PRODUCT',
            Report.target_id.in_(user_product_ids)
        ).all()
    
    # 3. 合并结果
    all_reports = user_reports + product_reports
    
    # 4. 按创建时间排序（最新的在前）
    all_reports.sort(key=lambda x: x.created_at, reverse=True)
    
    return all_reports


def get_appealed_reports():
    """
    获取所有已申诉的举报（管理员）
    """
    return Report.query.filter_by(is_appealed=True, appeal_handled=False).order_by(
        Report.appealed_at.desc()).all()


def handle_appeal(report_id, handler_id, action, handle_result=None):
    """
    处理申诉
    """
    report = db.session.get(Report, report_id)
    if not report:
        return False, '举报不存在。'
    if not report.is_appealed:
        return False, '该举报尚未申诉。'
    if report.appeal_handled:
        return False, '该申诉已处理。'
    
    report.appeal_handled = True
    
    if action == 'UPHELD':
        # 维持原决定
        report.handle_result = f'申诉处理结果：维持原决定。{handle_result or ""}'
    elif action == 'REVERSED':
        # 推翻原决定
        report.report_status = 'DISMISSED'
        report.handle_result = f'申诉处理结果：推翻原决定。{handle_result or ""}'
        
        # 如果之前下架了商品或封禁了用户，恢复它们
        if report.target_type == 'PRODUCT':
            product = db.session.get(Product, report.target_id)
            if product and product.product_status == 'OFF_SHELF':
                product.product_status = 'ON_SALE'
        elif report.target_type == 'USER':
            user = db.session.get(User, report.target_id)
            if user and user.status == 'DISABLED':
                user.status = 'ACTIVE'
                # 恢复用户商品
                Product.active().filter_by(seller_id=user.user_id, product_status='OFF_SHELF').update(
                    {'product_status': 'ON_SALE'}, synchronize_session='fetch')
    
    report.handler_id = handler_id
    report.handled_at = datetime.utcnow()
    
    db.session.commit()
    return True, '申诉已处理。'

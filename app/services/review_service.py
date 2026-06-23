from app.extensions import db
from app.models.review import Review
from app.models.orders import Order
import re
from html import escape


def _filter_content(content):
    """
    过滤评价内容，防止XSS攻击
    移除危险标签并转义HTML
    """
    if not content:
        return None
    
    # 移除script标签
    content = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', content, flags=re.IGNORECASE)
    
    # 移除其他危险标签
    content = re.sub(r'<(iframe|object|embed|form|input|button|style|link)\b[^<]*(?:(?!<\/\1>)<[^<]*)*<\/\1>', '', content, flags=re.IGNORECASE)
    
    # 移除on*事件属性
    content = re.sub(r'\s+on\w+="[^"]*"', '', content, flags=re.IGNORECASE)
    content = re.sub(r"\s+on\w+='[^']*'", '', content, flags=re.IGNORECASE)
    
    # 转义HTML
    filtered = escape(content.strip())
    
    # 限制长度为500字
    return filtered[:500] if filtered else None


def submit_review(order_id, reviewer_id, score, content=None):
    order = db.session.get(Order, order_id)
    if not order or order.deleted:
        return False, '订单不存在。'
    if order.order_status != 'COMPLETED':
        return False, '只能评价已完成的订单。'
    if reviewer_id not in (order.buyer_id, order.seller_id):
        return False, '无权评价此订单。'

    reviewed_user_id = order.seller_id if reviewer_id == order.buyer_id else order.buyer_id

    existing = Review.active().filter_by(order_id=order_id, reviewer_id=reviewer_id).first()
    if existing:
        return False, '您已经评价过此订单。'
    if score < 1 or score > 5:
        return False, '评分必须在1~5之间。'

    # 过滤评价内容
    filtered_content = _filter_content(content)

    review = Review(
        order_id=order_id, reviewer_id=reviewer_id,
        reviewed_user_id=reviewed_user_id, score=score,
        review_content=filtered_content
    )
    db.session.add(review)
    db.session.commit()
    return True, '评价提交成功！'


def get_user_reviews(user_id):
    return Review.active().filter_by(reviewed_user_id=user_id).order_by(
        Review.created_at.desc()).all()


def has_reviewed(order_id, reviewer_id):
    return Review.active().filter_by(
        order_id=order_id, reviewer_id=reviewer_id).first() is not None


def get_order_reviews(order_id):
    """
    获取订单的所有评价
    
    Args:
        order_id: 订单编号
        
    Returns:
        list: 评价列表
    """
    return Review.active().filter_by(order_id=order_id).all()

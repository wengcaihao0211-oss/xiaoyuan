from app.extensions import db
from app.models.message import Message
from app.models.product import Product
from app.models.user import User
from datetime import datetime
import re
from html import escape


def _filter_content(content):
    """
    过滤消息内容，防止XSS攻击
    移除危险标签并转义HTML
    """
    if not content:
        return ''
    
    # 移除script标签
    content = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', content, flags=re.IGNORECASE)
    
    # 移除其他危险标签
    content = re.sub(r'<(iframe|object|embed|form|input|button|style|link)\b[^<]*(?:(?!<\/\1>)<[^<]*)*<\/\1>', '', content, flags=re.IGNORECASE)
    
    # 移除on*事件属性
    content = re.sub(r'\s+on\w+="[^"]*"', '', content, flags=re.IGNORECASE)
    content = re.sub(r"\s+on\w+='[^']*'", '', content, flags=re.IGNORECASE)
    
    # 转义HTML
    return escape(content.strip())


def send_message(sender_id, receiver_id, product_id, content):
    # 验证发送者和接收者不是同一人
    if sender_id == receiver_id:
        return False, '不能给自己发消息。', None
    
    # 验证消息内容
    if not content or not content.strip():
        return False, '消息内容不能为空。', None
    
    content_length = len(content.strip())
    if content_length < 1:
        return False, '消息内容不能为空。', None
    if content_length > 500:
        return False, '消息内容不能超过500字。', None
    
    # 验证发送者和接收者账号状态
    sender = db.session.get(User, sender_id)
    receiver = db.session.get(User, receiver_id)
    
    if not sender or sender.status != 'ACTIVE':
        return False, '您的账号状态异常。', None
    if not receiver or receiver.status != 'ACTIVE':
        return False, '对方账号状态异常。', None
    
    # 管理员会话允许不绑定商品，其余消息仍校验商品有效性
    if product_id is not None:
        product = db.session.get(Product, product_id)
        if not product or product.deleted:
            return False, '关联商品不存在。', None
    
    # 过滤消息内容
    filtered_content = _filter_content(content)
    
    msg = Message(
        sender_id=sender_id, receiver_id=receiver_id,
        product_id=product_id, message_content=filtered_content
    )
    db.session.add(msg)
    db.session.commit()
    return True, '消息发送成功。', msg


def get_conversations(user_id, page=1, per_page=20, keyword=None, unread_only=False):
    """
    Get conversation list with pagination, search and filter.
    
    Args:
        user_id: Current user ID
        page: Page number, default 1
        per_page: Items per page, default 20
        keyword: Search keyword for username or product name
        unread_only: Whether to show only unread conversations
        
    Returns:
        tuple: (conversation_list, total_unread, total_pages)
    """
    sent = db.session.query(
        Message.receiver_id.label('other_id'), Message.product_id,
        db.func.max(Message.created_at).label('last_time')
    ).filter(Message.sender_id == user_id, Message.deleted == False).group_by(
        Message.receiver_id, Message.product_id)

    received = db.session.query(
        Message.sender_id.label('other_id'), Message.product_id,
        db.func.max(Message.created_at).label('last_time')
    ).filter(Message.receiver_id == user_id, Message.deleted == False).group_by(
        Message.sender_id, Message.product_id)

    conversations = {}
    def add_conv(other_id, product_id, last_time):
        key = (other_id, product_id)
        if key not in conversations or last_time > conversations[key]['last_time']:
            conversations[key] = {'other_id': other_id, 'product_id': product_id, 'last_time': last_time}

    for row in sent.all():
        add_conv(row.other_id, row.product_id, row.last_time)
    for row in received.all():
        add_conv(row.other_id, row.product_id, row.last_time)

    result = []
    for (other_id, product_id), data in conversations.items():
        other_user = db.session.get(User, other_id)
        product = db.session.get(Product, product_id)
        if not other_user:
            continue

        last_msg = Message.active().filter(
            db.or_(
                db.and_(Message.sender_id == user_id, Message.receiver_id == other_id),
                db.and_(Message.sender_id == other_id, Message.receiver_id == user_id)
            ), Message.product_id == product_id
        ).order_by(Message.created_at.desc()).first()

        unread = Message.active().filter(
            Message.sender_id == other_id, Message.receiver_id == user_id,
            Message.product_id == product_id, Message.read_status == False
        ).count()

        # Apply keyword filter
        if keyword:
            keyword_lower = keyword.lower()
            match_found = False
            if other_user.username and keyword_lower in other_user.username.lower():
                match_found = True
            if product and product.product_name and keyword_lower in product.product_name.lower():
                match_found = True
            if not match_found:
                continue

        # Apply unread filter
        if unread_only and unread == 0:
            continue

        result.append({
            'other_user': other_user, 'product': product,
            'last_message': last_msg, 'last_time': data['last_time'],
            'unread_count': unread,
        })

    # Sort by last message time descending
    result.sort(key=lambda x: x['last_time'], reverse=True)
    
    # Pagination
    total = len(result)
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    start = (page - 1) * per_page
    end = start + per_page
    paginated_result = result[start:end]
    
    # Get total unread count
    total_unread = get_unread_count(user_id)
    
    return paginated_result, total_unread, total_pages


def get_chat_messages(user_id, other_user_id, product_id):
    return Message.active().filter(
        db.or_(
            db.and_(Message.sender_id == user_id, Message.receiver_id == other_user_id),
            db.and_(Message.sender_id == other_user_id, Message.receiver_id == user_id)
        ), Message.product_id == product_id
    ).order_by(Message.created_at.asc()).all()


def mark_messages_read(user_id, other_user_id, product_id):
    """
    批量标记会话中的消息为已读
    
    Args:
        user_id: 当前用户ID
        other_user_id: 对方用户ID
        product_id: 关联商品ID
        
    Returns:
        int: 被标记为已读的消息数量
    """
    # 查询需要更新的消息
    messages = Message.active().filter(
        Message.sender_id == other_user_id,
        Message.receiver_id == user_id,
        Message.product_id == product_id,
        Message.read_status == False
    ).all()
    
    # 如果没有未读消息，直接返回0
    if not messages:
        return 0
    
    # 批量更新
    current_time = datetime.utcnow()
    update_count = Message.active().filter(
        Message.sender_id == other_user_id,
        Message.receiver_id == user_id,
        Message.product_id == product_id,
        Message.read_status == False
    ).update({
        'read_status': True,
        'read_time': current_time
    }, synchronize_session='fetch')
    
    db.session.commit()
    return update_count


def mark_message_read_by_ids(user_id, message_ids):
    """
    根据消息ID列表标记为已读
    
    Args:
        user_id: 当前用户ID
        message_ids: 消息ID列表
        
    Returns:
        int: 被标记为已读的消息数量
    """
    if not message_ids:
        return 0
    
    # 验证消息属于当前用户
    current_time = datetime.utcnow()
    update_count = Message.active().filter(
        Message.message_id.in_(message_ids),
        Message.receiver_id == user_id,
        Message.read_status == False
    ).update({
        'read_status': True,
        'read_time': current_time
    }, synchronize_session='fetch')
    
    db.session.commit()
    return update_count


def get_unread_count(user_id):
    return Message.get_unread_count(user_id)

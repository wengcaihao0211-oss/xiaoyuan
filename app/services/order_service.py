from datetime import datetime
from app.extensions import db
from app.models.orders import Order
from app.models.product import Product
from app.services.notification_service import create_notification
from app.utils.helpers import generate_order_no, generate_transaction_no
import re


class OrderService:
    """订单服务类 - F24/F25/F26 订单管理"""

    # 合法的交易方式枚举
    VALID_TRADE_TYPES = ['ONLINE', 'OFFLINE']

    @classmethod
    def _normalize_buyer_message(cls, message):
        """
        F26 买家留言处理：
        - 去除首尾空格
        - 过滤脚本
        - 检查恶意内容
        """
        if not message:
            return None
            
        # 去除首尾空格
        message = message.strip()
        
        # 如果为空，返回None
        if not message:
            return None
            
        # 限制长度
        if len(message) > 200:
            return None
            
        # 过滤脚本标签和恶意内容
        # 移除script标签
        message = re.sub(r'<script[^>]*>.*?</script>', '', message, flags=re.IGNORECASE | re.DOTALL)
        # 移除其他可能的危险标签
        message = re.sub(r'<[^>]+>', '', message)
        # 过滤常见的恶意关键词
        malicious_patterns = [
            r'on\w+\s*=', r'javascript:', r'vbscript:', r'data:',
            r'alert\(', r'eval\(', r'exec\(', r'expression\(',
            r'--', r';', r'/\*', r'\*/'
        ]
        for pattern in malicious_patterns:
            message = re.sub(pattern, '', message, flags=re.IGNORECASE)
            
        return message.strip() if message.strip() else None

    @classmethod
    def _validate_trade_type(cls, trade_type):
        """
        F25 交易方式验证
        """
        if trade_type not in cls.VALID_TRADE_TYPES:
            return False, '非法的交易方式'
        return True, ''

    @classmethod
    def submit_order(cls, buyer_id, product_id, trade_type, buyer_message=None):
        """
        F24/F25/F26 提交购买订单 - 核心方法
        
        Args:
            buyer_id: 买家编号
            product_id: 商品编号
            trade_type: 交易方式 (ONLINE/OFFLINE)
            buyer_message: 买家留言
            
        Returns:
            tuple: (success, message, order)
        """
        try:
            # F25: 验证交易方式
            valid, msg = cls._validate_trade_type(trade_type)
            if not valid:
                return False, msg, None

            # 1) 读取商品当前价格并保存订单快照
            product = db.session.get(Product, product_id)
            
            # 2) 校验商品状态和买卖双方账号
            if not product or product.deleted:
                return False, '商品不存在或已下架。', None
                
            if product.seller_id == buyer_id:
                return False, '不能购买自己的商品。', None
                
            if product.product_status != 'ON_SALE':
                return False, '该商品当前不可购买。', None
            
            # 4) 同一买家对同一商品存在进行中订单时禁止重复下单
            existing = Order.active().filter(
                Order.product_id == product_id, Order.buyer_id == buyer_id,
                Order.order_status.in_(['PENDING', 'CONFIRMED', 'PAID'])
            ).first()
            
            if existing:
                return False, '您已有一个进行中的订单。', None

            # F26: 处理买家留言
            normalized_message = cls._normalize_buyer_message(buyer_message)
            
            # 3) 创建唯一订单号，初始状态为待卖家确认
            order = Order(
                order_no=generate_order_no(),
                product_id=product_id,
                buyer_id=buyer_id,
                seller_id=product.seller_id,
                order_amount=product.price,  # 保存当前价格作为订单快照
                trade_type=trade_type,  # F25: 保存明确交易类型
                buyer_message=normalized_message,  # F26: 保存处理后的留言
                order_status='PENDING',
                payment_status='UNPAID'
            )
            db.session.add(order)
            db.session.flush()
            
            # 向卖家生成待处理通知
            create_notification(
                receiver_id=product.seller_id, ntype='ORDER',
                title='新的购买订单',
                content=f'您的商品「{product.product_name}」收到新的购买订单。',
                related_id=order.order_id, sender_id=buyer_id
            )
            
            # 5) 整个过程使用事务
            db.session.commit()
            
            return True, '订单提交成功，等待卖家确认。', order
            
        except Exception as e:
            # 异常与边界处理：数据库冲突时回滚并提示
            db.session.rollback()
            return False, '订单创建失败，请稍后重试。', None

    @classmethod
    def seller_confirm_order(cls, order, seller_id):
        """
        卖家确认订单
        F25: 线上方式进入待支付；线下方式进入待线下交易
        """
        if order.seller_id != seller_id:
            return False, '无权操作此订单。'
        if order.order_status != 'PENDING':
            return False, '订单当前状态无法确认。'
        if not order.can_transition_to('CONFIRMED'):
            return False, '订单状态转换无效。'

        order.order_status = 'CONFIRMED'
        other_orders = Order.active().filter(
            Order.product_id == order.product_id, Order.order_id != order.order_id,
            Order.order_status == 'PENDING'
        ).all()
        for o in other_orders:
            o.order_status = 'CANCELLED'

        create_notification(
            receiver_id=order.buyer_id, ntype='ORDER',
            title='订单已确认', content=f'您的订单 {order.order_no} 已被卖家确认。',
            related_id=order.order_id, sender_id=seller_id
        )
        db.session.commit()
        return True, '订单已确认。'

    @classmethod
    def seller_reject_order(cls, order, seller_id, reason):
        if order.seller_id != seller_id:
            return False, '无权操作此订单。'
        if order.order_status != 'PENDING':
            return False, '订单当前状态无法拒绝。'
        if not reason or len(reason.strip()) < 2 or len(reason) > 100:
            return False, '拒绝原因需要2~100个字符。'
        order.order_status = 'REJECTED'
        order.reject_reason = reason.strip()

        create_notification(
            receiver_id=order.buyer_id, ntype='ORDER',
            title='订单已被拒绝',
            content=f'您的订单 {order.order_no} 已被卖家拒绝。原因：{reason}',
            related_id=order.order_id, sender_id=seller_id
        )
        db.session.commit()
        return True, '已拒绝该订单。'

    @classmethod
    def buyer_cancel_order(cls, order, buyer_id):
        """
        买家取消订单
        F25: 订单创建后原则上不可直接修改交易方式，需取消后重新下单
        """
        if order.buyer_id != buyer_id:
            return False, '无权操作此订单。'
        if order.order_status not in ('PENDING', 'CONFIRMED'):
            return False, '订单当前状态无法取消。'
        order.order_status = 'CANCELLED'

        create_notification(
            receiver_id=order.seller_id, ntype='ORDER',
            title='订单已取消', content=f'订单 {order.order_no} 已被买家取消。',
            related_id=order.order_id, sender_id=buyer_id
        )
        db.session.commit()
        return True, '订单已取消。'

    @classmethod
    def simulate_payment(cls, order, buyer_id):
        if order.buyer_id != buyer_id:
            return False, '无权操作此订单。'
        if order.payment_status == 'PAID':
            return True, '该订单已支付。'
        if order.order_status != 'CONFIRMED':
            return False, '订单状态不允许支付。'
        if order.trade_type != 'ONLINE':
            return False, '线下交易无需模拟支付。'

        transaction_no = generate_transaction_no()
        order.payment_status = 'PAID'
        order.paid_at = datetime.utcnow()
        order.order_status = 'PAID'

        create_notification(
            receiver_id=order.buyer_id, ntype='ORDER',
            title='支付成功', content=f'订单 {order.order_no} 支付成功。交易编号：{transaction_no}',
            related_id=order.order_id, sender_id=buyer_id
        )
        create_notification(
            receiver_id=order.seller_id, ntype='ORDER',
            title='买家已支付', content=f'订单 {order.order_no} 买家已完成支付。',
            related_id=order.order_id, sender_id=buyer_id
        )
        db.session.commit()
        return True, f'支付成功！交易编号：{transaction_no}'

    @classmethod
    def buyer_complete_order(cls, order, buyer_id):
        if order.buyer_id != buyer_id:
            return False, '无权操作此订单。'
        if order.order_status == 'COMPLETED':
            return True, '订单已完成。'
        if order.trade_type == 'ONLINE' and order.order_status != 'PAID':
            return False, '请先完成支付。'
        if order.trade_type == 'OFFLINE' and order.order_status != 'CONFIRMED':
            return False, '请等待卖家确认。'

        order.order_status = 'COMPLETED'
        order.completed_at = datetime.utcnow()

        product = db.session.get(Product, order.product_id)
        if product:
            product.product_status = 'SOLD'

        create_notification(
            receiver_id=order.seller_id, ntype='ORDER',
            title='交易完成', content=f'订单 {order.order_no} 买家已确认收货，交易完成。',
            related_id=order.order_id, sender_id=buyer_id
        )
        db.session.commit()
        return True, '交易完成！可以互相评价了。'

    @classmethod
    def get_available_actions(cls, order, user_id):
        """
        获取用户可用的操作
        F25: 不同交易方式对应正确的后续状态和可用操作
        """
        actions = []
        is_buyer = (order.buyer_id == user_id)
        is_seller = (order.seller_id == user_id)
        
        if is_buyer:
            if order.order_status in ('PENDING', 'CONFIRMED'):
                actions.append('cancel')
            if order.order_status == 'CONFIRMED' and order.trade_type == 'ONLINE':
                actions.append('pay')
            if (order.order_status == 'PAID' and order.trade_type == 'ONLINE') or \
               (order.order_status == 'CONFIRMED' and order.trade_type == 'OFFLINE'):
                actions.append('complete')
                
        if is_seller:
            if order.order_status == 'PENDING':
                actions.append('confirm')
                actions.append('reject')
                
        return actions

    @classmethod
    def get_buyer_orders(cls, user_id, status_filter=None, keyword=None):
        """
        F27 买家查看订单列表
        
        Args:
            user_id: 买家用户ID
            status_filter: 订单状态筛选
            keyword: 商品关键词搜索
            
        Returns:
            查询对象
        """
        # 仅查询 buyer_id 为当前用户的订单
        q = Order.active().filter_by(buyer_id=user_id)
        
        # 支持状态筛选
        if status_filter:
            q = q.filter_by(order_status=status_filter)
            
        # 支持关键词搜索
        if keyword:
            q = q.join(Product).filter(Product.product_name.contains(keyword))
            
        # 默认按创建时间倒序
        return q.order_by(Order.created_at.desc())

    @classmethod
    def get_seller_orders(cls, user_id, status_filter=None, keyword=None):
        """
        F28 卖家查看订单列表
        
        Args:
            user_id: 卖家用户ID
            status_filter: 订单状态筛选
            keyword: 商品关键词搜索
            
        Returns:
            查询对象
        """
        # 仅查询 seller_id 为当前用户的订单
        q = Order.active().filter_by(seller_id=user_id)
        
        # 支持状态筛选
        if status_filter:
            q = q.filter_by(order_status=status_filter)
            
        # 支持关键词搜索
        if keyword:
            q = q.join(Product).filter(Product.product_name.contains(keyword))
            
        # 优先展示待确认订单
        return q.order_by(
            db.case((Order.order_status == 'PENDING', 0), else_=1),
            Order.created_at.desc()
        )
    
    @classmethod
    def get_pending_count(cls, user_id):
        """
        F28 获取待确认订单数量
        """
        return Order.active().filter_by(
            seller_id=user_id,
            order_status='PENDING'
        ).count()


# 保持向后兼容的函数别名
def submit_order(buyer_id, product_id, trade_type, buyer_message=None):
    return OrderService.submit_order(buyer_id, product_id, trade_type, buyer_message)

def seller_confirm_order(order, seller_id):
    return OrderService.seller_confirm_order(order, seller_id)

def seller_reject_order(order, seller_id, reason):
    return OrderService.seller_reject_order(order, seller_id, reason)

def buyer_cancel_order(order, buyer_id):
    return OrderService.buyer_cancel_order(order, buyer_id)

def simulate_payment(order, buyer_id):
    return OrderService.simulate_payment(order, buyer_id)

def buyer_complete_order(order, buyer_id):
    return OrderService.buyer_complete_order(order, buyer_id)

def get_buyer_orders(user_id, status_filter=None, keyword=None):
    return OrderService.get_buyer_orders(user_id, status_filter, keyword)

def get_seller_orders(user_id, status_filter=None, keyword=None):
    return OrderService.get_seller_orders(user_id, status_filter, keyword)

def get_pending_count(user_id):
    return OrderService.get_pending_count(user_id)

def get_available_actions(order, user_id):
    return OrderService.get_available_actions(order, user_id)

# F34 买家向卖家发送咨询消息

## 完整业务信息

所属模块：消息、评价与举报
参与者：已登录普通用户（买家）
优先级：高
前置条件：买卖双方账号正常；商品存在；买家不是卖家。
触发条件：买家在商品详情点击 “联系卖家” 并发送消息。
输入数据：商品编号、消息内容 1～500 字。
处理流程与业务规则：为买卖双方和商品创建或复用会话；过滤空白和脚本；保存发送者、接收者、时间及未读状态；更新会话最后消息。
输出及后置条件：消息发送成功，卖家未读数增加。
异常与边界处理：消息为空 / 超长、账号禁用、商品删除或给自己发消息时拒绝。
验收标准：合法消息即时出现在双方会话；非法脚本不执行；未读数正确。

## 面向对象设计

基于前后端分层开发逻辑，本功能采用 MVC 架构，包含以下核心类：

### 模型层（Model）
- Message 模型：存储消息内容、发送者、接收者、时间等信息
- Conversation 模型：管理买卖双方的会话，包含商品关联、最后消息等
- ConversationParticipant 模型：管理会话参与者及未读消息数

### 业务逻辑层（Service）
- MessageService：处理消息发送、会话管理、消息过滤等核心逻辑
- ConversationService：处理会话的创建、查找、更新等操作

### 表现层（Controller）
- MessageController：处理 HTTP 请求，调用 Service 层，返回响应

### 视图层（View）
- 商品详情页：提供联系卖家入口
- 消息列表页：显示用户的会话列表
- 会话详情页：显示具体对话内容

## 伪代码实现

```python
# ==================== 数据模型层 ====================

class Conversation(db.Model):
    """会话模型"""
    conversation_id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('product.product_id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_message = Column(Text)
    last_message_at = Column(DateTime)
    
    # 关联
    product = relationship('Product')
    participants = relationship('ConversationParticipant', back_populates='conversation')
    messages = relationship('Message', back_populates='conversation', order_by='Message.created_at')


class ConversationParticipant(db.Model):
    """会话参与者模型"""
    conversation_id = Column(Integer, ForeignKey('conversation.conversation_id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('user.user_id'), primary_key=True)
    unread_count = Column(Integer, default=0)
    
    # 关联
    conversation = relationship('Conversation', back_populates='participants')
    user = relationship('User')


class Message(db.Model):
    """消息模型"""
    message_id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversation.conversation_id'))
    sender_id = Column(Integer, ForeignKey('user.user_id'))
    receiver_id = Column(Integer, ForeignKey('user.user_id'))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    
    # 关联
    conversation = relationship('Conversation', back_populates='messages')
    sender = relationship('User', foreign_keys=[sender_id])
    receiver = relationship('User', foreign_keys=[receiver_id])


# ==================== 业务逻辑层 ====================

class MessageService:
    """消息服务类"""
    
    @staticmethod
    def send_message(buyer_id, product_id, content):
        """
        买家向卖家发送咨询消息
        
        Args:
            buyer_id: 买家用户ID
            product_id: 商品ID
            content: 消息内容
            
        Returns:
            Message: 发送的消息对象
            
        Raises:
            ValueError: 参数验证失败时
        """
        # 验证输入
        MessageService._validate_input(content)
        
        # 获取商品信息
        product = ProductService.get_product_by_id(product_id)
        if not product or product.status == 'DELETED':
            raise ValueError("商品不存在或已删除")
        
        # 获取卖家信息
        seller_id = product.seller_id
        if buyer_id == seller_id:
            raise ValueError("不能给自己发送消息")
        
        # 验证双方账号状态
        buyer = UserService.get_user_by_id(buyer_id)
        seller = UserService.get_user_by_id(seller_id)
        
        if buyer.status != 'ACTIVE':
            raise ValueError("您的账号已被禁用")
        if seller.status != 'ACTIVE':
            raise ValueError("卖家账号已被禁用")
        
        # 过滤消息内容
        filtered_content = MessageService._filter_content(content)
        
        # 获取或创建会话
        conversation = ConversationService.get_or_create_conversation(
            buyer_id, seller_id, product_id
        )
        
        # 创建消息
        message = Message(
            conversation_id=conversation.conversation_id,
            sender_id=buyer_id,
            receiver_id=seller_id,
            content=filtered_content,
            is_read=False
        )
        db.session.add(message)
        
        # 更新会话最后消息
        conversation.last_message = filtered_content
        conversation.last_message_at = datetime.utcnow()
        conversation.updated_at = datetime.utcnow()
        
        # 更新买家参与者（未读数不变）
        buyer_participant = ConversationParticipant.query.filter_by(
            conversation_id=conversation.conversation_id,
            user_id=buyer_id
        ).first()
        if buyer_participant:
            db.session.add(buyer_participant)
        
        # 更新卖家参与者（未读数+1）
        seller_participant = ConversationParticipant.query.filter_by(
            conversation_id=conversation.conversation_id,
            user_id=seller_id
        ).first()
        if seller_participant:
            seller_participant.unread_count += 1
            db.session.add(seller_participant)
        
        db.session.commit()
        return message
    
    @staticmethod
    def _validate_input(content):
        """验证输入"""
        if not content or not content.strip():
            raise ValueError("消息内容不能为空")
        
        content_length = len(content.strip())
        if content_length < 1:
            raise ValueError("消息内容不能为空")
        if content_length > 500:
            raise ValueError("消息内容不能超过500字")
    
    @staticmethod
    def _filter_content(content):
        """过滤消息内容，防止XSS攻击"""
        # 移除脚本标签
        import re
        content = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', content, flags=re.IGNORECASE)
        # 移除其他危险标签
        content = re.sub(r'<(iframe|object|embed|form|input|button)\b[^<]*(?:(?!<\/\1>)<[^<]*)*<\/\1>', '', content, flags=re.IGNORECASE)
        # 转义HTML
        from html import escape
        return escape(content.strip())


class ConversationService:
    """会话服务类"""
    
    @staticmethod
    def get_or_create_conversation(buyer_id, seller_id, product_id):
        """
        获取或创建会话
        
        Args:
            buyer_id: 买家ID
            seller_id: 卖家ID
            product_id: 商品ID
            
        Returns:
            Conversation: 会话对象
        """
        # 查找是否已存在会话
        conversation = Conversation.query.join(
            ConversationParticipant
        ).filter(
            Conversation.product_id == product_id,
            ConversationParticipant.user_id.in_([buyer_id, seller_id])
        ).group_by(Conversation.conversation_id).having(
            db.func.count(db.distinct(ConversationParticipant.user_id)) == 2
        ).first()
        
        if conversation:
            return conversation
        
        # 创建新会话
        conversation = Conversation(
            product_id=product_id
        )
        db.session.add(conversation)
        db.session.flush()  # 获取conversation_id
        
        # 添加参与者
        buyer_participant = ConversationParticipant(
            conversation_id=conversation.conversation_id,
            user_id=buyer_id,
            unread_count=0
        )
        seller_participant = ConversationParticipant(
            conversation_id=conversation.conversation_id,
            user_id=seller_id,
            unread_count=0
        )
        db.session.add(buyer_participant)
        db.session.add(seller_participant)
        
        db.session.commit()
        return conversation


# ==================== 表现层（Controller） ====================

@message_bp.route('/send/<int:product_id>', methods=['POST'])
@login_required
def send_message(product_id):
    """发送消息接口"""
    content = request.form.get('content', '')
    
    try:
        message = MessageService.send_message(
            buyer_id=current_user.user_id,
            product_id=product_id,
            content=content
        )
        
        flash('消息发送成功', 'success')
        return redirect(url_for('message.conversation_detail', 
                              conversation_id=message.conversation_id))
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('product.detail', product_id=product_id))


@message_bp.route('/conversation/<int:conversation_id>')
@login_required
def conversation_detail(conversation_id):
    """会话详情页"""
    # 获取会话
    conversation = Conversation.query.get_or_404(conversation_id)
    
    # 验证用户是否为会话参与者
    participant = ConversationParticipant.query.filter_by(
        conversation_id=conversation_id,
        user_id=current_user.user_id
    ).first()
    if not participant:
        abort(403)
    
    # 获取消息列表
    messages = Message.query.filter_by(
        conversation_id=conversation_id
    ).order_by(Message.created_at).all()
    
    # 标记为已读
    participant.unread_count = 0
    for message in messages:
        if message.receiver_id == current_user.user_id and not message.is_read:
            message.is_read = True
    db.session.commit()
    
    return render_template('message/conversation.html',
                          conversation=conversation,
                          messages=messages,
                          participant=participant)


# ==================== 视图层（模板逻辑） ====================

# 商品详情页 - 联系卖家按钮
<!-- templates/product/detail.html -->
<div class="product-actions">
    {% if current_user.is_authenticated and current_user.user_id != product.seller_id %}
        <button onclick="openContactSeller({{ product.product_id }})" 
                class="btn btn-primary">
            💬 联系卖家
        </button>
    {% endif %}
</div>

<!-- 联系卖家模态框 -->
<div id="contactSellerModal" class="modal">
    <div class="modal-content">
        <h3>联系卖家</h3>
        <form method="POST" action="{{ url_for('message.send_message', product_id=product.product_id) }}">
            <textarea name="content" placeholder="请输入您的咨询内容..." 
                     maxlength="500" required></textarea>
            <div class="char-count">0/500</div>
            <div class="modal-actions">
                <button type="button" onclick="closeModal()">取消</button>
                <button type="submit" class="primary">发送</button>
            </div>
        </form>
    </div>
</div>

# 会话详情页
<!-- templates/message/conversation.html -->
<div class="conversation-header">
    <div class="product-info">
        <img src="{{ conversation.product.image_url }}" alt="商品图片">
        <div>
            <h4>{{ conversation.product.title }}</h4>
            <p class="price">¥{{ "%.2f"|format(conversation.product.price) }}</p>
        </div>
    </div>
</div>

<div class="messages-container">
    {% for message in messages %}
        <div class="message {% if message.sender_id == current_user.user_id %}sent{% else %}received{% endif %}">
            <div class="message-content">{{ message.content }}</div>
            <div class="message-time">{{ message.created_at.strftime('%H:%M') }}</div>
        </div>
    {% endfor %}
</div>

<div class="message-input">
    <form method="POST" action="{{ url_for('message.send_message', product_id=conversation.product_id) }}">
        <textarea name="content" placeholder="输入消息..." maxlength="500" required></textarea>
        <button type="submit">发送</button>
    </form>
</div>
```

## 程序流程图

此业务流程需要绘制程序流程图，包含以下主要节点：

1. 开始节点
2. 用户点击"联系卖家"
3. 验证用户登录状态
4. 验证商品是否存在
5. 验证是否给自己发消息
6. 验证双方账号状态
7. 验证消息内容
8. 过滤消息内容
9. 获取或创建会话
10. 保存消息
11. 更新会话最后消息
12. 更新未读数
13. 返回成功响应
14. 结束节点

同时包含各验证失败的异常处理分支。

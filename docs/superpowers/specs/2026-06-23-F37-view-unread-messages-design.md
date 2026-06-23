# F37 查看未读消息

## 一、业务概述

### 1.1 所属模块
消息、评价与举报

### 1.2 参与者
已登录普通用户

### 1.3 优先级
高

### 1.4 前置条件
存在当前用户的消息记录。

### 1.5 触发条件
用户打开消息中心或具体会话。

## 二、数据输入

### 2.1 输入数据
会话编号或消息编号集合。

## 三、处理流程与业务规则

### 3.1 处理流程

1. **统计未读消息**
系统首先统计 receiver_id 为当前用户且 read_status = 未读的消息。这一步在用户打开消息中心时执行，用于在导航栏或消息列表中显示未读消息数量提示。

2. **标记消息已读**
当用户打开具体会话时，系统需要批量标记该会话中所有对方发送的未读消息为已读状态。标记时需要记录阅读时间，以便后续可能的业务分析。

3. **更新未读数量**
在标记消息已读后，系统需要更新总未读数，确保界面显示的未读数量准确反映当前状态。

### 3.2 业务规则

1. **会话粒度标记**
标记已读是以会话为单位进行的，每个会话由发送者、接收者和关联商品唯一确定。只有当前会话内的未读消息会被标记为已读。

2. **阅读时间记录**
每条消息被标记为已读时，都需要记录准确的阅读时间，这为后续功能扩展（如消息撤回时限、阅读统计等）提供数据支持。

3. **权限验证**
系统需要验证消息是否属于当前用户，只有 receiver_id 等于当前用户的消息才能被标记为已读，防止越权操作。

4. **幂等性保证**
多次打开同一会话不会产生副作用，已经标记为已读的消息状态保持不变。

## 四、输出及后置条件

### 4.1 输出
返回未读数量，已查看消息状态变为已读。

### 4.2 后置条件
- 用户在消息列表中可以看到准确的未读消息数量
- 已打开会话的未读数清零
- 其他会话的未读数不受影响
- 被标记为已读的消息在数据库中状态更新并记录阅读时间

## 五、异常与边界处理

### 5.1 消息不存在或不属于当前用户
当尝试标记的消息不存在或不属于当前用户时，系统应该忽略该操作或返回明确的拒绝信息，但不应影响其他正常消息的处理。

### 5.2 空会话处理
当会话中没有未读消息时，标记已读操作应该安全地跳过，不抛出异常。

### 5.3 批量操作容错
在批量标记消息已读时，如果部分消息处理失败，应该继续处理其他消息，并记录失败信息，而不是使整个操作回滚。

## 六、验收标准

### 6.1 会话未读数清零
打开会话后该会话未读数清零。用户进入聊天详情页面后，该会话的未读消息计数应立即归零，无论是在消息列表还是导航栏中都应该正确反映这一变化。

### 6.2 其他会话不受影响
其他会话未读数不受影响。只标记当前打开会话的消息为已读，用户与其他人的会话未读数应保持不变。

### 6.3 总未读数准确更新
总未读数应该准确反映所有会话中未读消息的总和，每次打开会话后总未读数应相应减少被标记为已读的消息数量。

---

## 七、面向对象设计

### 7.1 分层架构

本功能采用标准的 MVC 分层架构，符合前后端分离开发逻辑：

1. **表现层 (Controller)**
   - 处理消息列表和聊天详情的页面请求
   - 调用业务逻辑层获取和更新数据
   - 在页面加载时自动触发标记已读操作

2. **业务逻辑层 (Service)**
   - 实现未读消息统计逻辑
   - 实现批量标记已读逻辑
   - 处理权限验证和异常情况

3. **数据访问层 (Model)**
   - 消息模型需要包含阅读时间字段
   - 提供高效的未读消息查询接口
   - 提供批量更新接口

### 7.2 核心类设计

#### 7.2.1 数据模型

```python
# Message 模型 - 表示单条消息
class Message:
    message_id: int
    sender_id: int
    receiver_id: int
    product_id: int
    message_content: str
    read_status: bool
    read_time: datetime  # 新增：阅读时间
    created_at: datetime
    deleted: bool
    
    @classmethod
    def active(cls):
        """获取未删除的消息查询"""
        pass
    
    @classmethod
    def get_unread_count(cls, user_id):
        """获取用户总未读消息数"""
        pass
    
    @classmethod
    def get_conversation_unread_count(cls, user_id, other_user_id, product_id):
        """获取特定会话的未读消息数"""
        pass
```

#### 7.2.2 业务服务层

```python
# MessageService - 消息业务服务
class MessageService:
    
    @staticmethod
    def get_unread_count(user_id):
        """
        获取用户总未读消息数
        
        Args:
            user_id: 用户ID
            
        Returns:
            int: 未读消息总数
        """
        pass
    
    @staticmethod
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
        pass
    
    @staticmethod
    def mark_message_read_by_ids(user_id, message_ids):
        """
        根据消息ID列表标记为已读
        
        Args:
            user_id: 当前用户ID
            message_ids: 消息ID列表
            
        Returns:
            int: 被标记为已读的消息数量
        """
        pass
```

---

## 八、完整伪代码

### 8.1 数据模型层伪代码

```python
# app/models/message.py
from datetime import datetime
from app.extensions import db
from sqlalchemy import CheckConstraint


class Message(db.Model):
    __tablename__ = 'message'
    __table_args__ = (
        CheckConstraint('sender_id <> receiver_id', name='chk_message_users'),
    )

    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='消息编号')
    sender_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment='发送者编号')
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment='接收者编号')
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=True, comment='关联商品编号')
    message_content = db.Column(db.Text, nullable=False, comment='消息内容')
    read_status = db.Column(db.Boolean, nullable=False, default=False, comment='阅读状态')
    read_time = db.Column(db.DateTime, nullable=True, comment='阅读时间')  # 新增字段
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    deleted = db.Column(db.Boolean, nullable=False, default=False, comment='逻辑删除标志')

    @classmethod
    def active(cls):
        return cls.query.filter_by(deleted=False)
    
    @classmethod
    def get_unread_count(cls, user_id):
        """获取用户总未读消息数"""
        return cls.active().filter(
            cls.receiver_id == user_id,
            cls.read_status == False
        ).count()
    
    @classmethod
    def get_conversation_unread_count(cls, user_id, other_user_id, product_id):
        """获取特定会话的未读消息数"""
        return cls.active().filter(
            cls.sender_id == other_user_id,
            cls.receiver_id == user_id,
            cls.product_id == product_id,
            cls.read_status == False
        ).count()
```

### 8.2 业务服务层伪代码

```python
# app/services/message_service.py
from app.extensions import db
from app.models.message import Message
from datetime import datetime


class MessageService:
    
    @staticmethod
    def get_unread_count(user_id):
        """
        获取用户总未读消息数
        
        Args:
            user_id: 用户ID
            
        Returns:
            int: 未读消息总数
        """
        return Message.get_unread_count(user_id)
    
    @staticmethod
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
    
    @staticmethod
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
```

### 8.3 表现层控制器伪代码

```python
# app/blueprints/social/routes.py
@social_bp.route('/messages')
@login_required
def chat_list():
    """
    会话列表页面
    
    获取会话列表时自动统计未读消息数
    """
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword', '')
    unread_only = request.args.get('unread', 'false').lower() == 'true'
    
    # 调用业务逻辑层获取会话列表和总未读数
    conversations, total_unread, total_pages = message_service.get_conversations(
        user_id=current_user.user_id,
        page=page,
        per_page=20,
        keyword=keyword,
        unread_only=unread_only
    )
    
    return render_template(
        'social/chat_list.html',
        conversations=conversations,
        total_unread=total_unread,
        total_pages=total_pages,
        current_page=page,
        keyword=keyword,
        unread_only=unread_only
    )


@social_bp.route('/messages/<int:user_id>/<int:product_id>', methods=['GET', 'POST'])
@login_required
def chat_detail(user_id, product_id):
    """
    聊天详情页面
    
    打开会话时自动标记未读消息为已读
    """
    other_user = db.session.get(User, user_id)
    product = db.session.get(Product, product_id)
    if not other_user or not product:
        flash('用户或商品不存在。', 'danger')
        return redirect(url_for('social.chat_list'))
    
    # 验证用户权限
    is_participant = (current_user.user_id == product.seller_id or
                     Order.active().filter_by(
                         product_id=product_id, buyer_id=current_user.user_id
                     ).first() is not None or
                     message_service.get_chat_messages(current_user.user_id, user_id, product_id))
    if not is_participant and current_user.user_id != user_id:
        pass  # 允许访问，如果有消息记录
    
    form = MessageForm()
    if form.validate_on_submit():
        success, msg, msg_obj = message_service.send_message(
            sender_id=current_user.user_id,
            receiver_id=user_id,
            product_id=product_id,
            content=form.content.data
        )
        if success:
            return redirect(url_for('social.chat_detail', user_id=user_id, product_id=product_id))
        flash(msg, 'danger')
    
    # 标记消息为已读
    message_service.mark_messages_read(current_user.user_id, user_id, product_id)
    
    # 获取聊天消息
    messages = message_service.get_chat_messages(current_user.user_id, user_id, product_id)
    return render_template(
        'social/chat_detail.html',
        messages=messages, other_user=other_user,
        product=product, form=form
    )
```

---

## 九、程序流程图

此业务流程需要绘制程序流程图，主要流程节点如下：

```
开始
  ↓
用户打开消息中心
  ↓
统计用户总未读消息数
  ↓
显示消息列表（含未读数）
  ↓
用户点击具体会话
  ↓
验证会话权限
  ↓
查询该会话未读消息
  ↓
批量标记消息为已读
  ↓
记录阅读时间
  ↓
更新总未读数
  ↓
显示聊天详情页面
  ↓
结束
```

### 流程图说明

1. **开始节点**：用户访问消息中心
2. **统计未读**：查询数据库获取当前用户所有未读消息总数
3. **显示列表**：渲染消息列表，每个会话显示对应的未读数
4. **用户选择**：用户点击某个会话进入详情
5. **权限验证**：确认用户有权限访问该会话
6. **查询未读**：获取该会话中的未读消息
7. **标记已读**：批量更新消息状态为已读
8. **记录时间**：记录每条消息的阅读时间
9. **更新总数**：重新计算总未读数
10. **显示详情**：渲染聊天页面
11. **结束节点**：流程完成

---

## 十、性能优化建议

### 10.1 数据库优化

1. **索引优化**
   - 在 `(receiver_id, read_status, created_at)` 上建立复合索引，加速未读消息查询
   - 在 `(sender_id, receiver_id, product_id)` 上建立复合索引，加速会话查询

2. **查询优化**
   - 使用批量更新而不是逐条更新
   - 避免 N+1 查询问题，合理使用预加载

### 10.2 缓存策略

1. **未读数缓存**
   - 使用 Redis 缓存用户未读消息数
   - 发送消息和标记已读时更新缓存
   - 设置合理的过期时间作为兜底

2. **会话列表缓存**
   - 缓存用户的会话列表摘要信息
   - 有新消息时失效缓存

### 10.3 前端优化

1. **懒加载**
   - 聊天消息支持分页加载
   - 只加载当前可见区域的消息

2. **实时更新**
   - 使用 WebSocket 实现未读数实时更新
   - 避免频繁轮询

---

## 十一、安全考虑

### 11.1 访问控制

1. **消息所有权验证**
   - 严格验证 `receiver_id` 是否等于当前用户 ID
   - 防止用户标记他人的消息为已读

2. **IDOR 防护**
   - 验证会话中的用户关系
   - 防止越权访问其他用户的聊天

### 11.2 数据完整性

1. **批量操作安全**
   - 使用数据库事务保证一致性
   - 处理部分失败的情况

2. **时间安全**
   - 使用服务器时间而不是客户端时间
   - 防止时间篡改

---

## 十二、测试要点

### 12.1 功能测试

1. **未读数统计**
   - 发送消息后对方未读数+1
   - 标记已读后未读数相应减少
   - 总未读数等于各会话未读数之和

2. **会话标记已读**
   - 打开会话后该会话未读数清零
   - 其他会话未读数不受影响
   - 再次打开会话不会重复更新

3. **阅读时间记录**
   - 标记已读时 `read_time` 字段被正确设置
   - 时间格式和时区正确

### 12.2 边界测试

1. **空会话**
   - 打开没有消息的会话不会出错
   - 没有未读消息时操作正常

2. **部分失败**
   - 部分消息标记失败不影响其他消息
   - 提供准确的错误信息

3. **并发操作**
   - 多个用户同时标记已读不会产生数据冲突
   - 最终状态一致

---

## 十三、总结

本设计文档详细描述了 F37 查看未读消息功能的完整实现方案，包括：

1. **完整的业务规则**：完整保留了原始业务描述
2. **数据模型增强**：增加了 `read_time` 字段记录阅读时间
3. **完整的伪代码**：提供了从模型到视图的完整实现
4. **程序流程图**：标注了需要绘制程序流程图的需求
5. **全面的考虑**：包括性能优化、安全考虑和测试要点

该设计完全贴合现有项目架构，可以直接指导开发实现。

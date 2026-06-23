# F35 查看聊天消息列表

## 一、业务概述

### 1.1 所属模块
消息、评价与举报

### 1.2 参与者
已登录普通用户

### 1.3 优先级
高

### 1.4 前置条件
用户会话有效。

### 1.5 触发条件
用户进入消息中心。

## 二、数据输入

### 2.1 输入数据
- 页码
- 关键词
- 可选未读筛选

## 三、处理流程与业务规则

### 3.1 处理流程

1. **会话权限验证**
   - 系统首先验证用户会话的有效性，确保用户处于登录状态
   - 只有当前登录用户才能访问自己的消息列表

2. **会话查询与筛选**
   - 查询当前用户参与的所有会话
   - 按最后消息时间倒序排列，最新消息的会话显示在最前面
   - 支持按未读消息筛选，只显示有未读消息的会话
   - 支持关键词搜索，可以根据对方昵称或商品摘要进行筛选

3. **会话数据组装**
   - 对于每个会话，获取对方用户的昵称信息
   - 获取关联商品的摘要信息
   - 获取该会话的最后一条消息内容
   - 计算该会话的未读消息数量

4. **分页处理**
   - 每页显示20条会话记录
   - 提供分页导航，用户可以在多页之间切换

5. **返回结果**
   - 返回组装好的会话列表
   - 返回所有会话的总未读数，用于在导航栏等位置显示未读消息提示

### 3.2 业务规则

1. **用户权限规则**
   - 用户只能查看自己参与的会话
   - 不能查看其他用户的消息列表

2. **排序规则**
   - 会话列表严格按照最后消息时间倒序排列
   - 有新消息的会话自动置顶

3. **展示规则**
   - 展示对方昵称：显示聊天对象的用户名
   - 展示商品摘要：显示该会话关联的商品名称
   - 展示最后消息：显示该会话中的最后一条消息内容（前50字符）
   - 展示未读数：如果有未读消息，显示未读消息数量

4. **商品展示规则**
   - 即使商品被删除，仍显示商品快照信息
   - 商品删除状态在展示时不影响会话记录的完整性

5. **未读计数规则**
   - 未读消息数为对方发送且当前用户未读的消息总数
   - 进入会话详情后，该会话的未读消息自动标记为已读

## 四、输出及后置条件

### 4.1 输出
返回会话列表及总未读数。

### 4.2 后置条件
- 用户可以在页面上查看自己参与的所有会话
- 总未读数显示在导航栏等合适位置，提示用户有新消息
- 点击会话可以进入聊天详情页面

## 五、异常与边界处理

### 5.1 无会话时
- 当用户没有任何会话时，展示友好的空状态页面
- 显示提示信息和引导操作，如"暂无消息"
- 提供返回首页或其他页面的导航选项

### 5.2 被删除商品
- 即使关联的商品已被删除，仍显示商品快照
- 商品快照保留商品基本信息，确保会话记录的完整性

### 5.3 分页边界
- 当页码超出范围时，自动显示第一页或最后一页
- 提供清晰的分页导航，显示当前页和总页数

### 5.4 搜索结果为空
- 当关键词搜索无结果时，显示明确提示
- 提供清除搜索条件的选项

## 六、验收标准

### 6.1 用户权限验证
用户不能看到未参与会话，所有展示的会话必须是用户作为发送者或接收者参与的。

### 6.2 排序准确性
会话列表排序必须准确，最新消息的会话必须排在最前面。

### 6.3 未读数准确性
未读消息数量必须准确，只计数对方发送且当前用户未读的消息。

### 6.4 商品展示完整性
即使商品被删除，仍必须显示商品快照，不能出现会话信息缺失。

### 6.5 分页功能
分页功能必须正常工作，每页准确显示20条记录，超出范围时有合适处理。

---

## 七、面向对象设计

### 7.1 分层架构

本功能采用标准的 MVC 分层架构，符合前后端分离开发逻辑：

1. **表现层 (Controller)**
   - 处理 HTTP 请求
   - 参数验证
   - 调用业务逻辑层
   - 返回响应

2. **业务逻辑层 (Service)**
   - 实现核心业务规则
   - 数据组装与处理
   - 业务流程编排

3. **数据访问层 (Model)**
   - 数据库查询
   - 数据持久化
   - 关系映射

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
    created_at: datetime
    deleted: bool
    
    @classmethod
    def active(cls):
        """获取未删除的消息查询"""
        pass
    
    @classmethod
    def get_conversations(cls, user_id):
        """获取用户的会话列表"""
        pass
    
    @classmethod
    def get_unread_count(cls, user_id):
        """获取用户总未读数"""
        pass
```

#### 7.2.2 业务服务层

```python
# MessageService - 消息业务服务
class MessageService:
    
    @staticmethod
    def get_conversations(user_id, page=1, per_page=20, keyword=None, unread_only=False):
        """
        获取用户的会话列表
        
        Args:
            user_id: 当前用户ID
            page: 页码
            per_page: 每页数量
            keyword: 搜索关键词
            unread_only: 是否只显示未读会话
            
        Returns:
            分页的会话列表和总未读数
        """
        pass
    
    @staticmethod
    def get_unread_count(user_id):
        """获取用户总未读消息数"""
        pass
    
    @staticmethod
    def mark_messages_read(user_id, other_user_id, product_id):
        """标记会话消息为已读"""
        pass
```

#### 7.2.3 表现层控制器

```python
# ChatController - 聊天控制器
class ChatController:
    
    @staticmethod
    @login_required
    def chat_list():
        """
        会话列表页面
        
        接收参数:
            page: 页码，默认1
            keyword: 搜索关键词，可选
            unread: 是否只显示未读，可选
            
        返回:
            渲染的会话列表页面
        """
        pass
```

---

## 八、完整伪代码

### 8.1 数据模型层伪代码

```python
# models/message.py
from app.extensions import db
from datetime import datetime

class Message(db.Model):
    __tablename__ = 'message'
    
    message_id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False)
    message_content = db.Column(db.Text, nullable=False)
    read_status = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    deleted = db.Column(db.Boolean, default=False, nullable=False)
    
    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])
    product = db.relationship('Product')
    
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
```

### 8.2 业务服务层伪代码

```python
# services/message_service.py
from app.extensions import db
from app.models.message import Message
from app.models.user import User
from app.models.product import Product

class MessageService:
    
    @staticmethod
    def get_conversations(user_id, page=1, per_page=20, keyword=None, unread_only=False):
        """
        获取用户的会话列表
        
        Args:
            user_id: 当前用户ID
            page: 页码
            per_page: 每页数量
            keyword: 搜索关键词
            unread_only: 是否只显示未读会话
            
        Returns:
            tuple: (conversation_list, total_unread, total_pages)
        """
        # 1. 获取所有会话的基础信息
        sent_messages = db.session.query(
            Message.receiver_id.label('other_id'),
            Message.product_id,
            db.func.max(Message.created_at).label('last_time')
        ).filter(
            Message.sender_id == user_id,
            Message.deleted == False
        ).group_by(Message.receiver_id, Message.product_id)
        
        received_messages = db.session.query(
            Message.sender_id.label('other_id'),
            Message.product_id,
            db.func.max(Message.created_at).label('last_time')
        ).filter(
            Message.receiver_id == user_id,
            Message.deleted == False
        ).group_by(Message.sender_id, Message.product_id)
        
        # 2. 合并会话，去重
        conversations_dict = {}
        
        def add_conversation(other_id, product_id, last_time):
            key = (other_id, product_id)
            if key not in conversations_dict or last_time > conversations_dict[key]['last_time']:
                conversations_dict[key] = {
                    'other_id': other_id,
                    'product_id': product_id,
                    'last_time': last_time
                }
        
        for row in sent_messages.all():
            add_conversation(row.other_id, row.product_id, row.last_time)
        
        for row in received_messages.all():
            add_conversation(row.other_id, row.product_id, row.last_time)
        
        # 3. 组装完整会话数据
        result = []
        for (other_id, product_id), data in conversations_dict.items():
            other_user = db.session.get(User, other_id)
            product = db.session.get(Product, product_id)
            
            if not other_user:
                continue
            
            # 获取最后一条消息
            last_message = Message.active().filter(
                db.or_(
                    db.and_(Message.sender_id == user_id, Message.receiver_id == other_id),
                    db.and_(Message.sender_id == other_id, Message.receiver_id == user_id)
                ),
                Message.product_id == product_id
            ).order_by(Message.created_at.desc()).first()
            
            # 获取未读数
            unread_count = Message.active().filter(
                Message.sender_id == other_id,
                Message.receiver_id == user_id,
                Message.product_id == product_id,
                Message.read_status == False
            ).count()
            
            # 关键词筛选
            if keyword:
                keyword_lower = keyword.lower()
                match_keyword = False
                if other_user.username and keyword_lower in other_user.username.lower():
                    match_keyword = True
                if product and product.product_name and keyword_lower in product.product_name.lower():
                    match_keyword = True
                if not match_keyword:
                    continue
            
            # 未读筛选
            if unread_only and unread_count == 0:
                continue
            
            result.append({
                'other_user': other_user,
                'product': product,
                'last_message': last_message,
                'last_time': data['last_time'],
                'unread_count': unread_count
            })
        
        # 4. 按最后消息时间倒序排序
        result.sort(key=lambda x: x['last_time'], reverse=True)
        
        # 5. 分页处理
        total = len(result)
        total_pages = (total + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = start + per_page
        paginated_result = result[start:end]
        
        # 6. 获取总未读数
        total_unread = Message.get_unread_count(user_id)
        
        return paginated_result, total_unread, total_pages
    
    @staticmethod
    def get_unread_count(user_id):
        """获取用户总未读消息数"""
        return Message.get_unread_count(user_id)
    
    @staticmethod
    def mark_messages_read(user_id, other_user_id, product_id):
        """标记会话消息为已读"""
        Message.active().filter(
            Message.sender_id == other_user_id,
            Message.receiver_id == user_id,
            Message.product_id == product_id,
            Message.read_status == False
        ).update({'read_status': True}, synchronize_session='fetch')
        db.session.commit()
```

### 8.3 表现层控制器伪代码

```python
# blueprints/social/routes.py
from flask import render_template, request
from flask_login import login_required, current_user
from app.blueprints.social import social_bp
from app.services.message_service import MessageService

@social_bp.route('/messages')
@login_required
def chat_list():
    """
    会话列表页面
    
    接收参数:
        page: 页码，默认1
        keyword: 搜索关键词，可选
        unread: 是否只显示未读，可选
        
    返回:
        渲染的会话列表页面
    """
    # 1. 获取请求参数
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword', '')
    unread_only = request.args.get('unread', 'false').lower() == 'true'
    
    # 2. 调用业务逻辑层获取会话列表
    conversations, total_unread, total_pages = MessageService.get_conversations(
        user_id=current_user.user_id,
        page=page,
        per_page=20,
        keyword=keyword,
        unread_only=unread_only
    )
    
    # 3. 渲染模板返回
    return render_template(
        'social/chat_list.html',
        conversations=conversations,
        total_unread=total_unread,
        total_pages=total_pages,
        current_page=page,
        keyword=keyword,
        unread_only=unread_only
    )
```

### 8.4 视图层模板伪代码

```html
<!-- templates/social/chat_list.html -->
{% extends "base.html" %}

{% block title %}消息中心{% endblock %}

{% block content %}
<div class="container py-4">
    <!-- 页面标题 -->
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h4><i class="bi bi-chat-dots"></i> 消息中心</h4>
        {% if total_unread > 0 %}
        <span class="badge bg-danger">{{ total_unread }} 条未读</span>
        {% endif %}
    </div>
    
    <!-- 搜索和筛选栏 -->
    <div class="card mb-4">
        <div class="card-body">
            <form method="GET" class="row g-3">
                <div class="col-md-8">
                    <div class="input-group">
                        <input type="text" 
                               name="keyword" 
                               class="form-control" 
                               placeholder="搜索用户名或商品..."
                               value="{{ keyword }}">
                        <button class="btn btn-primary" type="submit">
                            <i class="bi bi-search"></i> 搜索
                        </button>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-check">
                        <input class="form-check-input" 
                               type="checkbox" 
                               name="unread" 
                               id="unreadOnly"
                               {% if unread_only %}checked{% endif %}
                               onchange="this.form.submit()">
                        <label class="form-check-label" for="unreadOnly">
                            只显示未读
                        </label>
                    </div>
                </div>
            </form>
        </div>
    </div>
    
    <!-- 会话列表 -->
    {% if conversations %}
    <div class="list-group">
        {% for conv in conversations %}
        <a href="{{ url_for('social.chat_detail', 
                           user_id=conv.other_user.user_id, 
                           product_id=conv.product.product_id) }}" 
           class="list-group-item list-group-item-action">
            <div class="d-flex align-items-center">
                <!-- 对方头像 -->
                <div class="me-3">
                    {% if conv.other_user.avatar %}
                    <img src="{{ url_for('static', filename=conv.other_user.avatar) }}" 
                         class="rounded-circle" 
                         width="56" 
                         height="56" 
                         style="object-fit: cover">
                    {% else %}
                    <i class="bi bi-person-circle text-muted" style="font-size: 56px"></i>
                    {% endif %}
                </div>
                
                <!-- 会话信息 -->
                <div class="flex-grow-1">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <strong>{{ conv.other_user.username }}</strong>
                        <small class="text-muted">
                            {{ conv.last_time.strftime('%Y-%m-%d %H:%M') if conv.last_time else '' }}
                        </small>
                    </div>
                    
                    {% if conv.product %}
                    <small class="text-muted d-block mb-1">
                        <i class="bi bi-box"></i> 关于：{{ conv.product.product_name }}
                    </small>
                    {% endif %}
                    
                    {% if conv.last_message %}
                    <p class="mb-0 small text-truncate text-secondary">
                        {{ conv.last_message.message_content[:60] }}{% if conv.last_message.message_content|length > 60 %}...{% endif %}
                    </p>
                    {% endif %}
                </div>
                
                <!-- 未读消息提示 -->
                {% if conv.unread_count > 0 %}
                <span class="badge bg-danger ms-2">{{ conv.unread_count }}</span>
                {% endif %}
            </div>
        </a>
        {% endfor %}
    </div>
    
    <!-- 分页导航 -->
    {% if total_pages > 1 %}
    <nav class="mt-4">
        <ul class="pagination justify-content-center">
            {% if current_page > 1 %}
            <li class="page-item">
                <a class="page-link" 
                   href="{{ url_for('social.chat_list', 
                                  page=current_page-1, 
                                  keyword=keyword,
                                  unread='true' if unread_only else 'false') }}">
                    上一页
                </a>
            </li>
            {% endif %}
            
            {% for p in range(1, total_pages + 1) %}
            <li class="page-item {% if p == current_page %}active{% endif %}">
                <a class="page-link" 
                   href="{{ url_for('social.chat_list', 
                                  page=p, 
                                  keyword=keyword,
                                  unread='true' if unread_only else 'false') }}">
                    {{ p }}
                </a>
            </li>
            {% endfor %}
            
            {% if current_page < total_pages %}
            <li class="page-item">
                <a class="page-link" 
                   href="{{ url_for('social.chat_list', 
                                  page=current_page+1, 
                                  keyword=keyword,
                                  unread='true' if unread_only else 'false') }}">
                    下一页
                </a>
            </li>
            {% endif %}
        </ul>
    </nav>
    {% endif %}
    
    {% else %}
    <!-- 空状态 -->
    <div class="text-center py-5">
        <div class="mb-4">
            <i class="bi bi-chat-dots text-muted" style="font-size: 4rem"></i>
        </div>
        <h5 class="text-muted mb-2">暂无消息</h5>
        <p class="text-muted mb-4">
            {% if keyword or unread_only %}
            没有找到匹配的会话，试试清除筛选条件
            {% else %}
            去逛逛，找到感兴趣的商品开始聊天吧！
            {% endif %}
        </p>
        
        {% if keyword or unread_only %}
        <a href="{{ url_for('social.chat_list') }}" class="btn btn-primary">
            <i class="bi bi-x-circle"></i> 清除筛选
        </a>
        {% else %}
        <a href="{{ url_for('browse.home') }}" class="btn btn-primary">
            <i class="bi bi-house"></i> 去首页逛逛
        </a>
        {% endif %}
    </div>
    {% endif %}
</div>
{% endblock %}
```

---

## 九、程序流程图

此业务流程需要绘制程序流程图，主要流程节点如下：

```
开始
  ↓
用户点击消息中心
  ↓
验证用户登录状态 ──→ 未登录 → 跳转登录页
  ↓
获取请求参数（页码、关键词、未读筛选）
  ↓
查询用户参与的所有会话
  ↓
应用关键词筛选（如需要）
  ↓
应用未读筛选（如需要）
  ↓
按最后消息时间倒序排列
  ↓
组装会话数据（对方昵称、商品摘要、最后消息、未读数）
  ↓
分页处理（每页20条）
  ↓
计算总未读数
  ↓
渲染会话列表页面
  ↓
    ↘ 有会话 → 展示会话列表 + 分页导航
    ↘ 无会话 → 展示空状态页面
  ↓
结束
```

### 流程图说明

1. **开始节点**：用户点击导航栏的消息入口
2. **权限验证**：确保用户已登录
3. **参数获取**：获取分页、搜索、筛选参数
4. **数据查询**：查询用户的所有会话
5. **数据筛选**：根据条件过滤会话
6. **排序**：按最后消息时间排序
7. **数据组装**：完善每个会话的信息
8. **分页**：处理分页逻辑
9. **渲染**：根据数据展示列表或空状态
10. **结束**：页面展示完成

---

## 十、性能优化建议

### 10.1 数据库优化

1. **索引优化**
   - 在 Message 表的 sender_id, receiver_id, product_id, created_at 上建立复合索引
   - 优化会话查询性能

2. **查询优化**
   - 避免 N+1 查询问题，使用批量预加载
   - 对商品和用户信息进行缓存

### 10.2 缓存策略

1. **会话列表缓存**
   - 对会话列表进行短时间缓存
   - 有新消息时自动失效缓存

2. **总未读数缓存**
   - 缓存总未读数，减少数据库查询
   - 消息状态变化时更新缓存

### 10.3 前端优化

1. **无限滚动**
   - 考虑实现无限滚动替代传统分页
   - 提升用户体验

2. **未读消息实时更新**
   - 使用 WebSocket 实现未读数实时更新
   - 提供更好的用户体验

---

## 十一、安全考虑

### 11.1 访问控制

1. **会话权限验证**
   - 严格验证用户只能访问自己的会话
   - 防止会话信息泄露

2. **XSS 防护**
   - 对消息内容进行适当的 HTML 转义
   - 防止恶意脚本注入

### 11.2 数据隐私

1. **敏感信息保护**
   - 不暴露用户的敏感信息
   - 只显示必要的昵称和商品信息

2. **删除数据处理**
   - 商品删除后仍保留必要的快照信息
   - 确保会话历史的完整性

---

## 十二、测试要点

### 12.1 功能测试

1. **会话列表展示**
   - 验证用户能看到自己参与的所有会话
   - 验证不能看到未参与的会话

2. **排序验证**
   - 验证会话按最后消息时间正确排序
   - 验证新消息会话置顶

3. **未读数验证**
   - 验证未读消息数准确
   - 验证进入会话后未读数清零

4. **筛选功能**
   - 验证关键词搜索功能
   - 验证未读筛选功能

5. **分页功能**
   - 验证分页导航正确
   - 验证每页数量正确

6. **空状态**
   - 验证无会话时的展示
   - 验证搜索无结果时的展示

### 12.2 边界测试

1. **商品删除**
   - 验证商品删除后会话仍正常显示
   - 验证商品快照信息完整

2. **用户状态**
   - 验证对方用户状态不影响会话展示
   - 验证会话记录的完整性

3. **大量数据**
   - 测试大量会话时的性能
   - 验证分页在大数据量下的表现

---

## 十三、总结

本设计文档详细描述了 F35 查看聊天消息列表功能的完整实现方案，包括：

1. **完整的业务规则**：完整保留了原始业务描述
2. **面向对象设计**：采用标准的 MVC 分层架构
3. **完整的伪代码**：提供了从模型到视图的完整伪代码
4. **程序流程图**：标注了需要绘制程序流程图的需求
5. **全面的考虑**：包括性能优化、安全考虑和测试要点

该设计完全贴合现有项目架构，可以直接指导开发实现。

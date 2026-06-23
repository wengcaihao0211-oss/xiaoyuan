# F39 卖家评价买家

## 一、业务概述

### 1.1 所属模块
消息、评价与举报

### 1.2 参与者
已登录普通用户（卖家）

### 1.3 优先级
高

### 1.4 前置条件
订单已完成且当前用户为卖家；该方向尚未评价。

### 1.5 触发条件
卖家提交评价。

## 二、数据输入

### 2.1 输入数据
订单编号、1～5 星评分、0～500 字内容。

## 三、处理流程与业务规则

### 3.1 处理流程

1. **订单关系和完成状态校验**
系统首先验证订单是否存在、是否已完成，以及当前用户是否为该订单的卖家。只有状态为"COMPLETED"的订单才能进行评价。

2. **重复评价检查**
检查当前用户是否已经对该订单的买家进行过评价。通过唯一约束 `(order_id, reviewer_id)` 保证同一订单同一评价人只能评价一次。

3. **评分验证**
验证评分是否在 1～5 星的有效范围内，防止非法评分数据。

4. **内容过滤**
对评价内容进行安全过滤，防止 XSS 攻击和恶意内容注入。评价内容主要反映沟通和履约情况。

5. **保存评价信息**
保存评价记录，明确标记被评价人为买家。评价记录包含订单编号、评价人、被评价人、评分、内容、创建时间等信息。

6. **更新买家评分统计**
评价提交后，更新买家的平均评分统计，确保评分统计与明细一致。

### 3.2 业务规则

1. **订单完成要求**
只有已完成的订单才能进行评价，未完成或已取消的订单不允许评价。

2. **评价人身份验证**
评价人必须是订单的卖家，不能越权评价其他订单。

3. **唯一性保障**
同一订单同一评价人只能评价一次，防止重复提交。

4. **评分范围限制**
评分必须在 1～5 星之间，不接受超出范围的评分。

5. **内容长度限制**
评价内容长度限制在 0～500 字，允许空内容但有最大长度限制。

6. **被评价人确定**
卖家评价时，被评价人固定为订单的买家，通过订单关系自动确定。

7. **评价内容侧重点**
卖家评价买家时，评价内容主要反映买家的沟通情况和履约情况。

8. **评价独立性**
买卖双方评价互不覆盖，各自独立存在，买家的评价不会影响卖家的评价，反之亦然。

## 四、输出及后置条件

### 4.1 输出
评价成功并更新买家评分摘要。

### 4.2 后置条件
- 评价记录成功保存到数据库
- 买家的平均评分统计更新
- 用户可以在订单详情页面查看自己提交的评价
- 其他相关页面显示买家最新的评分信息
- 买卖双方的评价互不影响，各自独立展示

## 五、异常与边界处理

### 5.1 重复评价
当用户尝试对同一订单重复评价时，系统拒绝操作并提示"您已经评价过此订单。"。

### 5.2 订单未完成
对于状态不是"COMPLETED"的订单，系统拒绝评价请求并提示"只能评价已完成的订单。"。

### 5.3 评分越界
当评分不在 1～5 星范围内时，系统拒绝评价并提示"评分必须在1~5之间。"。

### 5.4 越权操作
当用户尝试评价不属于自己的订单时，系统拒绝操作并提示"无权评价此订单。"。

### 5.5 订单不存在
当订单不存在或已被删除时，系统提示"订单不存在。"。

## 六、验收标准

### 6.1 评价唯一性
每个订单卖家最多评价买家一次。通过数据库唯一约束和代码双重保障，确保不会出现重复评价。

### 6.2 评价独立性
买卖双方评价互不覆盖。买家对卖家的评价和卖家对买家的评价是两条独立的记录，不会互相影响或覆盖。

### 6.3 评分统计一致性
评分统计与明细一致。买家的平均评分应该准确反映所有收到的评价，新增评价后统计立即更新并保持准确。

### 6.4 角色正确识别
卖家评价时被评价人必须是买家，不能错误地评价其他人。

### 6.5 内容正确保存
评价内容需要正确保存和显示，特殊字符需要正确处理，避免显示异常。

---

## 七、面向对象设计

### 7.1 分层架构

本功能采用标准的 MVC 分层架构，符合前后端分离开发逻辑：

1. **表现层（Controller）**
   - 处理评价表单展示和提交
   - 参数验证和权限检查
   - 调用业务逻辑层处理评价

2. **业务逻辑层（Service）**
   - 实现评价的核心业务规则
   - 处理重复评价检查
   - 验证评分和内容
   - 更新评分统计

3. **数据访问层（Model）**
   - 评价数据模型
   - 用户评分统计属性
   - 数据库唯一约束

### 7.2 核心类设计

#### 7.2.1 数据模型

```python
# Review 模型 - 表示评价记录
class Review:
    review_id: int
    order_id: int
    reviewer_id: int
    reviewed_user_id: int
    score: int
    review_content: str
    created_at: datetime
    deleted: bool
    
    @classmethod
    def active(cls):
        """获取未删除的评价查询"""
        pass
```

#### 7.2.2 业务服务层

```python
# ReviewService - 评价业务服务
class ReviewService:
    
    @staticmethod
    def submit_review(order_id, reviewer_id, score, content=None):
        """
        提交评价
        
        Args:
            order_id: 订单编号
            reviewer_id: 评价人编号
            score: 评分（1-5星）
            content: 评价内容（可选）
            
        Returns:
            tuple: (是否成功, 消息)
        """
        pass
    
    @staticmethod
    def has_reviewed(order_id, reviewer_id):
        """
        检查是否已评价
        
        Args:
            order_id: 订单编号
            reviewer_id: 评价人编号
            
        Returns:
            bool: 是否已评价
        """
        pass
    
    @staticmethod
    def get_user_reviews(user_id):
        """
        获取用户收到的评价
        
        Args:
            user_id: 用户编号
            
        Returns:
            list: 评价列表
        """
        pass
```

---

## 八、完整伪代码

### 8.1 数据模型层伪代码

```python
# app/models/review.py
from datetime import datetime
from app.extensions import db
from sqlalchemy import CheckConstraint


class Review(db.Model):
    __tablename__ = 'review'
    __table_args__ = (
        db.UniqueConstraint('order_id', 'reviewer_id', name='uk_review_order_reviewer'),
        CheckConstraint('score BETWEEN 1 AND 5', name='chk_review_score'),
        CheckConstraint('reviewer_id <> reviewed_user_id', name='chk_review_users'),
    )

    review_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='评价编号')
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False, comment='订单编号')
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment='评价人编号')
    reviewed_user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment='被评价人编号')
    score = db.Column(db.SmallInteger, nullable=False, comment='评分')
    review_content = db.Column(db.String(500), nullable=True, comment='评价内容')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    deleted = db.Column(db.Boolean, nullable=False, default=False, comment='逻辑删除标志')

    @classmethod
    def active(cls):
        return cls.query.filter_by(deleted=False)
```

### 8.2 业务服务层伪代码

```python
# app/services/review_service.py
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
    """
    提交评价
    
    Args:
        order_id: 订单编号
        reviewer_id: 评价人编号
        score: 评分（1-5星）
        content: 评价内容（可选）
        
    Returns:
        tuple: (是否成功, 消息)
    """
    # 获取订单
    order = db.session.get(Order, order_id)
    if not order or order.deleted:
        return False, '订单不存在。'
    
    # 检查订单状态
    if order.order_status != 'COMPLETED':
        return False, '只能评价已完成的订单。'
    
    # 检查权限
    if reviewer_id not in (order.buyer_id, order.seller_id):
        return False, '无权评价此订单。'
    
    # 确定被评价人：卖家评价买家
    reviewed_user_id = order.buyer_id if reviewer_id == order.seller_id else order.seller_id
    
    # 检查是否已评价
    existing = Review.active().filter_by(order_id=order_id, reviewer_id=reviewer_id).first()
    if existing:
        return False, '您已经评价过此订单。'
    
    # 检查评分范围
    if score < 1 or score > 5:
        return False, '评分必须在1~5之间。'
    
    # 过滤评价内容
    filtered_content = _filter_content(content)
    
    # 创建评价
    review = Review(
        order_id=order_id,
        reviewer_id=reviewer_id,
        reviewed_user_id=reviewed_user_id,
        score=score,
        review_content=filtered_content
    )
    db.session.add(review)
    db.session.commit()
    
    return True, '评价提交成功！'


def get_user_reviews(user_id):
    """
    获取用户收到的评价
    
    Args:
        user_id: 用户编号
        
    Returns:
        list: 评价列表，按创建时间倒序
    """
    return Review.active().filter_by(reviewed_user_id=user_id).order_by(
        Review.created_at.desc()).all()


def has_reviewed(order_id, reviewer_id):
    """
    检查是否已评价
    
    Args:
        order_id: 订单编号
        reviewer_id: 评价人编号
        
    Returns:
        bool: 是否已评价
    """
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
```

### 8.3 表现层控制器伪代码

```python
# app/blueprints/social/routes.py
@social_bp.route('/review/<int:order_id>', methods=['GET', 'POST'])
@login_required
def review(order_id):
    """
    评价表单处理（支持买卖双方）
    
    Args:
        order_id: 订单编号
        
    Returns:
        渲染的评价表单页面或重定向
    """
    # 获取订单
    order = db.session.get(Order, order_id)
    if not order or order.deleted:
        flash('订单不存在。', 'danger')
        return redirect(url_for('browse.home'))
    
    # 检查权限
    if current_user.user_id not in (order.buyer_id, order.seller_id):
        flash('无权评价此订单。', 'danger')
        return redirect(url_for('browse.home'))
    
    # 检查是否已评价
    if review_service.has_reviewed(order_id, current_user.user_id):
        flash('您已经评价过此订单。', 'info')
        return redirect(url_for('order.detail', id=order_id))
    
    form = ReviewForm()
    if form.validate_on_submit():
        # 提交评价
        success, message = review_service.submit_review(
            order_id=order_id,
            reviewer_id=current_user.user_id,
            score=form.score.data,
            content=form.review_content.data
        )
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('order.detail', id=order_id))
    
    # 获取相关信息
    product = db.session.get(Product, order.product_id)
    other_user = order.buyer if current_user.user_id == order.seller_id else order.seller_ref
    
    # 确定评价方向
    review_direction = "评价买家" if current_user.user_id == order.seller_id else "评价卖家"
    
    return render_template('social/review_form.html',
                         order=order, product=product,
                         other_user=other_user, form=form,
                         review_direction=review_direction)
```

---

## 九、程序流程图

此业务流程需要绘制程序流程图，主要流程节点如下：

```
开始
  ↓
用户点击评价按钮
  ↓
验证订单是否存在
  ↓
验证订单状态是否已完成
  ↓
验证当前用户是否为订单卖家
  ↓
检查是否已评价过该订单
  ↓
验证评分是否在1~5星范围内
  ↓
过滤评价内容防止XSS
  ↓
保存评价记录（被评价人为买家）
  ↓
更新买家评分统计
  ↓
返回评价成功结果
  ↓
结束
```

### 流程图说明

1. **开始节点**：用户点击订单详情中的评价按钮
2. **订单存在性检查**：确认订单存在且未删除
3. **订单状态检查**：确认订单状态为"COMPLETED"
4. **身份验证**：确认当前用户是订单的卖家
5. **重复评价检查**：确认该用户尚未对该订单评价过
6. **评分验证**：确认评分在1-5星有效范围内
7. **内容过滤**：对评价内容进行安全处理
8. **保存评价**：将评价信息存入数据库，被评价人为买家
9. **更新统计**：更新被评价人的平均评分
10. **返回结果**：向用户反馈评价结果
11. **结束节点**：流程完成

---

## 十、性能优化建议

### 10.1 数据库优化

1. **索引优化**
   - `(order_id, reviewer_id)` 已有唯一索引，支持重复检查
   - `(reviewed_user_id, created_at)` 复合索引，优化按用户查看评价的查询
   - `(reviewed_user_id)` 索引，优化平均评分统计查询

2. **查询优化**
   - 用户平均评分使用聚合查询缓存
   - 避免频繁计算，考虑定期更新或使用触发器
   - 获取订单评价时，可同时获取买卖双方的评价

### 10.2 缓存策略

1. **评分统计缓存**
   - 缓存用户平均评分，评价时更新
   - 设置合理过期时间兜底

2. **评价列表缓存**
   - 对用户收到的评价列表进行分页缓存
   - 新评价时失效相关缓存

---

## 十一、安全考虑

### 11.1 访问控制

1. **身份验证**
   - 确保用户已登录
   - 验证评价人身份与订单关系

2. **权限验证**
   - 只能评价自己参与的订单
   - 卖家只能评价买家，不能反过来

### 11.2 数据安全

1. **内容安全**
   - XSS防护，过滤危险标签和属性
   - HTML转义，防止注入攻击

2. **数据完整性**
   - 使用数据库唯一约束防止重复评价
   - 使用检查约束保证评分范围

---

## 十二、测试要点

### 12.1 功能测试

1. **卖家评价买家**
   - 正常评价流程测试
   - 不同评分值的评价测试
   - 带内容和不带内容的评价测试

2. **买卖双方独立评价**
   - 买家评价卖家后，卖家仍可评价买家
   - 两者的评价互不影响，各自独立存在
   - 在订单详情页面都能正确显示

3. **重复评价**
   - 卖家尝试对同一订单重复评价应被拒绝
   - 检查错误提示是否正确

4. **权限验证**
   - 未登录用户不能评价
   - 非订单卖家不能评价
   - 买家不能以卖家身份评价

5. **订单状态**
   - 只能评价已完成的订单
   - 其他状态的订单应被拒绝

### 12.2 边界测试

1. **评分边界**
   - 1星和5星的边界值测试
   - 0星和6星的非法值测试

2. **内容长度**
   - 空内容测试
   - 500字内容测试
   - 超过500字的截断测试

3. **特殊字符**
   - 包含HTML标签的内容测试
   - 包含特殊符号的内容测试

4. **双向评价**
   - 买卖双方都评价的场景测试
   - 两个评价独立显示，互不覆盖

---

## 十三、总结

本设计文档详细描述了 F39 卖家评价买家功能的完整实现方案，包括：

1. **完整的业务规则**：完整保留了原始业务描述
2. **清晰的流程说明**：详细说明了评价的完整处理流程
3. **完整的伪代码**：提供了从模型到视图的完整实现
4. **程序流程图**：标注了需要绘制程序流程图的需求
5. **全面的考虑**：包括性能优化、安全考虑和测试要点

该设计完全贴合现有项目架构，可以直接指导开发实现。同时，该功能与 F38 买家评价卖家共享大部分代码逻辑，通过 `reviewed_user_id` 的动态确定来支持双向评价，确保买卖双方评价互不覆盖。

# 校园交易系统 — 全局 ER 图

> 基于 `sql/schema.sql` (MySQL 8.0) 生成，覆盖 10 张表、18 条外键关系。

```mermaid
erDiagram
    user {
        bigint user_id PK "用户编号"
        varchar username UK "用户名(唯一)"
        varchar password_hash "密码哈希"
        varchar avatar "头像地址"
        varchar phone "联系方式"
        varchar introduction "个人简介"
        varchar role "用户角色: ADMIN/USER"
        varchar status "账号状态: ACTIVE/DISABLED"
        datetime created_at "创建时间"
        datetime updated_at "更新时间"
        tinyint deleted "逻辑删除"
    }

    category {
        bigint category_id PK "分类编号"
        varchar category_name UK "分类名称(唯一)"
        varchar description "分类描述"
        varchar status "状态: ENABLED/DISABLED"
        datetime created_at "创建时间"
        datetime updated_at "更新时间"
    }

    product {
        bigint product_id PK "商品编号"
        bigint seller_id FK "卖家编号 → user"
        bigint category_id FK "分类编号 → category"
        varchar product_name "商品名称"
        decimal price "商品价格"
        varchar condition_level "成色"
        text description "商品描述"
        varchar trade_location "交易地点"
        varchar product_status "状态: DRAFT/ON_SALE/SOLD/REMOVED"
        bigint view_count "浏览次数"
        datetime created_at "创建时间"
        datetime updated_at "更新时间"
        tinyint deleted "逻辑删除"
    }

    product_image {
        bigint image_id PK "图片编号"
        bigint product_id FK "商品编号 → product"
        varchar image_url "图片地址"
        int sort_order "排序号"
        datetime created_at "创建时间"
    }

    favorite {
        bigint favorite_id PK "收藏编号"
        bigint user_id FK "用户编号 → user"
        bigint product_id FK "商品编号 → product"
        datetime created_at "收藏时间"
    }

    orders {
        bigint order_id PK "订单编号"
        varchar order_no UK "订单业务编号(唯一)"
        bigint product_id FK "商品编号 → product"
        bigint buyer_id FK "买家编号 → user"
        bigint seller_id FK "卖家编号 → user"
        decimal order_amount "订单金额"
        varchar trade_type "交易方式"
        varchar buyer_message "买家留言"
        varchar order_status "订单状态: PENDING/CONFIRMED/PAID/COMPLETED"
        varchar payment_status "支付状态: UNPAID/PAID"
        varchar reject_reason "拒绝原因"
        datetime created_at "创建时间"
        datetime paid_at "支付时间"
        datetime completed_at "完成时间"
        datetime updated_at "更新时间"
        tinyint deleted "逻辑删除"
        bigint active_product_id UK "活跃商品约束(GENERATED)"
    }

    message {
        bigint message_id PK "消息编号"
        bigint sender_id FK "发送者 → user"
        bigint receiver_id FK "接收者 → user"
        bigint product_id FK "关联商品 → product"
        text message_content "消息内容"
        tinyint read_status "阅读状态"
        datetime created_at "发送时间"
        tinyint deleted "逻辑删除"
    }

    review {
        bigint review_id PK "评价编号"
        bigint order_id FK "订单编号 → orders"
        bigint reviewer_id FK "评价人 → user"
        bigint reviewed_user_id FK "被评价人 → user"
        tinyint score "评分(1-5)"
        varchar review_content "评价内容"
        datetime created_at "评价时间"
        tinyint deleted "逻辑删除"
    }

    report {
        bigint report_id PK "举报编号"
        bigint reporter_id FK "举报人 → user"
        varchar target_type "举报对象类型"
        bigint target_id "举报对象编号"
        varchar report_reason "举报原因"
        varchar description "举报说明"
        varchar report_status "处理状态: PENDING/HANDLED/DISMISSED"
        varchar handle_result "处理结果"
        bigint handler_id FK "管理员 → user"
        datetime created_at "举报时间"
        datetime handled_at "处理时间"
    }

    notification {
        bigint notification_id PK "通知编号"
        bigint receiver_id FK "接收者 → user"
        varchar notification_type "通知类型"
        varchar title "通知标题"
        text content "通知内容"
        bigint related_id "关联业务编号"
        tinyint read_status "阅读状态"
        datetime created_at "通知时间"
        tinyint deleted "逻辑删除"
    }

%% ===== 关系定义 =====

%% product 关系
product }o--|| user : "seller_id → user_id (卖家)"
product }o--|| category : "category_id → category_id (分类)"

%% product_image 关系
product_image }o--|| product : "product_id → product_id (图片归属)"

%% favorite 关系 (复合唯一: user_id + product_id)
favorite }o--|| user : "user_id → user_id (收藏人)"
favorite }o--|| product : "product_id → product_id (收藏商品)"

%% orders 关系 (复合唯一: active_product_id)
orders }o--|| product : "product_id → product_id (订单商品)"
orders }o--|| user : "buyer_id → user_id (买家)"
orders }o--|| user_seller["user"] : "seller_id → user_id (卖家)"

%% message 关系
message }o--|| user : "sender_id → user_id (发送者)"
message }o--|| user_receiver["user"] : "receiver_id → user_id (接收者)"
message }o--o| product : "product_id → product_id (关联商品,可空)"

%% review 关系 (复合唯一: order_id + reviewer_id)
review }o--|| orders : "order_id → order_id (评价订单)"
review }o--|| user : "reviewer_id → user_id (评价人)"
review }o--|| user_reviewed["user"] : "reviewed_user_id → user_id (被评价人)"

%% report 关系
report }o--|| user : "reporter_id → user_id (举报人)"
report }o--o| user_handler["user"] : "handler_id → user_id (处理人,可空)"

%% notification 关系
notification }o--|| user : "receiver_id → user_id (接收者)"
```

## 关系矩阵

| # | 源表 | 目标表 | 基数 | 外键列 | 备注 |
|---|------|--------|------|--------|------|
| 1 | product | user | N:1 | seller_id → user_id | 卖家 |
| 2 | product | category | N:1 | category_id → category_id | 分类 |
| 3 | product_image | product | N:1 | product_id → product_id | 图片归属 |
| 4 | favorite | user | N:1 | user_id → user_id | 收藏人 |
| 5 | favorite | product | N:1 | product_id → product_id | 收藏商品 |
| 6 | orders | product | N:1 | product_id → product_id | 订单商品 |
| 7 | orders | user | N:1 | buyer_id → user_id | 买家 |
| 8 | orders | user | N:1 | seller_id → user_id | 卖家 |
| 9 | message | user | N:1 | sender_id → user_id | 发送者 |
| 10 | message | user | N:1 | receiver_id → user_id | 接收者 |
| 11 | message | product | N:1 | product_id → product_id | 关联商品(可空) |
| 12 | review | orders | N:1 | order_id → order_id | 评价订单 |
| 13 | review | user | N:1 | reviewer_id → user_id | 评价人 |
| 14 | review | user | N:1 | reviewed_user_id → user_id | 被评价人 |
| 15 | report | user | N:1 | reporter_id → user_id | 举报人 |
| 16 | report | user | N:1 | handler_id → user_id | 处理人(可空) |
| 17 | notification | user | N:1 | receiver_id → user_id | 通知接收者 |

## 复合唯一约束

| 表 | 约束列 | 说明 |
|----|--------|------|
| favorite | (user_id, product_id) | 同一用户不能重复收藏同一商品 |
| review | (order_id, reviewer_id) | 同一订单每人只能评价一次 |
| orders | (active_product_id) | 同一商品同一时间只有一个有效订单 |

## 核心实体簇

```
                    ┌─────────────────┐
                    │     category     │
                    └────────┬────────┘
                             │ 1:N
              ┌──────────────┼──────────────┐
              │              ▼              │
              │  ┌─────────────────────┐    │
              │  │      product        │◄───┼── product_image (1:N)
              │  └────────┬───────────┘    │
              │           │                 │
   favorite ──┼── N:1 ────┤─ N:1 ── orders │
              │           │                 │
   message ───┼── N:1 ────┘                 │
              │                             │
              ▼                             ▼
    ┌─────────────────────────────────────────┐
    │                  user                    │
    │  (被 8 张表以不同角色引用)                 │
    └─────────────────────────────────────────┘
      ▲       ▲       ▲       ▲       ▲
      │       │       │       │       │
    product  orders  orders  message  message
    seller   buyer   seller  sender   receiver
      │       │       │       │       │
      ▼       ▼       ▼       ▼       ▼
    review  review  report  report  notification
    reviewer reviewed reporter handler  receiver
```

总关系数: **17 条外键**，**3 组复合唯一约束**。

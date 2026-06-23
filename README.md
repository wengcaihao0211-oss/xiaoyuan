# 校园二手物品交易与闲置管理系统

基于 Python Flask + Supabase PostgreSQL 的校园二手交易平台，实现 B/S 架构的 Web 应用。

## 技术栈

- **后端**: Python 3.10+, Flask 3.1
- **数据库**: Supabase PostgreSQL
- **ORM**: SQLAlchemy 2.0 + Flask-SQLAlchemy
- **前端**: Jinja2 模板 + Bootstrap 5
- **认证**: Flask-Login + Werkzeug 密码哈希

## 功能模块（50个需求）

| 模块 | 需求编号 | 功能 |
|------|---------|------|
| A 用户账号 | F01-F06 | 注册、登录（5次锁定）、登出、找回密码、修改密码、编辑资料 |
| B 商品发布 | F07-F16 | 发布商品、上传图片、分类选择、定价、草稿、管理、编辑、删除、上下架 |
| C 浏览收藏 | F17-F23 | 首页推荐、分类浏览、搜索筛选、商品详情、收藏管理 |
| D 订单交易 | F24-F33 | 提交订单、线上/线下交易、订单管理、确认、取消、拒绝、模拟支付、确认收货 |
| E 消息评价 | F34-F40 | 站内消息、聊天、双向评价、举报 |
| F 通知 | F41-F42 | 系统通知、订单通知 |
| G 管理后台 | F43-F50 | 管理员登录、用户管理、商品审核、分类管理、举报处理、数据统计 |

## 快速开始

### 1. 环境要求

- Python 3.10+
- Supabase 项目和 Postgres 连接串
- pip

### 2. 安装依赖

```bash
cd xiaoyuan
pip install -r requirements.txt
```

### 3. 配置 Supabase 数据库

编辑 `.env.example` 为 `.env`，修改数据库连接信息：

```env
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
```

在 Supabase 中创建表结构，二选一：

```bash
python init_db.py
```

或把 `sql/schema_pg.sql` 粘贴到 Supabase SQL Editor 执行。

如果你只想临时在本地使用 SQLite 调试，可额外设置：

```env
ALLOW_SQLITE_DEV=1
```

### 4. 初始化数据

`python init_db.py` 会自动：

- 创建所有表
- 初始化 7 个商品分类
- 创建管理员账号 `admin / admin123`
- 创建测试账号 `testuser / test123`

### 5. 运行

```bash
python run.py
```

访问 http://localhost:5000

## 项目结构

```
xiaoyuan/
├── app/
│   ├── __init__.py           # 应用工厂
│   ├── config.py              # 配置
│   ├── extensions.py          # Flask 扩展
│   ├── models/                # 数据模型 (10张表)
│   ├── services/              # 业务逻辑层
│   ├── blueprints/            # 路由 (8个蓝图)
│   ├── templates/             # Jinja2 模板 (~32个)
│   ├── static/                # 静态资源
│   └── utils/                 # 工具函数
├── uploads/                   # 用户上传文件
│   ├── avatars/
│   └── products/
├── sql/schema.sql             # 数据库DDL
├── requirements.txt
├── run.py
└── README.md
```

## 用户角色

- **访客**: 浏览首页、分类、搜索、商品详情
- **普通用户**: 发布商品、下单、消息、评价、收藏、举报
- **管理员**: 用户管理、商品审核、分类管理、举报处理、数据统计

## 订单状态流转

```
PENDING → CONFIRMED → PAID → COMPLETED
    ↓          ↓
REJECTED   CANCELLED
```

## 注意事项

- 支付为模拟支付（Mock），不涉及真实资金
- 图片上传限制：JPG/PNG/WebP，单张≤5MB，每商品最多6张
- 登录锁定：5次失败锁定15分钟
- 同一商品同一买家只能有一个活跃订单
- 默认开发配置已切换到 Supabase；未提供 `DATABASE_URL` 时不会再静默写入本地 SQLite

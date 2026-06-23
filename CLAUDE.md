# 校园二手物品交易与闲置管理系统

## 项目概述

- Flask + PostgreSQL + Jinja2 全栈 Web 应用
- 50 个功能需求 (F01-F50)，7 大模块
- 已部署：Vercel (Serverless) + Supabase (PostgreSQL)

## 本地运行

```bash
pip install -r requirements.txt
python run.py
# 默认读取 Supabase PostgreSQL 连接串
```

## 技术栈

- **后端**: Flask 3.1, SQLAlchemy 2.0, Flask-Login
- **前端**: Jinja2 模板 + Bootstrap 5 + 自定义 CSS
- **数据库**: Supabase PostgreSQL
- **部署**: Vercel (api/index.py 入口)

## 项目结构

```
xiaoyuan/
├── api/index.py              # Vercel 入口
├── app/
│   ├── __init__.py            # Flask 应用工厂，蓝图注册，上下文处理器
│   ├── config.py              # 配置类 (Dev/Prod/Test)
│   ├── extensions.py          # db, login_manager, migrate
│   ├── models/                # 10 个 SQLAlchemy 模型
│   │   ├── user.py            # 用户 (users表)
│   │   ├── category.py        # 分类
│   │   ├── product.py         # 商品
│   │   ├── product_image.py   # 商品图片
│   │   ├── favorite.py        # 收藏
│   │   ├── orders.py          # 订单 + 状态机
│   │   ├── message.py         # 站内消息
│   │   ├── review.py          # 评价 (1-5星)
│   │   ├── report.py          # 举报
│   │   └── notification.py    # 通知
│   ├── services/              # 业务逻辑层（路由只做参数提取+渲染）
│   │   ├── auth_service.py    # 登录锁/OTP/密码
│   │   ├── order_service.py   # 订单状态机/支付模拟
│   │   └── ...
│   ├── blueprints/            # 8 个蓝图 = 8 个 URL 前缀
│   │   ├── auth/              # /auth (登录/注册/密码)
│   │   ├── user/              # /user (个人资料)
│   │   ├── product/           # /product (发布/编辑/下架)
│   │   ├── browse/            # / (首页/搜索/详情/收藏)
│   │   ├── order/             # /order (下单/支付/完成)
│   │   ├── social/            # /social (聊天/评价/举报)
│   │   ├── notification/      # /notifications
│   │   └── admin/             # /admin (管理后台 8 个功能)
│   ├── templates/             # Jinja2 模板 (~32个)
│   ├── static/                # CSS, JS, 上传文件
│   └── utils/                 # 装饰器/文件上传/分页
├── run.py                     # 本地启动
├── vercel.json                # Vercel 部署配置
└── requirements.txt
```

## 架构约定

- **路由薄，服务厚**: routes.py 只做参数提取 + 调用 service + 渲染模板
- **Service 返回三元组**: `(success: bool, message: str, result: Any)`
- **软删除**: 主表都有 `deleted` 列，用 `.active()` 过滤
- **订单状态机**: PENDING → CONFIRMED → PAID → COMPLETED (见 orders.py)
- **管理员**: 角色 `role='ADMIN'`，`/admin/*` 路由用 `@admin_required` 保护

## 常用开发任务

- **加新功能**: 在对应蓝图下加路由 → 服务层写逻辑 → 加模板
- **改样式**: 改 `app/static/css/app.css`（CSS 变量在 `:root`）
- **改布局**: 改 `app/templates/base.html`
- **加数据库字段**: 改 model → 本地测试 → Supabase SQL Editor 加列
- **本地临时改用 SQLite**: 仅在确有需要时设置 `ALLOW_SQLITE_DEV=1`

## 部署相关

- Vercel 自动从 GitHub main 分支部署
- 环境变量在 Vercel Settings 里设：`DATABASE_URL`, `SECRET_KEY`
- Supabase 表结构在 `sql/schema_pg.sql`
- Vercel 上文件上传不可用（Serverless 无持久存储）

# Debug Session: admin-review-500
- **Status**: [OPEN]
- **Issue**: 管理员界面点击审核商品时出现 500 服务器内部错误
- **Debug Server**: pending
- **Log File**: .dbg/trae-debug-log-admin-review-500.ndjson

## Reproduction Steps
1. 启动本地 Flask 服务
2. 使用管理员账号登录后台
3. 打开商品审核页面
4. 点击通过或驳回商品
5. 观察是否返回 500

## Hypotheses & Verification
| ID | Hypothesis | Likelihood | Effort | Evidence |
|----|------------|------------|--------|----------|
| A | 审核路由接收到的参数不完整或表单提交与路由不匹配 | High | Low | Pending |
| B | `admin_service.review_product()` 在状态流转或数据库提交时抛异常 | High | Low | Pending |
| C | 审核页面模板中的按钮或表单配置导致异常请求 | Med | Low | Pending |
| D | 管理员会话或权限检查在审核动作时触发异常 | Med | Low | Pending |
| E | 某条真实商品数据触发了仅运行时可见的异常 | Med | Med | Pending |

## Log Evidence
- `pre-fix` 审核动作本身成功：`.dbg/trae-debug-log-admin-review-500.ndjson` 记录了 `approve request received`、`review product entered`、`approve before commit`、`approve commit succeeded`、`approve request completed`，说明路由和 `admin_service.review_product()` 不是 500 根因。
- 复现 `GET /admin/products/review` 时抛出 `sqlalchemy.exc.InternalError: (psycopg2.errors.InFailedSqlTransaction)`。
- 触发链路位于 `app/__init__.py` 的全局未读通知计数：`Notification.query.filter_by(receiver_id=current_user.user_id, read_status=0, deleted=0).count()`。
- 在 PostgreSQL 上，布尔字段与 `0` 比较会导致查询失败；异常分支又没有 `db.session.rollback()`，使当前事务进入 aborted 状态，后续模板访问 `p.seller.username` 时整页变成 500。
- 修复后再次复现，`/admin/products/review` 返回 `200`，页面标题正常渲染为“商品审核”。

## Verification Conclusion
- A：Rejected。审核表单提交与路由匹配，`approve` 请求可正常进入并完成。
- B：Rejected。`admin_service.review_product()` 提交事务成功，不是审核动作本身报错。
- C：Rejected。模板中的审核按钮不是直接根因。
- D：Rejected。管理员权限检查可通过，问题不在鉴权装饰器。
- E：Confirmed。错误由管理员页渲染阶段的数据库方言差异触发，只在运行时和 PostgreSQL 事务状态下显现。

## Fix
- 将 `app/__init__.py` 中未读通知统计的布尔筛选从 `read_status=0, deleted=0` 改为 `read_status=False, deleted=False`。
- 在该查询的异常分支中增加 `db.session.rollback()`，避免事务被污染后继续影响模板中的其他查询。

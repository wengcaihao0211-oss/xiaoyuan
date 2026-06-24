"""通知模块完整测试"""
import sys
import traceback

passed = 0
failed = 0
errors = []


def test(name, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f'  PASS  {name}')
    except AssertionError as e:
        failed += 1
        errors.append((name, str(e)))
        print(f'  FAIL  {name}: {e}')
    except Exception as e:
        failed += 1
        errors.append((name, traceback.format_exc()))
        print(f'  ERROR {name}: {e}')


def assert_eq(a, b, msg=''):
    assert a == b, f'{msg} expected={b!r}, got={a!r}'


def assert_true(v, msg=''):
    assert v, f'{msg} expected truthy, got {v!r}'


def assert_false(v, msg=''):
    assert not v, f'{msg} expected falsy, got {v!r}'


from app import create_app
from app.extensions import db
from app.services import notification_service as ns
from app.models.notification import Notification
from app.models.user import User
from app.models.product import Product

app = create_app()

# 添加临时测试登录路由（必须在 app_context 之外注册）
def _test_login_fn(user_id):
    from flask_login import login_user as _login_user
    user = db.session.get(User, user_id)
    if user:
        _login_user(user)
    return 'ok'

app.add_url_rule('/_test_login/<int:user_id>', '_test_login', _test_login_fn)

with app.app_context():
    with app.test_request_context('/'):
        # ============================================================
        print('\n=== 1. Service 层: create_notification ===')
        # ============================================================

        def t_create():
            ok, msg, n = ns.create_notification(
                receiver_id=2, ntype='SYSTEM', title='系统测试', content='内容'
            )
            assert_true(ok, 'create ok')
            assert_eq(n.notification_type, 'SYSTEM', 'type')
            assert_eq(n.receiver_id, 2, 'receiver')
            assert_eq(n.title, '系统测试', 'title')
            # 验证已提交到数据库
            from_db = db.session.get(Notification, n.notification_id)
            assert_true(from_db, 'persisted in db')
        test('创建系统通知并提交到数据库', t_create)

        def t_create_with_sender():
            ok, msg, n = ns.create_notification(
                receiver_id=2, ntype='ORDER', title='订单通知', content='内容',
                related_id=1, sender_id=3
            )
            assert_true(ok)
            assert_eq(n.sender_id, 3, 'sender_id')
            assert_eq(n.related_id, 1, 'related_id')
        test('创建带 sender_id 和 related_id 的通知', t_create_with_sender)

        # ============================================================
        print('\n=== 2. Service 层: get_notification_by_id ===')
        # ============================================================

        def t_get_existing():
            ok, msg, n = ns.create_notification(
                receiver_id=1, ntype='SYSTEM', title='T', content='C'
            )
            ok2, msg2, n2 = ns.get_notification_by_id(n.notification_id, 1)
            assert_true(ok2, 'get ok')
            assert_eq(n2.notification_id, n.notification_id, 'id match')
        test('获取存在的通知', t_get_existing)

        def t_get_wrong_user():
            ok, msg, n = ns.create_notification(
                receiver_id=1, ntype='SYSTEM', title='T', content='C'
            )
            ok2, msg2, n2 = ns.get_notification_by_id(n.notification_id, 999)
            assert_false(ok2, 'should fail for wrong user')
            assert_true(n2 is None, 'notif should be None')
        test('越权访问 - 其他用户的通知', t_get_wrong_user)

        def t_get_deleted():
            ok, msg, n = ns.create_notification(
                receiver_id=1, ntype='SYSTEM', title='T', content='C'
            )
            ns.delete_notification(n.notification_id, 1)
            ok2, msg2, n2 = ns.get_notification_by_id(n.notification_id, 1)
            assert_false(ok2, 'should fail for deleted')
        test('访问已删除的通知', t_get_deleted)

        def t_get_nonexistent():
            ok, msg, n = ns.get_notification_by_id(999999, 1)
            assert_false(ok, 'should fail for nonexistent')
        test('访问不存在的通知', t_get_nonexistent)

        # ============================================================
        print('\n=== 3. Service 层: mark_read ===')
        # ============================================================

        def t_mark_read():
            ok, msg, n = ns.create_notification(
                receiver_id=1, ntype='SYSTEM', title='T', content='C'
            )
            assert_false(n.read_status, 'initially unread')
            ok2, msg2, n2 = ns.mark_read(n.notification_id, 1)
            assert_true(ok2, 'mark_read ok')
            assert_true(n2.read_status, 'now read')
        test('标记单条已读', t_mark_read)

        def t_mark_read_nonexistent():
            ok, msg, n = ns.mark_read(999999, 1)
            assert_false(ok, 'should fail')
        test('标记不存在的通知已读', t_mark_read_nonexistent)

        # ============================================================
        print('\n=== 4. Service 层: mark_all_read ===')
        # ============================================================

        def t_mark_all_read():
            # 创建几条未读通知
            ns.create_notification(receiver_id=1, ntype='SYSTEM', title='A', content='A')
            ns.create_notification(receiver_id=1, ntype='ORDER', title='B', content='B')
            ns.mark_all_read(1)
            count = ns.get_unread_count(1)
            assert_eq(count, 0, 'all read')
        test('批量标记全部已读', t_mark_all_read)

        # ============================================================
        print('\n=== 5. Service 层: delete_notification ===')
        # ============================================================

        def t_delete():
            ok, msg, n = ns.create_notification(
                receiver_id=1, ntype='SYSTEM', title='T', content='C'
            )
            nid = n.notification_id
            ok2, msg2, n2 = ns.delete_notification(nid, 1)
            assert_true(ok2, 'delete ok')
            # 软删除后查不到
            ok3, msg3, n3 = ns.get_notification_by_id(nid, 1)
            assert_false(ok3, 'should not find deleted')
        test('删除通知（软删除）', t_delete)

        def t_delete_wrong_user():
            ok, msg, n = ns.create_notification(
                receiver_id=1, ntype='SYSTEM', title='T', content='C'
            )
            ok2, msg2, n2 = ns.delete_notification(n.notification_id, 999)
            assert_false(ok2, 'wrong user cannot delete')
        test('越权删除 - 其他用户的通知', t_delete_wrong_user)

        # ============================================================
        print('\n=== 6. Service 层: get_user_notifications + 分页 ===')
        # ============================================================

        def t_get_notifications():
            pag = ns.get_user_notifications(1)
            assert_true(pag.items is not None, 'has items')
            assert_true(len(pag.items) >= 0, 'items is list')
        test('获取用户通知列表', t_get_notifications)

        def t_get_notifications_type_filter():
            # 先创建一条 AUDIT 通知
            ns.create_notification(receiver_id=1, ntype='AUDIT', title='A', content='A')
            pag = ns.get_user_notifications(1, type_filter='AUDIT')
            for n in pag.items:
                assert_eq(n.notification_type, 'AUDIT', 'filter works')
        test('按类型筛选通知', t_get_notifications_type_filter)

        # ============================================================
        print('\n=== 7. Service 层: get_unread_count ===')
        # ============================================================

        def t_unread_count():
            count = ns.get_unread_count(1)
            assert_true(isinstance(count, int), 'count is int')
            assert_true(count >= 0, 'count >= 0')
        test('获取未读数量', t_unread_count)

        # ============================================================
        print('\n=== 8. Service 层: notify_admins ===')
        # ============================================================

        def t_notify_admins():
            ns.notify_admins(title='管理员通知', content='有新举报', related_id=1, sender_id=2)
            admin = User.query.filter_by(role='ADMIN', deleted=False).first()
            pag = ns.get_user_notifications(admin.user_id, type_filter='SYSTEM')
            found = any(n.title == '管理员通知' for n in pag.items)
            assert_true(found, 'admin got the notification')
        test('通知所有管理员', t_notify_admins)

        # ============================================================
        print('\n=== 9. Model 层: target_url ===')
        # ============================================================

        def t_target_url_system():
            ok, msg, n = ns.create_notification(
                receiver_id=1, ntype='SYSTEM', title='T', content='C'
            )
            assert_true(n.target_url is None, 'SYSTEM has no target')
        test('SYSTEM 通知无跳转链接', t_target_url_system)

        def t_target_url_order_no_exist():
            ok, msg, n = ns.create_notification(
                receiver_id=1, ntype='ORDER', title='T', content='C', related_id=99999
            )
            assert_true(n.target_url is None, 'deleted order -> no url')
        test('ORDER 关联订单不存在时无链接', t_target_url_order_no_exist)

        def t_target_url_audit_existing():
            p = db.session.query(Product).filter_by(deleted=False).first()
            if p:
                ok, msg, n = ns.create_notification(
                    receiver_id=1, ntype='AUDIT', title='T', content='C', related_id=p.product_id
                )
                assert_true(n.target_url is not None, 'should have url')
                assert_true('/product/' in n.target_url, f'url should contain /product/: {n.target_url}')
        test('AUDIT 关联存在商品时有跳转链接', t_target_url_audit_existing)

        def t_target_url_review():
            ok, msg, n = ns.create_notification(
                receiver_id=1, ntype='REVIEW', title='T', content='C', related_id=1
            )
            assert_true(n.target_url is None, 'REVIEW has no endpoint')
        test('REVIEW 通知无跳转链接', t_target_url_review)

        def t_target_url_favorite():
            ok, msg, n = ns.create_notification(
                receiver_id=1, ntype='FAVORITE', title='T', content='C', related_id=1
            )
            assert_true(n.target_url is None, 'FAVORITE has no endpoint')
        test('FAVORITE 通知无跳转链接', t_target_url_favorite)

        # ============================================================
        print('\n=== 10. Model 层: related_exists ===')
        # ============================================================

        def t_related_exists_true():
            p = db.session.query(Product).filter_by(deleted=False).first()
            if p:
                ok, msg, n = ns.create_notification(
                    receiver_id=1, ntype='AUDIT', title='T', content='C', related_id=p.product_id
                )
                assert_true(n.related_exists, 'product exists')
        test('AUDIT 关联商品存在', t_related_exists_true)

        def t_related_exists_false():
            ok, msg, n = ns.create_notification(
                receiver_id=1, ntype='AUDIT', title='T', content='C', related_id=99999
            )
            assert_false(n.related_exists, 'product does not exist')
        test('AUDIT 关联商品不存在', t_related_exists_false)

        def t_related_exists_none_type():
            ok, msg, n = ns.create_notification(
                receiver_id=1, ntype='SYSTEM', title='T', content='C', related_id=1
            )
            assert_true(n.related_exists, 'untracked type returns True')
        test('SYSTEM 类型 related_exists 返回 True', t_related_exists_none_type)

        # ============================================================
        print('\n=== 11. Model 层: sender_name ===')
        # ============================================================

        def t_sender_name():
            ok, msg, n = ns.create_notification(
                receiver_id=1, ntype='SYSTEM', title='T', content='C', sender_id=2
            )
            assert_eq(n.sender_name, 'testuser', 'sender name')
        test('sender_name 返回触发者用户名', t_sender_name)

        def t_sender_name_none():
            ok, msg, n = ns.create_notification(
                receiver_id=1, ntype='SYSTEM', title='T', content='C'
            )
            assert_true(n.sender_name is None, 'no sender -> None')
        test('无 sender_id 时 sender_name 返回 None', t_sender_name_none)

        # ============================================================
        print('\n=== 12. Model 层: TYPE_DISPLAY ===')
        # ============================================================

        def t_type_display():
            for t, expected in [
                ('SYSTEM', '系统通知'), ('ORDER', '订单通知'), ('AUDIT', '审核通知'),
                ('ACCOUNT', '账号通知'), ('REPORT', '举报通知'), ('REVIEW', '评价通知'),
                ('FAVORITE', '收藏通知'),
            ]:
                assert_eq(Notification.TYPE_DISPLAY.get(t), expected, f'{t} display')
        test('所有类型显示名称正确', t_type_display)

        # ============================================================
        # 路由层测试
        # ============================================================
        print('\n=== 13. 路由层: 通知列表页 ===')
        # ============================================================

        def t_route_list():
            with app.test_client() as c:
                c.get('/_test_login/2')
                r = c.get('/notifications/')
                assert_eq(r.status_code, 200, 'list 200')
                assert_true(b'\xe9\x80\x9a\xe7\x9f\xa5' in r.data or '通知'.encode() in r.data, 'contains 通知')
        test('GET /notifications/ 返回 200', t_route_list)

        def t_route_list_unauthenticated():
            with app.test_client() as c:
                r = c.get('/notifications/')
                assert_eq(r.status_code, 302, 'redirect to login')
        test('未登录访问通知页 → 302 重定向', t_route_list_unauthenticated)

        def t_route_list_filter():
            with app.test_client() as c:
                c.get('/_test_login/2')
                r = c.get('/notifications/?type=AUDIT')
                assert_eq(r.status_code, 200, 'filter 200')
        test('GET /notifications/?type=AUDIT 返回 200', t_route_list_filter)

        # ============================================================
        print('\n=== 14. 路由层: 通知详情页 ===')
        # ============================================================

        def t_route_detail():
            with app.test_client() as c:
                c.get('/_test_login/2')
                ok, msg, n = ns.create_notification(
                    receiver_id=2, ntype='SYSTEM', title='详情测试', content='内容'
                )
                r = c.get(f'/notifications/{n.notification_id}')
                assert_eq(r.status_code, 200, 'detail 200')
                assert_true(b'\xe8\xaf\xa6\xe6\x83\x85' in r.data or '详情'.encode() in r.data, 'contains detail content')
        test('GET /notifications/<id> 返回详情页', t_route_detail)

        def t_route_detail_auto_read():
            with app.test_client() as c:
                c.get('/_test_login/2')
                ok, msg, n = ns.create_notification(
                    receiver_id=2, ntype='SYSTEM', title='T', content='C'
                )
                assert_false(n.read_status, 'initially unread')
                c.get(f'/notifications/{n.notification_id}')
                n2 = db.session.get(Notification, n.notification_id)
                assert_true(n2.read_status, 'auto marked read')
        test('访问详情页自动标记已读', t_route_detail_auto_read)

        def t_route_detail_wrong_user():
            with app.test_client() as c:
                c.get('/_test_login/2')
                ok, msg, n = ns.create_notification(
                    receiver_id=1, ntype='SYSTEM', title='T', content='C'
                )
                r = c.get(f'/notifications/{n.notification_id}')
                assert_eq(r.status_code, 302, 'wrong user -> redirect')
        test('访问其他用户通知 → 302 重定向', t_route_detail_wrong_user)

        def t_route_detail_nonexistent():
            with app.test_client() as c:
                c.get('/_test_login/2')
                r = c.get('/notifications/999999')
                assert_eq(r.status_code, 302, 'nonexistent -> redirect')
        test('访问不存在的通知 → 302 重定向', t_route_detail_nonexistent)

        # ============================================================
        print('\n=== 15. 路由层: 标记单条已读 ===')
        # ============================================================

        def t_route_read_single():
            with app.test_client() as c:
                c.get('/_test_login/2')
                ok, msg, n = ns.create_notification(
                    receiver_id=2, ntype='SYSTEM', title='T', content='C'
                )
                r = c.post(f'/notifications/{n.notification_id}/read')
                assert_eq(r.status_code, 302, 'read -> redirect')
                n2 = db.session.get(Notification, n.notification_id)
                assert_true(n2.read_status, 'now read')
        test('POST 标记单条已读', t_route_read_single)

        # ============================================================
        print('\n=== 16. 路由层: 删除通知 ===')
        # ============================================================

        def t_route_delete():
            with app.test_client() as c:
                c.get('/_test_login/2')
                ok, msg, n = ns.create_notification(
                    receiver_id=2, ntype='SYSTEM', title='T', content='C'
                )
                r = c.post(f'/notifications/{n.notification_id}/delete')
                assert_eq(r.status_code, 302, 'delete -> redirect')
                n2 = db.session.get(Notification, n.notification_id)
                assert_true(n2.deleted, 'now deleted')
        test('POST 删除通知', t_route_delete)

        # ============================================================
        print('\n=== 17. 路由层: 批量已读 ===')
        # ============================================================

        def t_route_read_all():
            with app.test_client() as c:
                c.get('/_test_login/2')
                ns.create_notification(receiver_id=2, ntype='SYSTEM', title='T1', content='C')
                ns.create_notification(receiver_id=2, ntype='SYSTEM', title='T2', content='C')
                r = c.post('/notifications/read-all')
                assert_eq(r.status_code, 302, 'read-all -> redirect')
                count = ns.get_unread_count(2)
                assert_eq(count, 0, 'all read')
        test('POST 批量全部已读', t_route_read_all)

        # ============================================================
        print('\n=== 18. 业务触发: 收藏通知 ===')
        # ============================================================

        def t_fav_notification():
            with app.test_client() as c:
                c.get('/_test_login/3')  # cyw 登录
                p = db.session.get(Product, 1)
                if p:
                    r = c.post(f'/favorite/toggle/{p.product_id}')
                    pag = ns.get_user_notifications(2, type_filter='FAVORITE')
                    found = any('收藏' in n.title for n in pag.items)
                    assert_true(found, f'testuser got favorite notification (status={r.status_code})')
        test('收藏商品 → 卖家收到收藏通知', t_fav_notification)

        # ============================================================
        print('\n=== 19. 业务触发: 举报通知 (service 层) ===')
        # ============================================================

        def t_report_notification():
            from app.services import report_service
            before = ns.get_unread_count(1)
            ok, msg = report_service.submit_report(
                reporter_id=2, target_type='PRODUCT',
                target_id=2, reason='价格欺诈', description='举报测试'
            )
            assert_true(ok, f'report submitted: {msg}')
            after = ns.get_unread_count(1)
            assert_true(after > before, f'admin got report notification (before={before}, after={after})')
        test('提交举报 → 管理员收到通知', t_report_notification)

        # ============================================================
        # 结果汇总
        # ============================================================
        print(f'\n{"="*60}')
        print(f'  通过: {passed}  失败: {failed}  总计: {passed+failed}')
        print(f'{"="*60}')

        if errors:
            print('\n失败详情:')
            for name, detail in errors:
                print(f'\n--- {name} ---')
                print(detail)

        sys.exit(0 if failed == 0 else 1)

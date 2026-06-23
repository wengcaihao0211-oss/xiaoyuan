# -*- coding: utf-8 -*-
from app import create_app

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False
app.config['TESTING'] = True

client = app.test_client()
response = client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=False)
print({'login_status_code': response.status_code, 'login_location': response.headers.get('Location')})
with client.session_transaction() as sess:
    print({'session_keys': list(sess.keys()), 'user_id': sess.get('_user_id'), 'session_version': sess.get('session_version')})
text = response.get_data(as_text=True)
for marker in ['管理员登录成功', '该账号不是管理员', 'danger', 'warning', '账号', '密码']:
    if marker in text:
        print({'marker_found': marker})

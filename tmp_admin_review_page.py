# -*- coding: utf-8 -*-
from flask_login.utils import _create_identifier
from app import create_app
from app.models.user import User

app = create_app()
app.config['TESTING'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True

with app.app_context():
    admin = User.query.filter_by(role='ADMIN', deleted=False, status='ACTIVE').order_by(User.user_id.asc()).first()
    admin_id = admin.user_id
    session_version = admin.session_version
    print({'admin_id': admin_id, 'admin_username': admin.username})

with app.test_request_context('/'):
    session_id = _create_identifier()

client = app.test_client()
with client.session_transaction() as sess:
    sess['_user_id'] = str(admin_id)
    sess['_fresh'] = True
    sess['_id'] = session_id
    sess['session_version'] = session_version

review_response = client.get('/admin/products/review')
print({'review_status_code': review_response.status_code})
print(review_response.get_data(as_text=True)[:300])

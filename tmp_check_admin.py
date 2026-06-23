from app import create_app
from app.models.user import User

app = create_app()
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    print({'exists': bool(admin), 'user_id': getattr(admin, 'user_id', None), 'role': getattr(admin, 'role', None), 'status': getattr(admin, 'status', None), 'session_version': getattr(admin, 'session_version', None)})

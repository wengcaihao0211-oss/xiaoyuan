from app import create_app
from app.models.user import User

app = create_app()
with app.app_context():
    users = User.query.filter_by(deleted=False).order_by(User.user_id.asc()).all()
    print([{'user_id': u.user_id, 'username': u.username, 'role': u.role, 'status': u.status} for u in users])

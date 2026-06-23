from functools import wraps
from flask import abort, flash, redirect, request, url_for
from flask_login import current_user


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if current_user.role != 'ADMIN':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def active_user_required(f):
    """Decorator to require active (non-disabled) user."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.status == 'DISABLED':
            flash('您的账号已被禁用，无法执行此操作。', 'danger')
            return redirect(url_for('browse.home'))
        return f(*args, **kwargs)
    return decorated_function


def owner_required(model_class, id_param='id'):
    """Decorator to check the current user owns the resource."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from app.extensions import db
            obj_id = kwargs.get(id_param)
            obj = db.session.get(model_class, obj_id)
            if obj is None:
                abort(404)
            seller_attr = getattr(obj, 'seller_id', None) or getattr(obj, 'user_id', None)
            if seller_attr != current_user.user_id:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

from datetime import timedelta
from time import perf_counter

from flask import Flask, jsonify, render_template, request, session
from sqlalchemy import inspect, text
from sqlalchemy.orm import selectinload
from app.config import config
from app.extensions import db, login_manager, migrate


def ensure_all_schemas():
    """Auto-add missing columns for all models on startup.

    Iterates over every SQLAlchemy model registered on db.Model,
    compares the Python columns with the actual database columns,
    and runs ALTER TABLE ADD COLUMN for any that are missing.
    This prevents 'no such column' crashes after git pull updates models.
    """
    try:
        inspector = inspect(db.engine)
        table_names = set(inspector.get_table_names())

        # Walk every model class registered on db.Model
        model_classes = [
            cls for cls in db.Model.__subclasses__()
            if hasattr(cls, '__tablename__') and cls.__tablename__ in table_names
        ]

        for model_cls in model_classes:
            table_name = model_cls.__tablename__
            db_columns = {col['name'] for col in inspector.get_columns(table_name)}
            # Collect all column names defined on the model via Column()
            from sqlalchemy import Column
            model_columns = {
                attr_name for attr_name in dir(model_cls)
                if isinstance(getattr(model_cls, attr_name, None), Column)
            }

            # Attribute-level Column objects don't include inherited mapped columns
            # (e.g. from a base mixin), so also check the mapper columns
            try:
                from sqlalchemy.orm import class_mapper
                mapper_cols = {c.key for c in class_mapper(model_cls).columns}
            except Exception:
                mapper_cols = set()

            all_model_columns = model_columns | mapper_cols

            for col_name in sorted(all_model_columns):
                if col_name in db_columns:
                    continue

                # Look up the Column object to infer a SQL type
                col_obj = getattr(model_cls, col_name, None)
                col_type = _column_sql_type(col_obj)

                statement = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
                try:
                    db.session.execute(text(statement))
                    db.session.commit()
                    import logging
                    logging.getLogger(__name__).info(
                        'Auto-migration: %s.%s (%s) added', table_name, col_name, col_type
                    )
                except Exception:
                    db.session.rollback()

        # Also run the user-specific backfill logic
        _ensure_user_schema_post_migrate(inspector)

    except Exception:
        db.session.rollback()


def _column_sql_type(col_obj):
    """Infer a sensible SQL type string from a SQLAlchemy Column for ALTER TABLE."""
    if col_obj is None:
        return 'VARCHAR(500)'
    try:
        col_type = col_obj.type
        type_str = str(col_type).upper()
        # Map common SQLA types to SQLite-compatible types
        if 'INTEGER' in type_str or 'BIGINT' in type_str:
            return 'INTEGER'
        if 'BOOLEAN' in type_str:
            return 'BOOLEAN'
        if 'FLOAT' in type_str or 'NUMERIC' in type_str or 'DECIMAL' in type_str:
            return 'FLOAT'
        if 'DATETIME' in type_str or 'TIMESTAMP' in type_str or 'DATE' in type_str:
            return 'TIMESTAMP'
        if 'JSON' in type_str:
            return 'TEXT'
        if 'TEXT' in type_str or 'CLOB' in type_str:
            return 'TEXT'
        # For VARCHAR(n), try to preserve the length
        if hasattr(col_type, 'length') and col_type.length:
            return f'VARCHAR({col_type.length})'
        return 'VARCHAR(500)'
    except Exception:
        return 'VARCHAR(500)'


def _ensure_user_schema_post_migrate(inspector):
    """Backfill user indexes and normalize legacy data."""
    try:
        if 'users' not in inspector.get_table_names():
            return

        existing_indexes = {idx['name'] for idx in inspector.get_indexes('users')}

        # Normalize legacy blank contact values before creating unique indexes
        try:
            db.session.execute(text("UPDATE users SET phone = NULL WHERE phone = ''"))
            db.session.execute(text("UPDATE users SET email = NULL WHERE email = ''"))
            db.session.commit()
        except Exception:
            db.session.rollback()

        if 'password_changed_at' in {c['name'] for c in inspector.get_columns('users')}:
            try:
                db.session.execute(text(
                    "UPDATE users SET password_changed_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) "
                    "WHERE password_changed_at IS NULL"
                ))
                db.session.commit()
            except Exception:
                db.session.rollback()

        if 'session_version' in {c['name'] for c in inspector.get_columns('users')}:
            try:
                db.session.execute(text(
                    "UPDATE users SET session_version = 1 WHERE session_version IS NULL"
                ))
                db.session.commit()
            except Exception:
                db.session.rollback()

        # Create conditional unique indexes (SQLite 3.35+)
        if 'uq_users_phone_active' not in existing_indexes:
            try:
                db.session.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_phone_active "
                    "ON users (phone) WHERE phone IS NOT NULL AND phone <> '' AND deleted = FALSE"
                ))
                db.session.commit()
            except Exception:
                db.session.rollback()

        if 'uq_users_email_active' not in existing_indexes:
            try:
                db.session.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_active "
                    "ON users (email) WHERE email IS NOT NULL AND email <> '' AND deleted = FALSE"
                ))
                db.session.commit()
            except Exception:
                db.session.rollback()

    except Exception:
        db.session.rollback()


def create_app(config_name='default'):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['SESSION_REFRESH_EACH_REQUEST'] = True

    if config_name != 'testing' and not app.config.get('SQLALCHEMY_DATABASE_URI'):
        raise RuntimeError(
            'Missing DATABASE_URL or SUPABASE_DB_URL. '
            'Set your Supabase Postgres connection string before starting the app. '
            'For temporary local fallback only, set ALLOW_SQLITE_DEV=1.'
        )

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Auto-migrate missing columns on every startup (safe idempotent)
    if config_name != 'testing':
        with app.app_context():
            ensure_all_schemas()

    @app.before_request
    def refresh_authenticated_session():
        from flask_login import current_user
        if current_user.is_authenticated:
            session_version = session.get('session_version')
            if session_version != current_user.session_version:
                from flask import flash, redirect, url_for
                from flask_login import logout_user
                session.pop('session_version', None)
                logout_user()
                flash('密码已更新，请重新登录。', 'warning')
                return redirect(url_for('auth.login'))
            session.permanent = True
            session['session_version'] = current_user.session_version
            session.modified = True

    # Health check (no DB needed)
    @app.route('/ping')
    def ping():
        return 'pong'

    @app.route('/db-test')
    def db_test():
        try:
            from app.models.category import Category
            count = Category.query.count()
            return f'DB OK: {count} categories'
        except Exception as e:
            return f'DB Error: {str(e)}'

    @app.route('/home-diagnostic')
    def home_diagnostic():
        available_stages = [
            'database', 'schema', 'products', 'images', 'template'
        ]
        stage = request.args.get('stage')
        if not stage:
            return jsonify({'available_stages': available_stages})
        if stage not in available_stages:
            return jsonify({
                'ok': False,
                'stage': stage,
                'error_type': 'UnknownStage',
            }), 400

        started = perf_counter()
        try:
            from app.models.category import Category
            from app.models.product import Product
            from app.models.product_image import ProductImage

            if stage == 'database':
                result = {'value': db.session.execute(text('SELECT 1')).scalar()}
            elif stage == 'schema':
                table_names = set(inspect(db.engine).get_table_names())
                expected = {
                    'category', 'product', 'product_image', 'users'
                }
                result = {
                    'present': sorted(expected & table_names),
                    'missing': sorted(expected - table_names),
                }
            elif stage == 'products':
                result = {
                    'total': Product.query.count(),
                    'on_sale': Product.on_sale().count(),
                }
            elif stage == 'images':
                result = {'total': ProductImage.query.count()}
            else:
                newest = Product.on_sale().options(
                    selectinload(Product.images)
                ).order_by(Product.created_at.desc()).limit(12).all()
                hottest = Product.on_sale().options(
                    selectinload(Product.images)
                ).order_by(Product.view_count.desc()).limit(12).all()
                rendered = render_template(
                    'browse/home.html',
                    newest_products=newest,
                    hot_products=hottest,
                )
                result = {
                    'categories': Category.enabled().count(),
                    'newest': len(newest),
                    'hottest': len(hottest),
                    'rendered_chars': len(rendered),
                }

            return jsonify({
                'ok': True,
                'stage': stage,
                'elapsed_ms': round((perf_counter() - started) * 1000, 1),
                'result': result,
            })
        except Exception as error:
            db.session.rollback()
            app.logger.exception('Homepage diagnostic failed at %s', stage)
            return jsonify({
                'ok': False,
                'stage': stage,
                'elapsed_ms': round((perf_counter() - started) * 1000, 1),
                'error_type': type(error).__name__,
                'error_category': (
                    'database'
                    if error.__class__.__module__.startswith('sqlalchemy')
                    else 'application'
                ),
            })

    # Register blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.user import user_bp
    from app.blueprints.product import product_bp
    from app.blueprints.browse import browse_bp
    from app.blueprints.order import order_bp
    from app.blueprints.social import social_bp
    from app.blueprints.notification import notification_bp
    from app.blueprints.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(product_bp, url_prefix='/product')
    app.register_blueprint(browse_bp)
    app.register_blueprint(order_bp, url_prefix='/order')
    app.register_blueprint(social_bp, url_prefix='/social')
    app.register_blueprint(notification_bp, url_prefix='/notifications')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # User loader for Flask-Login
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(413)
    def too_large(e):
        from flask import flash, redirect, request
        flash('上传文件过大，单个文件最大 5MB。', 'danger')
        return redirect(request.url)

    # Template filters
    @app.template_filter('beijing_time')
    def beijing_time(value):
        """将UTC时间转换为北京时间并格式化显示。"""
        from app.utils.helpers import utc_to_beijing
        if not value:
            return ''
        beijing_dt = utc_to_beijing(value)
        return beijing_dt.strftime('%Y-%m-%d %H:%M')
    
    @app.template_filter('beijing_hm')
    def beijing_hm(value):
        """将UTC时间转换为北京时间并只显示小时:分钟。"""
        from app.utils.helpers import utc_to_beijing
        if not value:
            return ''
        beijing_dt = utc_to_beijing(value)
        return beijing_dt.strftime('%H:%M')

    # Context processors
    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from app.services import order_service
        categories_cache = None

        def get_categories():
            nonlocal categories_cache
            if categories_cache is not None:
                return categories_cache
            from app.models.category import Category
            try:
                categories_cache = Category.enabled().order_by(
                    Category.category_name
                ).all()
            except Exception:
                db.session.rollback()
                categories_cache = []
            return categories_cache

        ctx = {
            'current_user': current_user,
            'get_categories': get_categories,
            'order_service': order_service,
        }
        if current_user.is_authenticated:
            try:
                from app.services.notification_service import get_unread_count
                unread = get_unread_count(current_user.user_id)
                ctx['unread_notification_count'] = unread
            except Exception:
                db.session.rollback()
                ctx['unread_notification_count'] = 0
            
            try:
                from app.services import message_service
                unread_msg = message_service.get_unread_count(current_user.user_id)
                ctx['unread_message_count'] = unread_msg
            except Exception:
                db.session.rollback()
                ctx['unread_message_count'] = 0
            
            try:
                from app.models.favorite import Favorite
                favorite_count = Favorite.query.filter_by(
                    user_id=current_user.user_id
                ).count()
                ctx['favorite_count'] = favorite_count
            except Exception:
                db.session.rollback()
                ctx['favorite_count'] = 0
        else:
            ctx['unread_notification_count'] = 0
            ctx['unread_message_count'] = 0
            ctx['favorite_count'] = 0
        return ctx

    return app

from time import perf_counter

from flask import Flask, jsonify, render_template, request
from sqlalchemy import inspect, text
from sqlalchemy.orm import selectinload
from app.config import config
from app.extensions import db, login_manager, migrate


def create_app(config_name='default'):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

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

    # Context processors
    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        ctx = {'current_user': current_user}
        try:
            from app.models.category import Category
            ctx['get_categories'] = lambda: Category.enabled().order_by(Category.category_name).all()
        except Exception:
            ctx['get_categories'] = lambda: []
        if current_user.is_authenticated:
            try:
                from app.models.notification import Notification
                unread = Notification.query.filter_by(
                    receiver_id=current_user.user_id, read_status=0, deleted=0
                ).count()
                ctx['unread_notification_count'] = unread
            except Exception:
                ctx['unread_notification_count'] = 0
        else:
            ctx['unread_notification_count'] = 0
        return ctx

    return app

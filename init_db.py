"""Initialize the database with tables and seed data."""
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.category import Category

app = create_app()

with app.app_context():
    print(f'[INFO] Database backend: {db.engine.url.drivername}')

    # Create all tables
    db.create_all()
    print('[OK] All tables created.')

    # Seed categories
    categories = [
        ('教材教辅', '课本、参考书、考试资料等'),
        ('电子产品', '手机、电脑、平板、配件等'),
        ('生活用品', '日用品、收纳、装饰等'),
        ('服饰鞋包', '衣服、鞋子、包包、配饰等'),
        ('运动户外', '运动器材、户外装备等'),
        ('娱乐数码', '游戏、耳机、相机等'),
        ('其他', '其他闲置物品'),
    ]
    for name, desc in categories:
        if not Category.query.filter_by(category_name=name).first():
            db.session.add(Category(category_name=name, description=desc))
    db.session.commit()
    print(f'[OK] {len(categories)} categories seeded.')

    # Create admin user if not exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            role='ADMIN',
            status='ACTIVE',
            phone='13800000000',
            email='admin@example.com',
            nickname='系统管理员',
            introduction='系统管理员'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('[OK] Admin user created (username: admin, password: admin123)')
    else:
        print('[OK] Admin user already exists.')

    # Create test user if not exists
    test_user = User.query.filter_by(username='testuser').first()
    if not test_user:
        test_user = User(
            username='testuser',
            role='USER',
            status='ACTIVE',
            phone='13900000001',
            email='testuser@example.com',
            nickname='测试用户',
            introduction='test user'
        )
        test_user.set_password('test123')
        db.session.add(test_user)
        db.session.commit()
        print('[OK] Test user created (username: testuser, password: test123)')
    else:
        print('[OK] Test user already exists.')

    print('\nDatabase initialization complete!')
    print('   Admin login: admin / admin123')
    print('   User login:  testuser / test123')

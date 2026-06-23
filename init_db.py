"""Initialize the database with tables and seed data."""
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.category import Category

app = create_app()

with app.app_context():
    print(f'[INFO] Database backend: {db.engine.url.drivername}')

    # Create tables if not exist, then auto-migrate missing columns
    db.create_all()
    from app import ensure_all_schemas
    ensure_all_schemas()
    print('[OK] All tables created / migrated.')

    # Seed categories
    categories = [
        # 1. 教材学习
        ('教材学习', '教材、参考书、考试资料、笔记、文具等'),
        # 2. 数码电子
        ('数码电子', '手机、电脑、平板、耳机、相机、游戏机等'),
        # 3. 服饰鞋包
        ('服饰鞋包', '衣服、鞋子、包包、配饰、帽子、围巾等'),
        # 4. 生活用品
        ('生活用品', '日用品、宿舍神器、收纳、装饰、护肤品等'),
        # 5. 运动户外
        ('运动户外', '运动器材、健身装备、户外用品、运动鞋服等'),
        # 6. 图书娱乐
        ('图书娱乐', '小说、漫画、桌游、玩具、乐器等'),
        # 7. 美妆个护
        ('美妆个护', '护肤品、化妆品、洗护用品、香水等'),
        # 8. 家居装饰
        ('家居装饰', '摆件、装饰画、收纳、台灯、软装等'),
        # 9. 交通出行
        ('交通出行', '自行车、电动车、滑板、平衡车、配件等'),
        # 10. 其他闲置
        ('其他闲置', '不在以上分类中的物品'),
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

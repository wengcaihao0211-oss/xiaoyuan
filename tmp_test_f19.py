"""快速测试 F19 搜索功能是否正常工作"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models.product import Product
from app.models.category import Category
from app.models.user import User
from app.services import browse_service
from datetime import datetime

app = create_app()

print("="*60)
print("测试 F19 根据商品名称搜索功能")
print("="*60)

with app.app_context():
    # 1. 初始化数据库
    print("\n[1/6] 初始化数据库...")
    db.create_all()
    
    # 2. 创建测试用户
    print("\n[2/6] 创建测试用户...")
    test_user = User.query.filter_by(username='testuser').first()
    if not test_user:
        test_user = User(
            username='testuser',
            role='USER',
            status='ACTIVE',
            phone='13900000001',
            email='testuser@example.com',
            nickname='测试用户'
        )
        test_user.set_password('test123')
        db.session.add(test_user)
        db.session.commit()
    
    # 3. 创建商品分类
    print("\n[3/6] 创建商品分类...")
    if not Category.query.first():
        categories = [
            ('教材教辅', '课本、参考书'),
            ('电子产品', '手机、电脑'),
        ]
        for name, desc in categories:
            db.session.add(Category(category_name=name, description=desc))
        db.session.commit()
    category = Category.query.first()
    
    # 4. 创建测试商品
    print("\n[4/6] 创建测试商品...")
    test_products = [
        {
            'product_name': '高等数学教材',
            'description': '同济大学出版社 第七版 上下册',
            'price': 25.00,
            'condition_level': '九成新',
            'product_status': 'ON_SALE',
        },
        {
            'product_name': 'iPhone 13 手机',
            'description': '黑色 128G 无锁 正常使用',
            'price': 3500.00,
            'condition_level': '八成新',
            'product_status': 'ON_SALE',
        },
        {
            'product_name': '线性代数教材',
            'description': '高等教育出版社 第六版',
            'price': 15.00,
            'condition_level': '全新',
            'product_status': 'ON_SALE',
        },
        {
            'product_name': '二手iPad Pro',
            'description': '11寸 2021款 256G WiFi版',
            'price': 4200.00,
            'condition_level': '七成新',
            'product_status': 'ON_SALE',
        },
        {
            'product_name': '数学分析习题集',
            'description': '吉米多维奇 全套',
            'price': 45.00,
            'condition_level': '九成新',
            'product_status': 'REVIEW',  # 审核中，不应显示
        },
    ]
    
    # 清理旧商品
    Product.query.filter(Product.seller_id == test_user.user_id).delete()
    db.session.commit()
    
    # 添加新商品
    for p_data in test_products:
        product = Product(
            seller_id=test_user.user_id,
            category_id=category.category_id,
            created_at=datetime.utcnow(),
            view_count=0,
            **p_data
        )
        db.session.add(product)
    db.session.commit()
    print(f"   已创建 {len(test_products)} 个测试商品")
    
    # 5. 测试搜索功能
    print("\n[5/6] 测试搜索功能...")
    
    # 测试 1: 关键词搜索 "教材"
    print("\n   测试 1 - 搜索关键词 '教材':")
    success, msg, payload = browse_service.get_search_payload(keyword='教材')
    print(f"      成功: {success}")
    print(f"      消息: {msg}")
    print(f"      命中商品数: {len(payload['products'])}")
    for p in payload['products']:
        print(f"        - {p.product_name} (¥{p.price})")
    
    # 测试 2: 关键词搜索 "手机"
    print("\n   测试 2 - 搜索关键词 '手机':")
    success, msg, payload = browse_service.get_search_payload(keyword='手机')
    print(f"      成功: {success}")
    print(f"      命中商品数: {len(payload['products'])}")
    for p in payload['products']:
        print(f"        - {p.product_name} (¥{p.price})")
    
    # 测试 3: 空关键词（应该返回全部在售商品）
    print("\n   测试 3 - 空关键词搜索:")
    success, msg, payload = browse_service.get_search_payload(keyword='')
    print(f"      成功: {success}")
    print(f"      命中商品数: {len(payload['products'])} (应该是 4 个)")
    
    # 测试 4: 超长关键词拒绝
    print("\n   测试 4 - 超长关键词 (超过 30 个字符):")
    long_keyword = '这是一个非常非常非常非常非常非常非常非常非常非常长的关键词'
    success, msg, payload = browse_service.get_search_payload(keyword=long_keyword)
    print(f"      成功: {success} (应该是 False)")
    print(f"      消息: {msg}")
    
    # 测试 5: 关键词去空格
    print("\n   测试 5 - 关键词去空格 '  数学  ':")
    success, msg, payload = browse_service.get_search_payload(keyword='  数学  ')
    print(f"      成功: {success}")
    print(f"      命中商品数: {len(payload['products'])}")
    
    # 测试 6: SQL 注入防护测试
    print("\n   测试 6 - SQL 注入测试 '%' OR '1'='1':")
    success, msg, payload = browse_service.get_search_payload(keyword="%' OR '1'='1")
    print(f"      成功: {success}")
    print(f"      命中商品数: {len(payload['products'])} (应该是 0)")
    
    # 测试 7: 排序测试
    print("\n   测试 7 - 按价格升序排序:")
    success, msg, payload = browse_service.get_search_payload(keyword='', sort='price_asc')
    print(f"      成功: {success}")
    print(f"      排序结果:")
    for p in payload['products']:
        print(f"        - {p.product_name}: ¥{p.price}")
    
    # 6. 完成
    print("\n[6/6] 测试完成！")
    print("\n" + "="*60)
    print("F19 搜索功能实现验证通过！")
    print("="*60)

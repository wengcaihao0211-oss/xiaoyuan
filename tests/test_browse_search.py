from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.services import browse_service


def create_test_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    return app


def make_user(username="search_user"):
    user = User(
        username=username,
        phone=None,
        email=f"{username}@example.com",
        role="USER",
        status="ACTIVE",
    )
    user.set_password("abc12345")
    return user


def make_product(seller_id, category_id, name, price, description, status="ON_SALE"):
    return Product(
        seller_id=seller_id,
        category_id=category_id,
        product_name=name,
        price=Decimal(price),
        condition_level="九成新",
        description=description,
        trade_location="校园交易点",
        product_status=status,
    )


def reset_search_cache():
    browse_service._search_cache.clear()
    browse_service._search_keyword_counter.clear()


def test_search_matches_name_and_description_and_trims_keyword():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        reset_search_cache()
        seller = make_user()
        category = Category(category_name="数码", status="ENABLED")
        db.session.add_all([seller, category])
        db.session.flush()
        db.session.add(make_product(seller.user_id, category.category_id, "蓝牙耳机", "99.00", "降噪耳机"))
        db.session.add(make_product(seller.user_id, category.category_id, "二手音箱", "88.00", "适合宿舍使用的耳机替代品"))
        db.session.add(make_product(seller.user_id, category.category_id, "耳机审核中", "77.00", "待审核商品", status="PENDING_REVIEW"))
        db.session.commit()

    response = client.get("/search?q=%20耳机%20")

    assert response.status_code == 200
    assert "蓝牙耳机".encode("utf-8") in response.data
    assert "二手音箱".encode("utf-8") in response.data
    assert "耳机审核中".encode("utf-8") not in response.data
    assert "共 2 个结果".encode("utf-8") in response.data


def test_search_empty_keyword_returns_all_on_sale_products():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        reset_search_cache()
        seller = make_user("all_user")
        category = Category(category_name="教材", status="ENABLED")
        db.session.add_all([seller, category])
        db.session.flush()
        db.session.add(make_product(seller.user_id, category.category_id, "高数课本", "20.00", "教材"))
        db.session.add(make_product(seller.user_id, category.category_id, "英语词典", "30.00", "词典"))
        db.session.add(make_product(seller.user_id, category.category_id, "草稿商品", "10.00", "不公开", status="DRAFT"))
        db.session.commit()

    response = client.get("/search")

    assert response.status_code == 200
    assert "高数课本".encode("utf-8") in response.data
    assert "英语词典".encode("utf-8") in response.data
    assert "草稿商品".encode("utf-8") not in response.data
    assert "共 2 个结果".encode("utf-8") in response.data


def test_search_rejects_too_long_keyword():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        reset_search_cache()

    response = client.get("/search?q=" + ("a" * 31), follow_redirects=True)

    assert response.status_code == 200
    assert "关键词长度需为 1~30 字".encode("utf-8") in response.data
    assert "没有找到相关商品".encode("utf-8") in response.data


def test_search_escapes_sql_wildcards_and_keeps_query_semantics():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        reset_search_cache()
        seller = make_user("special_user")
        category = Category(category_name="配件", status="ENABLED")
        db.session.add_all([seller, category])
        db.session.flush()
        db.session.add(make_product(seller.user_id, category.category_id, "字符测试%_", "40.00", "带特殊字符"))
        db.session.add(make_product(seller.user_id, category.category_id, "普通商品A", "50.00", "普通说明"))
        db.session.commit()

    response = client.get("/search?q=%25_")

    assert response.status_code == 200
    assert "字符测试%_".encode("utf-8") in response.data
    assert "普通商品A".encode("utf-8") not in response.data
    assert "共 1 个结果".encode("utf-8") in response.data


def test_search_supports_pagination_and_sorting():
    app = create_test_app()

    with app.app_context():
        reset_search_cache()
        seller = make_user("page_sort_user")
        category = Category(category_name="电子产品", status="ENABLED")
        db.session.add_all([seller, category])
        db.session.flush()
        for index in range(13):
            db.session.add(
                make_product(
                    seller.user_id,
                    category.category_id,
                    f"手机{index}",
                    f"{10 + index}.00",
                    "手机搜索测试描述",
                )
            )
        db.session.commit()

        asc_ok, _, asc_payload = browse_service.get_search_payload(keyword="手机", sort="price_asc", page=1)
        asc_page_2_ok, _, asc_page_2_payload = browse_service.get_search_payload(keyword="手机", sort="price_asc", page=2)
        desc_ok, _, desc_payload = browse_service.get_search_payload(keyword="手机", sort="price_desc", page=1)

    assert asc_ok is True
    assert desc_ok is True
    assert asc_page_2_ok is True
    assert asc_payload["total_count"] == 13
    assert [product.product_name for product in asc_payload["products"][:3]] == ["手机0", "手机1", "手机2"]
    assert len(asc_page_2_payload["products"]) == 1
    assert asc_page_2_payload["products"][0].product_name == "手机12"
    assert [product.product_name for product in desc_payload["products"][:3]] == ["手机12", "手机11", "手机10"]


def test_hot_keyword_search_can_be_cached():
    app = create_test_app()

    with app.app_context():
        reset_search_cache()
        seller = make_user("cache_user")
        category = Category(category_name="缓存分类", status="ENABLED")
        db.session.add_all([seller, category])
        db.session.flush()
        db.session.add(make_product(seller.user_id, category.category_id, "缓存商品", "66.00", "缓存测试商品"))
        db.session.commit()

        for _ in range(3):
            success, _, payload = browse_service.get_search_payload(keyword="缓存", sort="latest", page=1)
            assert success is True
            assert payload["total_count"] == 1

        assert ("缓存", "latest", 1, app.config["ITEMS_PER_PAGE"], None, None, "") in browse_service._search_cache

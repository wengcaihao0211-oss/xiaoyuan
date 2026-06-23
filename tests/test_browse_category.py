from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models.category import Category
from app.models.product import Product
from app.models.user import User


def create_test_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    return app


def make_user(username="browse_user"):
    user = User(
        username=username,
        phone=None,
        email=f"{username}@example.com",
        role="USER",
        status="ACTIVE",
    )
    user.set_password("abc12345")
    return user


def make_product(seller_id, category_id, name, price, status="ON_SALE"):
    return Product(
        seller_id=seller_id,
        category_id=category_id,
        product_name=name,
        price=Decimal(price),
        condition_level="九成新",
        description=f"{name} 的商品描述内容足够长。",
        trade_location="校园交易点",
        product_status=status,
    )


def test_category_browse_only_returns_target_category_products_and_accurate_total():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        seller = make_user()
        target_category = Category(category_name="数码", status="ENABLED")
        other_category = Category(category_name="教材", status="ENABLED")
        db.session.add_all([seller, target_category, other_category])
        db.session.flush()

        for index in range(21):
            db.session.add(
                make_product(
                    seller.user_id,
                    target_category.category_id,
                    f"目标商品{index}",
                    f"{20 + index}.00",
                )
            )

        db.session.add(
            make_product(
                seller.user_id,
                other_category.category_id,
                "其他分类商品",
                "99.00",
            )
        )
        db.session.add(
            make_product(
                seller.user_id,
                target_category.category_id,
                "待审核商品",
                "88.00",
                status="PENDING_REVIEW",
            )
        )
        db.session.commit()
        category_id = target_category.category_id

    first_page = client.get(f"/category/{category_id}")
    second_page = client.get(f"/category/{category_id}?page=2")
    first_page_html = first_page.get_data(as_text=True)
    second_page_html = second_page.get_data(as_text=True)

    assert first_page.status_code == 200
    assert "共 21 个在售商品".encode("utf-8") in first_page.data
    assert "其他分类商品".encode("utf-8") not in first_page.data
    assert "待审核商品".encode("utf-8") not in first_page.data
    assert first_page_html.count("目标商品") == 20

    assert second_page.status_code == 200
    assert second_page_html.count("目标商品") == 1


def test_category_browse_supports_latest_and_price_sorting():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        seller = make_user("sort_user")
        category = Category(category_name="电子产品", status="ENABLED")
        db.session.add_all([seller, category])
        db.session.flush()

        db.session.add(make_product(seller.user_id, category.category_id, "低价商品", "10.00"))
        db.session.add(make_product(seller.user_id, category.category_id, "中价商品", "20.00"))
        db.session.add(make_product(seller.user_id, category.category_id, "高价商品", "30.00"))
        db.session.commit()
        category_id = category.category_id

    latest_html = client.get(f"/category/{category_id}?sort=latest").get_data(as_text=True)
    asc_html = client.get(f"/category/{category_id}?sort=price_asc").get_data(as_text=True)
    desc_html = client.get(f"/category/{category_id}?sort=price_desc").get_data(as_text=True)

    assert latest_html.find("高价商品") < latest_html.find("中价商品") < latest_html.find("低价商品")
    assert asc_html.find("低价商品") < asc_html.find("中价商品") < asc_html.find("高价商品")
    assert desc_html.find("高价商品") < desc_html.find("中价商品") < desc_html.find("低价商品")


def test_category_browse_invalid_or_disabled_category_returns_warning():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        seller = make_user("disabled_user")
        disabled_category = Category(category_name="停用分类", status="DISABLED")
        db.session.add_all([seller, disabled_category])
        db.session.commit()
        disabled_id = disabled_category.category_id

    missing = client.get("/category/9999", follow_redirects=True)
    disabled = client.get(f"/category/{disabled_id}", follow_redirects=True)

    assert missing.status_code == 200
    assert "分类不存在或已禁用".encode("utf-8") in missing.data
    assert disabled.status_code == 200
    assert "分类不存在或已禁用".encode("utf-8") in disabled.data


def test_category_browse_out_of_range_page_returns_empty_page():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        seller = make_user("page_user")
        category = Category(category_name="生活用品", status="ENABLED")
        db.session.add_all([seller, category])
        db.session.flush()
        db.session.add(make_product(seller.user_id, category.category_id, "页码测试商品", "15.00"))
        db.session.commit()
        category_id = category.category_id

    response = client.get(f"/category/{category_id}?page=99")

    assert response.status_code == 200
    assert "共 1 个在售商品".encode("utf-8") in response.data
    assert "当前页没有商品，请尝试返回上一页".encode("utf-8") in response.data
    assert "页码测试商品".encode("utf-8") not in response.data

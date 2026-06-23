import io
import re
from decimal import Decimal

from PIL import Image
from werkzeug.datastructures import FileStorage

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


def make_user(username="seller_user", password="abc12345"):
    user = User(
        username=username,
        phone="13812341000",
        email=f"{username}@example.com",
        nickname="卖家",
        role="USER",
        status="ACTIVE",
    )
    user.set_password(password)
    return user


def make_category(name="数码", status="ENABLED"):
    return Category(category_name=name, description="desc", status=status)


def make_image_upload(filename="test.png", color=(255, 0, 0)):
    bio = io.BytesIO()
    image = Image.new("RGB", (40, 40), color)
    image.save(bio, format="PNG")
    bio.seek(0)
    return FileStorage(stream=bio, filename=filename, content_type="image/png")


def extract_submission_token(html):
    match = re.search(r'name="submission_token"[^>]*value="([^"]+)"', html)
    assert match, html
    return match.group(1)


def login(client, identifier="seller_user", password="abc12345"):
    return client.post(
        "/auth/login",
        data={"username": identifier, "password": password},
        follow_redirects=False,
    )


def publish_payload(category_id, token, name="待审核商品"):
    return {
        "product_name": name,
        "category_id": category_id,
        "price": "99.99",
        "condition_level": "九成新",
        "description": "这是一个满足长度要求的商品描述内容。",
        "trade_location": "一食堂门口",
        "submission_token": token,
        "submit_publish": "提交审核",
    }


def test_publish_review_product_creates_pending_review_and_hidden_from_public_list():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        db.session.add(make_user())
        db.session.add(make_category())
        db.session.commit()
        category_id = Category.query.filter_by(category_name="数码").first().category_id

    assert login(client).status_code == 302
    token = extract_submission_token(client.get("/product/publish").get_data(as_text=True))

    created = client.post(
        "/product/publish",
        data={
            **publish_payload(category_id, token),
            "images": [(make_image_upload().stream, "test.png")],
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert created.status_code == 302

    with app.app_context():
        product = Product.query.filter_by(product_name="待审核商品").first()
        assert product is not None
        assert product.product_id is not None
        assert product.product_status == "PENDING_REVIEW"
        assert product.seller.username == "seller_user"
        assert len(product.images) == 1
        product_id = product.product_id

    home = app.test_client().get("/", follow_redirects=True)
    assert "待审核商品".encode("utf-8") not in home.data

    detail = app.test_client().get(f"/product/{product_id}", follow_redirects=False)
    assert detail.status_code == 302


def test_duplicate_publish_submission_with_same_token_only_creates_one_product():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        db.session.add(make_user())
        db.session.add(make_category())
        db.session.commit()
        category_id = Category.query.filter_by(category_name="数码").first().category_id

    assert login(client).status_code == 302
    token = extract_submission_token(client.get("/product/publish").get_data(as_text=True))

    draft_payload = {
        "product_name": "唯一草稿",
        "category_id": category_id,
        "price": "19.90",
        "condition_level": "八成新",
        "description": "这是一个不会重复创建的草稿商品描述。",
        "trade_location": "宿舍楼下",
        "submission_token": token,
        "submit_draft": "保存草稿",
    }
    first = client.post("/product/publish", data=draft_payload, follow_redirects=False)
    second = client.post("/product/publish", data=draft_payload, follow_redirects=True)

    assert first.status_code == 302
    assert second.status_code == 200
    assert "请勿重复提交商品".encode("utf-8") in second.data

    with app.app_context():
        assert Product.query.filter_by(product_name="唯一草稿").count() == 1


def test_publish_rejects_disabled_category_and_missing_images_for_review():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        db.session.add(make_user())
        disabled_category = make_category(status="DISABLED")
        enabled_category = make_category(name="教材", status="ENABLED")
        db.session.add(disabled_category)
        db.session.add(enabled_category)
        db.session.commit()
        disabled_id = disabled_category.category_id
        enabled_id = enabled_category.category_id

        from app.services import product_service

        success, message, _ = product_service.create_product(
            seller_id=1,
            name="停用分类商品",
            category_id=disabled_id,
            price=Decimal("99.99"),
            condition_level="九成新",
            description="这是一个满足长度要求的商品描述内容。",
            trade_location="一食堂门口",
            images=[make_image_upload()],
            submit=True,
        )
        assert success is False
        assert "商品分类不存在或已停用" in message

    assert login(client).status_code == 302
    token = extract_submission_token(client.get("/product/publish").get_data(as_text=True))

    token2 = extract_submission_token(client.get("/product/publish").get_data(as_text=True))
    no_image_response = client.post(
        "/product/publish",
        data=publish_payload(enabled_id, token2, name="无图商品"),
        follow_redirects=True,
    )
    assert no_image_response.status_code == 200
    assert "提交审核至少需要上传 1 张商品图片".encode("utf-8") in no_image_response.data


def test_publish_rejects_invalid_image_file():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        db.session.add(make_user())
        db.session.add(make_category())
        db.session.commit()
        category_id = Category.query.filter_by(category_name="数码").first().category_id

    assert login(client).status_code == 302
    token = extract_submission_token(client.get("/product/publish").get_data(as_text=True))

    invalid = client.post(
        "/product/publish",
        data={
            **publish_payload(category_id, token, name="非法图片商品"),
            "images": [(io.BytesIO(b"fake-image"), "bad.png", "image/png")],
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert invalid.status_code == 200
    assert "上传文件不是有效的图片".encode("utf-8") in invalid.data

    with app.app_context():
        assert Product.query.filter_by(product_name="非法图片商品").count() == 0


def test_edit_product_keeps_image_order_and_delete_after_refresh():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        seller = make_user()
        category = make_category()
        db.session.add(seller)
        db.session.add(category)
        db.session.commit()

        from app.services import product_service

        success, _, product = product_service.create_product(
            seller_id=seller.user_id,
            name="图片排序商品",
            category_id=category.category_id,
            price=Decimal("20.00"),
            condition_level="九成新",
            description="这是一个用于测试图片排序删除的商品描述。",
            trade_location="操场门口",
            images=[
                make_image_upload("a.png", (255, 0, 0)),
                make_image_upload("b.png", (0, 255, 0)),
                make_image_upload("c.png", (0, 0, 255)),
            ],
            submit=False,
        )
        assert success is True
        product_id = product.product_id
        image_ids = [image.image_id for image in product.images]
        category_id = category.category_id

    assert login(client).status_code == 302
    response = client.post(
        f"/product/edit/{product_id}",
        data={
            "product_name": "图片排序商品",
            "category_id": category_id,
            "price": "20.00",
            "condition_level": "九成新",
            "description": "这是一个用于测试图片排序删除的商品描述。",
            "trade_location": "操场门口",
            f"image_order_{image_ids[0]}": "1",
            f"image_order_{image_ids[1]}": "0",
            f"image_order_{image_ids[2]}": "2",
            "delete_image_ids": str(image_ids[2]),
            "submit_draft": "保存草稿",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        product = db.session.get(Product, product_id)
        assert len(product.images) == 2
        assert product.images[0].image_id == image_ids[1]
        assert product.images[0].sort_order == 0
        assert product.images[1].image_id == image_ids[0]
        assert product.images[1].sort_order == 1
        assert product.cover_image == product.images[0].image_url

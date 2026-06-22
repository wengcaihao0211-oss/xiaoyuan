from sqlalchemy import event

from app import create_app
from app.extensions import db
from app.models.category import Category
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.user import User


def test_homepage_query_count_stays_bounded_with_multiple_products():
    app = create_app("testing")

    with app.app_context():
        db.create_all()

        seller = User(
            username="seller",
            password_hash="unused",
            role="USER",
            status="ACTIVE",
        )
        category = Category(category_name="Books", status="ENABLED")
        db.session.add_all([seller, category])
        db.session.flush()

        for index in range(6):
            product = Product(
                seller_id=seller.user_id,
                category_id=category.category_id,
                product_name=f"Book {index}",
                price=10 + index,
                condition_level="NEW",
                description="A useful second-hand book",
                trade_location="Campus",
                product_status="ON_SALE",
                view_count=index,
            )
            db.session.add(product)
            db.session.flush()
            db.session.add(
                ProductImage(
                    product_id=product.product_id,
                    image_url=f"uploads/products/book-{index}.png",
                    sort_order=0,
                )
            )

        db.session.commit()

        statements = []

        def record_statement(*args):
            statements.append(args[2])

        event.listen(db.engine, "before_cursor_execute", record_statement)
        try:
            response = app.test_client().get("/")
        finally:
            event.remove(db.engine, "before_cursor_execute", record_statement)

        assert response.status_code == 200
        assert len(statements) <= 3, statements


def test_homepage_degrades_to_empty_state_when_product_query_fails():
    app = create_app("testing")

    with app.app_context():
        Category.__table__.create(db.engine)
        db.session.add(Category(category_name="Books", status="ENABLED"))
        db.session.commit()

    response = app.test_client().get("/")

    assert response.status_code == 200

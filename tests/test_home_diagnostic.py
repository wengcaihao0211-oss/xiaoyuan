from app import create_app
from app.extensions import db
from app.models.category import Category


def test_home_diagnostic_reports_each_stage_without_exposing_secrets():
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        db.session.add(Category(category_name="Books", status="ENABLED"))
        db.session.commit()

    client = app.test_client()

    overview = client.get("/home-diagnostic")
    assert overview.status_code == 200
    assert overview.get_json()["available_stages"] == [
        "database",
        "schema",
        "products",
        "images",
        "template",
    ]

    for stage in overview.get_json()["available_stages"]:
        response = client.get(f"/home-diagnostic?stage={stage}")
        payload = response.get_json()

        assert response.status_code == 200
        assert payload["stage"] == stage
        assert payload["ok"] is True
        assert "DATABASE_URL" not in response.get_data(as_text=True)
        assert "postgresql://" not in response.get_data(as_text=True)

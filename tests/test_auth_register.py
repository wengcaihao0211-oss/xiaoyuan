import re

from app import create_app
from app.extensions import db
from app.models.user import User
from app.services import auth_service


def create_test_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    return app


def extract_otp(message):
    match = re.search(r'(\d{6})', message)
    assert match, message
    return match.group(1)


def test_register_creates_single_user_with_hashed_password_and_redirects_to_login():
    app = create_test_app()

    with app.app_context():
        success, message = auth_service.send_register_otp(phone="13812345678")
        assert success is True
        otp = extract_otp(message)

    response = app.test_client().post(
        "/auth/register",
        data={
            "username": "user_1001",
            "password": "abc12345",
            "confirm_password": "abc12345",
            "phone": "13812345678",
            "email": "",
            "nickname": "测试昵称",
            "otp": otp,
            "action": "register",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")

    with app.app_context():
        users = User.query.filter_by(username="user_1001").all()
        assert len(users) == 1
        assert users[0].password_hash != "abc12345"
        assert users[0].check_password("abc12345") is True
        assert users[0].role == "USER"
        assert users[0].status == "ACTIVE"
        assert users[0].created_at is not None


def test_register_rejects_duplicate_username():
    app = create_test_app()

    with app.app_context():
        existing = User(
            username="dup_user",
            phone="13800000001",
            email="dup1@example.com",
            role="USER",
            status="ACTIVE",
        )
        existing.set_password("abc12345")
        db.session.add(existing)
        db.session.commit()

        success, message = auth_service.send_register_otp(phone="13812345679")
        assert success is True
        otp = extract_otp(message)

    response = app.test_client().post(
        "/auth/register",
        data={
            "username": "dup_user",
            "password": "abc12345",
            "confirm_password": "abc12345",
            "phone": "13812345679",
            "email": "",
            "nickname": "",
            "otp": otp,
            "action": "register",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "用户名已被注册".encode("utf-8") in response.data

    with app.app_context():
        assert User.query.filter_by(username="dup_user").count() == 1


def test_register_duplicate_submission_only_creates_one_account():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        success, message = auth_service.send_register_otp(email="repeat@example.com")
        assert success is True
        otp = extract_otp(message)

    payload = {
        "username": "repeat_user",
        "password": "abc12345",
        "confirm_password": "abc12345",
        "phone": "",
        "email": "repeat@example.com",
        "nickname": "",
        "otp": otp,
        "action": "register",
    }

    first = client.post("/auth/register", data=payload, follow_redirects=False)
    second = client.post("/auth/register", data=payload, follow_redirects=True)

    assert first.status_code == 302
    assert second.status_code == 200

    with app.app_context():
        assert User.query.filter_by(username="repeat_user").count() == 1

import re
from datetime import datetime, timedelta

from app import create_app
from app.extensions import db
from app.models.user import User
from app.services import auth_service


def create_test_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    return app


def make_user(username, password, phone, email):
    user = User(
        username=username,
        phone=phone,
        email=email,
        role="USER",
        status="ACTIVE",
    )
    user.set_password(password)
    return user


def extract_otp(message):
    match = re.search(r"(\d{6})", message)
    assert match, message
    return match.group(1)


def login(client, identifier, password):
    return client.post(
        "/auth/login",
        data={"username": identifier, "password": password},
        follow_redirects=False,
    )


def test_password_reset_updates_hash_and_invalidates_old_password():
    app = create_test_app()

    with app.app_context():
        user = make_user("recover_user", "abc12345", "13812340100", "recover@example.com")
        db.session.add(user)
        db.session.commit()

        success, message = auth_service.send_password_reset_otp("recover_user")
        assert success is True
        otp = extract_otp(message)

        reset_ok, reset_message = auth_service.reset_password("recover_user", otp, "newabc123")
        assert reset_ok is True
        assert "密码重置成功" in reset_message

        db.session.refresh(user)
        assert user.check_password("abc12345") is False
        assert user.check_password("newabc123") is True
        assert user.session_version == 2


def test_expired_password_reset_otp_cannot_be_used():
    app = create_test_app()

    with app.app_context():
        user = make_user("expired_user", "abc12345", "13812340101", "expired@example.com")
        db.session.add(user)
        db.session.commit()

        success, message = auth_service.send_password_reset_otp("expired_user")
        assert success is True
        otp = extract_otp(message)
        key = auth_service.get_password_reset_otp_key(user)
        auth_service._otp_store[key]["expires"] = datetime.utcnow() - timedelta(seconds=1)

        reset_ok, reset_message = auth_service.reset_password("expired_user", otp, "newabc123")
        assert reset_ok is False
        assert "验证码已过期" in reset_message


def test_password_reset_send_is_limited_to_once_per_minute():
    app = create_test_app()

    with app.app_context():
        user = make_user("limit_user", "abc12345", "13812340102", "limit@example.com")
        db.session.add(user)
        db.session.commit()

        first_ok, first_message = auth_service.send_password_reset_otp("limit_user")
        second_ok, second_message = auth_service.send_password_reset_otp("limit_user")

        assert first_ok is True
        assert "验证码已生成" in first_message
        assert second_ok is False
        assert "发送过于频繁" in second_message


def test_change_password_keeps_current_session_and_invalidates_other_sessions():
    app = create_test_app()

    with app.app_context():
        db.session.add(
            make_user("change_user", "abc12345", "13812340103", "change@example.com")
        )
        db.session.commit()

    client_a = app.test_client()
    client_b = app.test_client()

    assert login(client_a, "change_user", "abc12345").status_code == 302
    assert login(client_b, "change_user", "abc12345").status_code == 302

    changed = client_a.post(
        "/auth/change-password",
        data={
            "old_password": "abc12345",
            "new_password": "newabc123",
            "confirm_password": "newabc123",
        },
        follow_redirects=False,
    )
    assert changed.status_code == 302

    current_session = client_a.get("/user/profile", follow_redirects=False)
    assert current_session.status_code == 200

    old_session = client_b.get("/user/profile", follow_redirects=False)
    assert old_session.status_code == 302
    assert "/auth/login" in old_session.headers["Location"]

    assert login(app.test_client(), "change_user", "abc12345").status_code == 200
    assert login(app.test_client(), "change_user", "newabc123").status_code == 302

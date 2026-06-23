from app import create_app
from app.extensions import db
from app.models.user import User


def create_test_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    return app


def make_user(username, password, phone, email, status="ACTIVE"):
    user = User(
        username=username,
        phone=phone,
        email=email,
        role="USER",
        status=status,
    )
    user.set_password(password)
    return user


def test_login_accepts_username_phone_and_email():
    app = create_test_app()

    with app.app_context():
        user = make_user("login_user", "abc12345", "13812340000", "login@example.com")
        db.session.add(user)
        db.session.commit()

    for identifier in ["login_user", "13812340000", "login@example.com"]:
        client = app.test_client()
        response = client.post(
            "/auth/login",
            data={"username": identifier, "password": "abc12345"},
            follow_redirects=False,
        )
        assert response.status_code == 302

        protected = client.get("/user/profile", follow_redirects=False)
        assert protected.status_code == 200

    with app.app_context():
        user = User.query.filter_by(username="login_user").first()
        assert user.last_login_at is not None


def test_wrong_password_triggers_lockout_after_five_failures():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        db.session.add(
            make_user("locked_user", "abc12345", "13812340001", "locked@example.com")
        )
        db.session.commit()

    for _ in range(5):
        response = client.post(
            "/auth/login",
            data={"username": "locked_user", "password": "wrongpass1"},
            follow_redirects=True,
        )
        assert response.status_code == 200

    locked = client.post(
        "/auth/login",
        data={"username": "locked_user", "password": "abc12345"},
        follow_redirects=True,
    )
    assert "账号已被锁定".encode("utf-8") in locked.data


def test_disabled_user_cannot_login():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        db.session.add(
            make_user("disabled_user", "abc12345", "13812340002", "disabled@example.com", status="DISABLED")
        )
        db.session.commit()

    response = client.post(
        "/auth/login",
        data={"username": "disabled_user", "password": "abc12345"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "该账号已被禁用".encode("utf-8") in response.data


def test_logout_is_idempotent_and_blocks_protected_page_afterwards():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        db.session.add(
            make_user("logout_user", "abc12345", "13812340003", "logout@example.com")
        )
        db.session.commit()

    login_response = client.post(
        "/auth/login",
        data={"username": "logout_user", "password": "abc12345"},
        follow_redirects=False,
    )
    assert login_response.status_code == 302

    profile_response = client.get("/user/profile", follow_redirects=False)
    assert profile_response.status_code == 200

    first_logout = client.get("/auth/logout", follow_redirects=False)
    second_logout = client.get("/auth/logout", follow_redirects=False)

    assert first_logout.status_code == 302
    assert second_logout.status_code == 302

    profile_after_logout = client.get("/user/profile", follow_redirects=False)
    assert profile_after_logout.status_code == 302
    assert "/auth/login" in profile_after_logout.headers["Location"]

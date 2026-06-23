import io
import re

from app import create_app
from app.extensions import db
from app.models.user import User
from app.services import user_service


def create_test_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    return app


def make_user(username, password, phone, email, nickname="测试用户", introduction="hello"):
    user = User(
        username=username,
        phone=phone,
        email=email,
        nickname=nickname,
        introduction=introduction,
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


def test_profile_update_requires_otp_for_contact_change_and_persists_sanitized_content():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        db.session.add(
            make_user("profile_user", "abc12345", "13812340200", "profile@example.com")
        )
        db.session.commit()

        current_user = User.query.filter_by(username="profile_user").first()
        success, message = user_service.send_profile_contact_otp(
            current_user,
            phone="13812340201",
            email="newprofile@example.com"
        )
        assert success is True
        otp = extract_otp(message)

    assert login(client, "profile_user", "abc12345").status_code == 302

    response = client.post(
        "/user/profile/edit",
        data={
            "nickname": "<script>alert(1)</script>新昵称",
            "phone": "13812340201",
            "email": "newprofile@example.com",
            "introduction": "<img src=x onerror=alert(1)>你好<script>alert(2)</script>",
            "contact_otp": otp,
            "action": "save",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    profile_page = client.get("/user/profile", follow_redirects=True)
    assert profile_page.status_code == 200
    assert "新昵称".encode("utf-8") in profile_page.data
    assert b"<script>" not in profile_page.data
    assert b"onerror" not in profile_page.data

    with app.app_context():
        user = User.query.filter_by(username="profile_user").first()
        assert user.nickname == "新昵称"
        assert user.phone == "13812340201"
        assert user.email == "newprofile@example.com"
        assert user.introduction == "你好"


def test_profile_update_rejects_duplicate_contact_and_keeps_original_values():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        db.session.add(make_user("owner_user", "abc12345", "13812340202", "owner@example.com"))
        db.session.add(make_user("other_user", "abc12345", "13812340203", "other@example.com"))
        db.session.commit()

    assert login(client, "owner_user", "abc12345").status_code == 302

    response = client.post(
        "/user/profile/edit",
        data={
            "nickname": "我的昵称",
            "phone": "13812340203",
            "email": "owner@example.com",
            "introduction": "新的简介",
            "contact_otp": "",
            "action": "save",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "手机号已被其他账号使用".encode("utf-8") in response.data

    with app.app_context():
        user = User.query.filter_by(username="owner_user").first()
        assert user.phone == "13812340202"
        assert user.nickname == "测试用户"


def test_profile_update_rejects_invalid_avatar_file():
    app = create_test_app()
    client = app.test_client()

    with app.app_context():
        db.session.add(make_user("avatar_user", "abc12345", "13812340204", "avatar@example.com"))
        db.session.commit()

    assert login(client, "avatar_user", "abc12345").status_code == 302

    response = client.post(
        "/user/profile/edit",
        data={
            "nickname": "头像用户",
            "phone": "13812340204",
            "email": "avatar@example.com",
            "introduction": "hello",
            "contact_otp": "",
            "action": "save",
            "avatar": (io.BytesIO(b"not-an-image"), "avatar.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "上传文件不是有效的图片".encode("utf-8") in response.data

    with app.app_context():
        user = User.query.filter_by(username="avatar_user").first()
        assert user.avatar is None

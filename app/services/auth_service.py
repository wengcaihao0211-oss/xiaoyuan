import random
import re
import threading
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.user import User

_login_attempts = {}
_lock = threading.Lock()

MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
REGISTER_OTP_PREFIX = 'register:'
PASSWORD_RESET_OTP_PREFIX = 'password-reset:'
PHONE_PATTERN = re.compile(r'^1[3-9]\d{9}$')
USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_]{4,20}$')
PASSWORD_LETTER_PATTERN = re.compile(r'[A-Za-z]')
PASSWORD_DIGIT_PATTERN = re.compile(r'\d')
PASSWORD_RESET_REQUEST_INTERVAL_SECONDS = 60
PASSWORD_RESET_OTP_TTL_MINUTES = 5
PASSWORD_RESET_REQUEST_HINT = '若账号存在且已绑定手机号或邮箱，验证码已发送，请注意查收。'


def check_login_lockout(login_key):
    with _lock:
        entry = _login_attempts.get(login_key)
        if not entry:
            return False, 0
        if entry.get('lock_until') and datetime.utcnow() < entry['lock_until']:
            remaining = (entry['lock_until'] - datetime.utcnow()).total_seconds() / 60
            return True, max(1, int(remaining))
        if entry.get('lock_until') and datetime.utcnow() >= entry['lock_until']:
            del _login_attempts[login_key]
        return False, 0


def record_failed_attempt(login_key):
    with _lock:
        entry = _login_attempts.get(login_key, {'count': 0, 'lock_until': None})
        entry['count'] = entry.get('count', 0) + 1
        if entry['count'] >= MAX_ATTEMPTS:
            entry['lock_until'] = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
            _login_attempts[login_key] = entry
            return True, LOCKOUT_MINUTES
        _login_attempts[login_key] = entry
        return False, 0


def reset_attempts(login_key):
    with _lock:
        _login_attempts.pop(login_key, None)


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password_hash, password):
    return check_password_hash(password_hash, password)


_otp_store = {}
_otp_lock = threading.Lock()


def generate_otp(username):
    otp = str(random.randint(100000, 999999))
    with _otp_lock:
        _otp_store[username] = {
            'otp': otp,
            'expires': datetime.utcnow() + timedelta(minutes=5),
            'sent_at': datetime.utcnow()
        }
    return otp


def issue_otp(key, ttl_minutes=5, min_interval_seconds=None):
    now = datetime.utcnow()
    with _otp_lock:
        entry = _otp_store.get(key)
        if entry and min_interval_seconds:
            elapsed = (now - entry.get('sent_at', now)).total_seconds()
            if elapsed < min_interval_seconds:
                remaining = max(1, int(min_interval_seconds - elapsed))
                return False, remaining, None

        otp = str(random.randint(100000, 999999))
        _otp_store[key] = {
            'otp': otp,
            'expires': now + timedelta(minutes=ttl_minutes),
            'sent_at': now
        }
        return True, 0, otp


def verify_otp(username, otp, consume=True):
    with _otp_lock:
        entry = _otp_store.get(username)
        if not entry:
            return False, '未找到验证码请求，请重新获取。'
        if datetime.utcnow() > entry['expires']:
            _otp_store.pop(username, None)
            return False, '验证码已过期，请重新获取。'
        if entry['otp'] != otp:
            return False, '验证码不正确。'
        if consume:
            _otp_store.pop(username, None)
        return True, '验证成功。'


def normalize_username(username):
    return (username or '').strip()


def normalize_phone(phone):
    return (phone or '').strip()


def normalize_email(email):
    return (email or '').strip().lower()


def normalize_nickname(nickname):
    return (nickname or '').strip()


def normalize_login_identifier(identifier):
    return (identifier or '').strip()


def find_user_for_login(identifier):
    normalized = normalize_login_identifier(identifier)
    normalized_email = normalized.lower()
    return User.active().filter(
        or_(
            User.username == normalized,
            User.phone == normalized,
            User.email == normalized_email
        )
    ).first()


def get_login_lock_key(identifier, user=None):
    if user:
        return f'user:{user.user_id}'
    return f'login:{normalize_login_identifier(identifier).lower()}'


def validate_registration_payload(username, password, phone=None, email=None):
    username = normalize_username(username)
    phone = normalize_phone(phone)
    email = normalize_email(email)

    if not USERNAME_PATTERN.fullmatch(username):
        return False, '用户名仅允许 4~20 位字母、数字、下划线。'
    password_valid, password_message = validate_password_strength(password)
    if not password_valid:
        return False, password_message
    if not phone and not email:
        return False, '手机号或邮箱至少填写一项。'
    if phone and not PHONE_PATTERN.fullmatch(phone):
        return False, '手机号格式不正确。'
    return True, ''


def validate_password_strength(password):
    value = password or ''
    if len(value) < 8 or len(value) > 20:
        return False, '密码长度需为 8~20 位。'
    if not PASSWORD_LETTER_PATTERN.search(value) or not PASSWORD_DIGIT_PATTERN.search(value):
        return False, '密码必须同时包含字母和数字。'
    return True, ''


def get_register_otp_key(phone=None, email=None):
    phone = normalize_phone(phone)
    email = normalize_email(email)
    contact = email or phone
    return f'{REGISTER_OTP_PREFIX}{contact}'


def send_register_otp(phone=None, email=None):
    phone = normalize_phone(phone)
    email = normalize_email(email)

    if not phone and not email:
        return False, '请先填写手机号或邮箱后再获取验证码。'
    if phone and not PHONE_PATTERN.fullmatch(phone):
        return False, '手机号格式不正确。'
    if phone and User.active().filter_by(phone=phone).first():
        return False, '手机号已被其他账号使用。'
    if email and User.active().filter_by(email=email).first():
        return False, '邮箱已被其他账号使用。'

    otp = generate_otp(get_register_otp_key(phone=phone, email=email))
    target = email or phone
    return True, f'验证码已生成（演示模式）：{otp}，请在 5 分钟内完成注册。目标：{target}'


def verify_register_otp(phone=None, email=None, otp=None):
    return verify_otp(get_register_otp_key(phone=phone, email=email), otp)


def find_user_for_account(identifier):
    return find_user_for_login(identifier)


def log_security_event(user, action, detail):
    username = getattr(user, 'username', 'unknown')
    current_app.logger.info('[SECURITY] user=%s action=%s detail=%s', username, action, detail)


def rotate_user_sessions(user):
    user.session_version = (user.session_version or 0) + 1


def get_password_reset_otp_key(user):
    return f'{PASSWORD_RESET_OTP_PREFIX}{user.user_id}'


def send_password_reset_otp(identifier):
    user = find_user_for_account(identifier)
    if not user or (not user.phone and not user.email):
        return True, PASSWORD_RESET_REQUEST_HINT

    key = get_password_reset_otp_key(user)
    success, remaining, otp = issue_otp(
        key,
        ttl_minutes=PASSWORD_RESET_OTP_TTL_MINUTES,
        min_interval_seconds=PASSWORD_RESET_REQUEST_INTERVAL_SECONDS
    )
    if not success:
        return False, f'验证码发送过于频繁，请 {remaining} 秒后再试。'

    target = user.email or user.phone
    log_security_event(user, 'PASSWORD_RESET_OTP_SENT', f'target={target}')
    return True, (
        f'验证码已生成（演示模式）：{otp}，请在 '
        f'{PASSWORD_RESET_OTP_TTL_MINUTES} 分钟内完成重置。目标：{target}'
    )


def register_user(username, password, phone=None, email=None, nickname=None, otp=None):
    username = normalize_username(username)
    phone = normalize_phone(phone) or None
    email = normalize_email(email) or None
    nickname = normalize_nickname(nickname) or None

    valid, message = validate_registration_payload(username, password, phone=phone, email=email)
    if not valid:
        return False, message, None

    otp_valid, otp_message = verify_register_otp(phone=phone, email=email, otp=otp)
    if not otp_valid:
        return False, otp_message, None

    existing = User.active().filter_by(username=username).first()
    if existing:
        return False, '用户名已被注册。', None
    if phone and User.active().filter_by(phone=phone).first():
        return False, '手机号已被其他账号使用。', None
    if email and User.active().filter_by(email=email).first():
        return False, '邮箱已被其他账号使用。', None

    user = User(
        username=username,
        phone=phone,
        email=email,
        nickname=nickname,
        role='USER',
        status='ACTIVE'
    )
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        conflict = User.active().filter_by(username=username).first()
        if conflict:
            return False, '用户名已被注册。', None
        if phone and User.active().filter_by(phone=phone).first():
            return False, '手机号已被其他账号使用。', None
        if email and User.active().filter_by(email=email).first():
            return False, '邮箱已被其他账号使用。', None
        return False, '注册失败，请稍后重试。', None
    return True, '注册成功！', user


def authenticate_user(identifier, password, login_ip=None):
    user = find_user_for_login(identifier)
    login_key = get_login_lock_key(identifier, user=user)

    is_locked, remaining = check_login_lockout(login_key)
    if is_locked:
        return False, f'账号已被锁定，请 {remaining} 分钟后再试。', None
    if not user:
        record_failed_attempt(login_key)
        return False, '账号或密码错误。', None
    if user.status == 'DISABLED':
        return False, '该账号已被禁用，当前无法登录。', None
    if not user.check_password(password):
        record_failed_attempt(login_key)
        return False, '账号或密码错误。', None
    reset_attempts(login_key)
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = (login_ip or '').strip()[:45] or None
    db.session.commit()
    return True, '登录成功！', user


def change_password(user, old_password, new_password):
    if not user.check_password(old_password):
        return False, '旧密码不正确。'
    valid, message = validate_password_strength(new_password)
    if not valid:
        return False, message
    if user.check_password(new_password):
        return False, '新密码不能与当前密码相同。'
    user.set_password(new_password)
    rotate_user_sessions(user)
    log_security_event(user, 'PASSWORD_CHANGED', 'password changed by authenticated user')
    db.session.commit()
    return True, '密码修改成功！'


def reset_password(identifier, otp, new_password):
    user = find_user_for_account(identifier)
    if not user:
        return False, '验证码错误或已过期，请重新获取。'
    valid, message = validate_password_strength(new_password)
    if not valid:
        return False, message
    if user.check_password(new_password):
        return False, '新密码不能与旧密码相同。'
    otp_valid, otp_message = verify_otp(get_password_reset_otp_key(user), otp, consume=False)
    if not otp_valid:
        if otp_message == '验证码不正确。':
            return False, '验证码错误，请重新输入。'
        return False, otp_message
    user.set_password(new_password)
    rotate_user_sessions(user)
    verify_otp(get_password_reset_otp_key(user), otp, consume=True)
    log_security_event(user, 'PASSWORD_RESET', 'password reset by otp')
    db.session.commit()
    return True, '密码重置成功，请登录。'

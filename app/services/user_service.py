import re

from app.extensions import db
from app.models.user import User
from app.utils.helpers import save_upload
from app.services import auth_service


PROFILE_CONTACT_OTP_PREFIX = 'profile-contact:'
TAG_PATTERN = re.compile(r'<[^>]+>')
SCRIPT_PATTERN = re.compile(r'(?is)<(script|style).*?>.*?</\1>')


def sanitize_plain_text(value):
    text = (value or '').strip()
    if not text:
        return ''
    text = SCRIPT_PATTERN.sub('', text)
    text = TAG_PATTERN.sub('', text)
    return text.strip()


def normalize_profile_contact(phone=None, email=None):
    normalized_phone = auth_service.normalize_phone(phone) or None
    normalized_email = auth_service.normalize_email(email) or None
    return normalized_phone, normalized_email


def get_profile_contact_otp_key(user, phone=None, email=None):
    normalized_phone, normalized_email = normalize_profile_contact(phone=phone, email=email)
    return f'{PROFILE_CONTACT_OTP_PREFIX}{user.user_id}:{normalized_phone or ""}:{normalized_email or ""}'


def validate_profile_payload(user, nickname, phone=None, email=None, introduction=None):
    sanitized_nickname = sanitize_plain_text(nickname)
    if not sanitized_nickname or len(sanitized_nickname) > 20:
        return False, '昵称需为 1~20 字。', {}

    sanitized_intro = sanitize_plain_text(introduction)
    if len(sanitized_intro) > 200:
        return False, '个人简介不能超过 200 字。', {}

    normalized_phone, normalized_email = normalize_profile_contact(phone=phone, email=email)
    if normalized_phone and not auth_service.PHONE_PATTERN.fullmatch(normalized_phone):
        return False, '手机号格式不正确。', {}

    if normalized_phone:
        phone_owner = User.active().filter(
            User.phone == normalized_phone,
            User.user_id != user.user_id
        ).first()
        if phone_owner:
            return False, '手机号已被其他账号使用。', {}

    if normalized_email:
        email_owner = User.active().filter(
            User.email == normalized_email,
            User.user_id != user.user_id
        ).first()
        if email_owner:
            return False, '邮箱已被其他账号使用。', {}

    return True, '', {
        'nickname': sanitized_nickname,
        'phone': normalized_phone,
        'email': normalized_email,
        'introduction': sanitized_intro or None,
    }


def send_profile_contact_otp(user, phone=None, email=None):
    valid, message, normalized = validate_profile_payload(
        user,
        nickname=user.nickname or '临时昵称',
        phone=phone,
        email=email,
        introduction=user.introduction or ''
    )
    if not valid:
        return False, message

    contact_changed = (
        normalized['phone'] != user.phone or
        normalized['email'] != user.email
    )
    if not contact_changed:
        return False, '手机号或邮箱未发生变化，无需验证。'

    key = get_profile_contact_otp_key(user, phone=normalized['phone'], email=normalized['email'])
    success, remaining, otp = auth_service.issue_otp(
        key,
        ttl_minutes=5,
        min_interval_seconds=60
    )
    if not success:
        return False, f'验证码发送过于频繁，请 {remaining} 秒后再试。'

    target = '、'.join([value for value in [normalized['phone'], normalized['email']] if value])
    auth_service.log_security_event(user, 'PROFILE_CONTACT_OTP_SENT', f'target={target}')
    return True, f'验证码已生成（演示模式）：{otp}，请在 5 分钟内完成验证。目标：{target}'


def update_profile(user, nickname=None, phone=None, email=None, introduction=None, avatar_file=None, contact_otp=None):
    valid, message, normalized = validate_profile_payload(
        user,
        nickname=nickname,
        phone=phone,
        email=email,
        introduction=introduction
    )
    if not valid:
        return False, message

    contact_changed = (
        normalized['phone'] != user.phone or
        normalized['email'] != user.email
    )
    if contact_changed:
        if not (contact_otp or '').strip():
            return False, '手机号或邮箱修改后请先获取并填写验证码。'

        otp_valid, otp_message = auth_service.verify_otp(
            get_profile_contact_otp_key(user, phone=normalized['phone'], email=normalized['email']),
            (contact_otp or '').strip(),
            consume=False
        )
        if not otp_valid:
            if otp_message == '验证码不正确。':
                return False, '验证码错误，请重新输入。'
            return False, otp_message

    avatar_path = None
    if avatar_file and avatar_file.filename:
        try:
            avatar_path = save_upload(avatar_file, 'avatars', f'user_{user.user_id}')
        except ValueError as e:
            return False, str(e)

    user.nickname = normalized['nickname']
    user.phone = normalized['phone']
    user.email = normalized['email']
    user.introduction = normalized['introduction']
    if avatar_path:
        user.avatar = avatar_path

    db.session.commit()
    if contact_changed:
        auth_service.verify_otp(
            get_profile_contact_otp_key(user, phone=normalized['phone'], email=normalized['email']),
            (contact_otp or '').strip(),
            consume=True
        )
        auth_service.log_security_event(user, 'PROFILE_UPDATED_CONTACT', 'profile contact updated')
    return True, '个人资料更新成功！'


def get_user_stats(user):
    from app.models.product import Product
    from app.models.review import Review
    from app.models.orders import Order
    product_count = Product.active().filter_by(seller_id=user.user_id).count()
    sold_count = Product.active().filter_by(seller_id=user.user_id, product_status='SOLD').count()
    avg_rating = db.session.query(db.func.avg(Review.score)).filter(
        Review.reviewed_user_id == user.user_id, Review.deleted == False
    ).scalar()
    order_count = Order.query.filter(
        (Order.buyer_id == user.user_id) | (Order.seller_id == user.user_id),
        Order.deleted == False
    ).count()
    return {
        'product_count': product_count,
        'sold_count': sold_count,
        'avg_rating': round(float(avg_rating), 1) if avg_rating else None,
        'review_count': Review.active().filter_by(reviewed_user_id=user.user_id).count(),
        'order_count': order_count,
    }

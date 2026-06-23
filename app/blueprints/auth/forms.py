import re

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError


USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_]{4,20}$')
PASSWORD_LETTER_PATTERN = re.compile(r'[A-Za-z]')
PASSWORD_DIGIT_PATTERN = re.compile(r'\d')
PHONE_PATTERN = re.compile(r'^1[3-9]\d{9}$')


class LoginForm(FlaskForm):
    username = StringField('账号', validators=[DataRequired('请输入用户名、手机号或邮箱')])
    password = PasswordField('密码', validators=[DataRequired('请输入密码')])
    submit = SubmitField('登录')


class RegisterForm(FlaskForm):
    username = StringField('用户名', validators=[
        DataRequired('请输入用户名'),
        Length(min=4, max=20, message='用户名长度需为 4~20 位')
    ])
    password = PasswordField('密码', validators=[
        DataRequired('请输入密码'),
        Length(min=8, max=20, message='密码长度需为 8~20 位')
    ])
    confirm_password = PasswordField('确认密码', validators=[
        DataRequired('请确认密码'),
        EqualTo('password', message='两次密码不一致')
    ])
    phone = StringField('手机号', validators=[Optional(), Length(max=30)])
    email = StringField('邮箱', validators=[
        Optional(),
        Length(max=255, message='邮箱长度不能超过 255 个字符'),
        Email(message='邮箱格式不正确')
    ])
    nickname = StringField('昵称', validators=[
        Optional(),
        Length(max=50, message='昵称长度不能超过 50 个字符')
    ])
    otp = StringField('验证码', validators=[
        DataRequired('请输入验证码'),
        Length(min=6, max=6, message='验证码为 6 位')
    ])
    submit = SubmitField('注册')

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False

        has_phone = bool((self.phone.data or '').strip())
        has_email = bool((self.email.data or '').strip())
        if not has_phone and not has_email:
            message = '手机号和邮箱至少填写一项'
            self.phone.errors.append(message)
            self.email.errors.append(message)
            return False

        return True

    def validate_username(self, field):
        if not USERNAME_PATTERN.fullmatch((field.data or '').strip()):
            raise ValidationError('用户名仅允许 4~20 位字母、数字、下划线')

    def validate_password(self, field):
        value = field.data or ''
        if not PASSWORD_LETTER_PATTERN.search(value) or not PASSWORD_DIGIT_PATTERN.search(value):
            raise ValidationError('密码必须同时包含字母和数字')

    def validate_phone(self, field):
        value = (field.data or '').strip()
        if value and not PHONE_PATTERN.fullmatch(value):
            raise ValidationError('手机号格式不正确')


class ForgotPasswordForm(FlaskForm):
    username = StringField('账号', validators=[DataRequired('请输入用户名、手机号或邮箱')])
    submit = SubmitField('获取验证码')


class ResetPasswordForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    otp = StringField('验证码', validators=[DataRequired('请输入验证码'), Length(min=6, max=6)])
    new_password = PasswordField('新密码', validators=[
        DataRequired('请输入新密码'),
        Length(min=8, max=20, message='密码长度需为 8~20 位')
    ])
    confirm_password = PasswordField('确认新密码', validators=[
        DataRequired('请确认新密码'),
        EqualTo('new_password', message='两次密码不一致')
    ])
    submit = SubmitField('重置密码')

    def validate_new_password(self, field):
        value = field.data or ''
        if not PASSWORD_LETTER_PATTERN.search(value) or not PASSWORD_DIGIT_PATTERN.search(value):
            raise ValidationError('密码必须同时包含字母和数字')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('旧密码', validators=[DataRequired('请输入旧密码')])
    new_password = PasswordField('新密码', validators=[
        DataRequired('请输入新密码'),
        Length(min=8, max=20, message='新密码长度需为 8~20 位')
    ])
    confirm_password = PasswordField('确认新密码', validators=[
        DataRequired('请确认新密码'),
        EqualTo('new_password', message='两次密码不一致')
    ])
    submit = SubmitField('修改密码')

    def validate_new_password(self, field):
        value = field.data or ''
        if not PASSWORD_LETTER_PATTERN.search(value) or not PASSWORD_DIGIT_PATTERN.search(value):
            raise ValidationError('密码必须同时包含字母和数字')

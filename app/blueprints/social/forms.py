from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class MessageForm(FlaskForm):
    content = TextAreaField('消息内容', validators=[
        DataRequired('消息内容不能为空'),
        Length(max=2000)
    ])
    submit = SubmitField('发送')


class ReviewForm(FlaskForm):
    score = SelectField('评分', choices=[
        (5, '⭐⭐⭐⭐⭐ 非常好'),
        (4, '⭐⭐⭐⭐ 好'),
        (3, '⭐⭐⭐ 一般'),
        (2, '⭐⭐ 较差'),
        (1, '⭐ 很差'),
    ], coerce=int, validators=[DataRequired('请选择评分')])
    review_content = TextAreaField('评价内容（选填）', validators=[
        Optional(), Length(max=500)
    ])
    submit = SubmitField('提交评价')


class ReportForm(FlaskForm):
    target_type = HiddenField(validators=[DataRequired()])
    target_id = HiddenField(validators=[DataRequired()])
    report_reason = SelectField('举报原因', choices=[
        ('虚假信息', '虚假信息'),
        ('违禁商品', '违禁商品'),
        ('欺诈行为', '欺诈行为'),
        ('骚扰信息', '骚扰信息'),
        ('侵权内容', '侵权内容'),
        ('其他', '其他'),
    ], validators=[DataRequired('请选择举报原因')])
    description = TextAreaField('详细说明（10～500字）', validators=[
        Optional(),
        Length(min=10, max=500, message='说明长度需要在10～500字之间')
    ])
    submit = SubmitField('提交举报')


class AppealForm(FlaskForm):
    appeal_content = TextAreaField('申诉内容（10～1000字）', validators=[
        DataRequired('申诉内容不能为空'),
        Length(min=10, max=1000, message='申诉内容长度需要在10～1000字之间')
    ])
    submit = SubmitField('提交申诉')

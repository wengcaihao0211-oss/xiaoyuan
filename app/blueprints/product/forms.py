from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, TextAreaField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, NumberRange, Length


class ProductForm(FlaskForm):
    product_name = StringField('商品名称', validators=[
        DataRequired('请输入商品名称'),
        Length(min=1, max=50, message='商品名称1~50个字符')
    ])
    category_id = SelectField('商品分类', coerce=int, validators=[DataRequired('请选择分类')])
    price = DecimalField('价格', validators=[
        DataRequired('请输入价格'),
        NumberRange(min=0.01, max=99999.99, message='价格在0.01~99999.99之间')
    ])
    condition_level = SelectField('商品成色', choices=[
        ('全新', '全新'),
        ('九成新', '九成新'),
        ('八成新', '八成新'),
        ('七成新', '七成新'),
        ('七成新以下', '七成新以下'),
    ], validators=[DataRequired('请选择成色')])
    description = TextAreaField('商品描述', validators=[
        DataRequired('请输入商品描述'),
        Length(min=10, max=1000, message='描述需要10~1000个字符')
    ])
    trade_location = StringField('交易地点', validators=[
        DataRequired('请输入交易地点'),
        Length(max=255)
    ])
    submission_token = HiddenField()
    submit_draft = SubmitField('保存草稿')
    submit_publish = SubmitField('提交审核')

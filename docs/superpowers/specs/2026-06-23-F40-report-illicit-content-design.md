# F40 举报违规商品或用户

## 一、功能概述

所属模块：消息、评价与举报

参与者：已登录普通用户

优先级：高

前置条件：举报目标存在；举报人账号正常。

触发条件：用户在商品详情或用户资料页提交举报。

## 二、输入数据

输入数据包括：目标类型、目标编号、举报原因枚举、说明 10～500 字。

## 三、处理流程与业务规则

校验目标；保存举报快照、原因、说明、提交时间和待处理状态；同一用户对同一目标存在待处理举报时禁止重复提交；通知管理员。

## 四、输出及后置条件

输出及后置条件：生成举报编号，用户可查看处理状态。

## 五、异常与边界处理

异常与边界处理：举报自己、目标不存在、说明过短 / 超长或重复待处理举报时拒绝。

## 六、验收标准

验收标准：合法举报进入待处理队列；重复举报不新增；管理员可看到完整信息。

## 七、程序流程图

此业务流程需要绘制程序流程图。

## 八、完整伪代码

```python
# ==========================================
# 数据模型层 - Report 模型
# ==========================================
class Report:
    def __init__(self):
        self.report_id = None
        self.reporter_id = None
        self.target_type = None  # 'PRODUCT' 或 'USER'
        self.target_id = None
        self.report_reason = None
        self.description = None
        self.target_snapshot = None  # 举报时的目标快照
        self.report_status = 'PENDING'
        self.handle_result = None
        self.handler_id = None
        self.created_at = None
        self.handled_at = None

# ==========================================
# 服务层 - ReportService
# ==========================================
class ReportService:
    @staticmethod
    def submit_report(reporter_id, target_type, target_id, reason, description=None):
        """
        提交举报
        """
        # 1. 校验举报人账号状态
        reporter = UserService.get_user_by_id(reporter_id)
        if not reporter or reporter.status != 'ACTIVE':
            return False, '举报人账号异常。', None
        
        # 2. 校验举报目标
        target = ReportService._validate_target(target_type, target_id)
        if not target:
            return False, '举报目标不存在。', None
        
        # 3. 检查是否举报自己
        if ReportService._is_self_report(reporter_id, target_type, target):
            return False, '不能举报自己。', None
        
        # 4. 校验说明长度
        if description:
            desc_length = len(description.strip())
            if desc_length < 10:
                return False, '说明至少需要10个字符。', None
            if desc_length > 500:
                return False, '说明不能超过500个字符。', None
        
        # 5. 检查重复待处理举报
        existing = ReportRepository.find_pending_report(reporter_id, target_type, target_id)
        if existing:
            return False, '您已有一个待处理的举报，请等待管理员处理。', None
        
        # 6. 生成目标快照
        snapshot = ReportService._generate_snapshot(target_type, target)
        
        # 7. 保存举报
        report = Report()
        report.reporter_id = reporter_id
        report.target_type = target_type
        report.target_id = target_id
        report.report_reason = reason
        report.description = description.strip() if description else None
        report.target_snapshot = snapshot
        report.report_status = 'PENDING'
        report.created_at = datetime.utcnow()
        
        saved_report = ReportRepository.save(report)
        
        # 8. 通知管理员
        NotificationService.notify_admins_new_report(saved_report)
        
        return True, '举报提交成功，管理员将尽快处理。', saved_report.report_id
    
    @staticmethod
    def _validate_target(target_type, target_id):
        """
        校验举报目标是否存在
        """
        if target_type == 'PRODUCT':
            return ProductService.get_product_by_id(target_id)
        elif target_type == 'USER':
            return UserService.get_user_by_id(target_id)
        return None
    
    @staticmethod
    def _is_self_report(reporter_id, target_type, target):
        """
        检查是否举报自己
        """
        if target_type == 'USER':
            return target.user_id == reporter_id
        elif target_type == 'PRODUCT':
            return target.seller_id == reporter_id
        return False
    
    @staticmethod
    def _generate_snapshot(target_type, target):
        """
        生成目标快照
        """
        if target_type == 'PRODUCT':
            return {
                'product_name': target.product_name,
                'price': float(target.price),
                'description': target.description,
                'seller_id': target.seller_id,
                'product_status': target.product_status
            }
        elif target_type == 'USER':
            return {
                'username': target.username,
                'nickname': target.nickname,
                'introduction': target.introduction,
                'role': target.role
            }
        return None
    
    @staticmethod
    def get_user_reports(user_id):
        """
        获取用户提交的举报列表
        """
        return ReportRepository.find_by_reporter_id(user_id)
    
    @staticmethod
    def get_report_detail(report_id, user_id):
        """
        获取举报详情（仅允许举报人查看）
        """
        report = ReportRepository.find_by_id(report_id)
        if report and report.reporter_id == user_id:
            return report
        return None

# ==========================================
# 控制器层 - ReportController
# ==========================================
class ReportController:
    @login_required
    def show_report_form(self):
        """
        显示举报表单页面
        """
        target_type = request.args.get('type', 'PRODUCT')
        target_id = request.args.get('id', 0, type=int)
        
        target = ReportService._validate_target(target_type, target_id)
        if not target:
            flash('举报目标不存在。', 'danger')
            return redirect(url_for('home'))
        
        form = ReportForm()
        form.target_type.data = target_type
        form.target_id.data = str(target_id)
        
        return render_template('social/report_form.html', form=form, 
                              target_type=target_type, target=target)
    
    @login_required
    def submit_report(self):
        """
        处理举报提交
        """
        form = ReportForm()
        
        if form.validate_on_submit():
            success, message, report_id = ReportService.submit_report(
                reporter_id=current_user.user_id,
                target_type=form.target_type.data,
                target_id=int(form.target_id.data),
                reason=form.report_reason.data,
                description=form.description.data
            )
            
            flash(message, 'success' if success else 'danger')
            
            if success:
                return redirect(url_for('my_reports'))
        
        # 重新加载目标信息
        target_type = form.target_type.data
        target_id = int(form.target_id.data)
        target = ReportService._validate_target(target_type, target_id)
        
        return render_template('social/report_form.html', form=form,
                              target_type=target_type, target=target)
    
    @login_required
    def my_reports(self):
        """
        我的举报列表
        """
        reports = ReportService.get_user_reports(current_user.user_id)
        return render_template('social/my_reports.html', reports=reports)

# ==========================================
# 前端层 - 表单类
# ==========================================
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
```

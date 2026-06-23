"""
AI内容审核服务
"""
import os
import json
import random
from datetime import datetime
from app.extensions import db
from app.models.report import Report
from app.models.product import Product
from app.models.user import User


# 配置AI审核的置信度阈值
AI_CONFIDENCE_THRESHOLD = 0.85  # 高于此值AI可以自动处理
AI_MIN_CONFIDENCE = 0.6  # 低于此值需要人工审核


def analyze_product_content(product_name, description):
    """
    审核商品内容
    返回: (审核结果, 原因/说明)
    审核结果: 'APPROVED' - 通过, 'REJECTED' - 直接拒绝, 'NEEDS_REVIEW' - 需要人工审核
    """
    content = f"{product_name} {description}"
    
    # 高风险关键词 - 直接拒绝
    high_risk_keywords = [
        '毒品', '赌博', '枪支', '武器', '弹药', '管制刀具', '违禁品',
        '假币', '假证', '假章', '办证', '刻章', '诈骗', '传销', '非法集资', '洗钱'
    ]
    
    # 中风险关键词 - 直接拒绝
    medium_risk_keywords = [
        '色情', '暴力', '血腥', '恐怖', '走私', '假货', '盗版', '侵权',
        '劣质', '有毒', '有害', '致癌', '致死', '三无', '过期', '变质'
    ]
    
    # 低风险关键词 - 需要人工审核
    low_risk_keywords = [
        '高仿', '精仿', '夸大宣传', '虚假宣传', '绝对化', '第一', '最', '顶级',
        '第一品牌', '全网第一', '销量第一', '最佳', '最高', '最低', '最新', '最先进',
        '代考', '替考', '答案', '作弊', '作弊器', '窃听', '偷拍',
        '恶意营销', '刷屏', '垃圾广告', '骗人', '欺骗', '欺诈', '套路', '陷阱',
        '冒充', '虚假身份', '假客服', '假商家',
        '私下交易', '绕过平台', '加微信', '加qq', '线下交易'
    ]
    
    # 检查高风险
    for keyword in high_risk_keywords:
        if keyword in content:
            return 'REJECTED', f"商品内容包含高风险违规关键词: {keyword}"
    
    # 检查中风险
    for keyword in medium_risk_keywords:
        if keyword in content:
            return 'REJECTED', f"商品内容包含中风险违规关键词: {keyword}"
    
    # 检查低风险 - 需要人工审核
    for keyword in low_risk_keywords:
        if keyword in content:
            return 'NEEDS_REVIEW', f"商品内容包含需人工审核的关键词: {keyword}"
    
    return 'APPROVED', ""


class AIReviewService:
    """
    AI内容审核服务
    """
    
    # 违规关键词库
    VIOLATION_KEYWORDS = {
        'product': [
            # 违法违规类
            '色情', '暴力', '血腥', '恐怖', '毒品', '赌博', '博彩', '彩票', '枪支', '武器',
            '弹药', '管制刀具', '违禁品', '走私', '假货', '盗版', '侵权', '高仿', '精仿',
            '诈骗', '传销', '非法集资', '洗钱', '假币', '假证', '假章', '办证', '刻章',
            # 商品质量类
            '劣质', '有毒', '有害', '致癌', '致死', '三无', '过期', '变质',
            # 营销违规类
            '夸大宣传', '虚假宣传', '绝对化', '第一', '最', '顶级', '第一品牌',
            '全网第一', '销量第一', '最佳', '最高', '最低', '最新', '最先进',
            # 其他
            '代考', '替考', '答案', '作弊', '作弊器', '窃听', '偷拍',
        ],
        'user': [
            # 行为违规类
            '辱骂', '侮辱', '诽谤', '恐吓', '威胁', '骚扰', '骚扰信息',
            # 内容违规类
            '色情', '暴力', '血腥', '恐怖', '反动', '分裂',
            # 营销违规类
            '恶意营销', '刷屏', '垃圾广告', '虚假宣传', '夸大宣传',
            '骗人', '欺骗', '欺诈', '套路', '陷阱',
            # 身份违规
            '冒充', '虚假身份', '假客服', '假商家',
            # 交易违规
            '私下交易', '绕过平台', '加微信', '加qq', '线下交易',
        ],
    }
    
    # 安全关键词库（用于判断内容正常）
    SAFE_KEYWORDS = [
        '正常', '合法', '正规', '正品', '诚信', '优质', '靠谱',
        '好评', '推荐', '实用', '便宜', '划算', '实惠',
        '质量好', '服务好', '满意', '很好', '非常好', '不错',
        '二手', '闲置', '转让', '自用', '全新', '正品保证',
    ]
    
    @classmethod
    def analyze_report(cls, report):
        """
        分析举报内容，返回AI审核结果
        
        Args:
            report: Report对象
            
        Returns:
            dict: {
                'result': 'SAFE' | 'VIOLATION' | 'UNCERTAIN',
                'confidence': float,
                'reason': str
            }
        """
        try:
            # 构建要分析的文本
            content_to_analyze = cls._build_analysis_content(report)
            
            # 实际项目中，这里应该调用真实的AI API
            # 例如：OpenAI、阿里云内容安全、腾讯云内容安全等
            # 这里使用模拟的AI分析
            result = cls._simulate_ai_analysis(content_to_analyze, report)
            
            return result
            
        except Exception as e:
            print(f"AI审核出错: {e}")
            return {
                'result': 'UNCERTAIN',
                'confidence': 0.0,
                'reason': f'AI审核服务异常: {str(e)}'
            }
    
    @classmethod
    def _build_analysis_content(cls, report):
        """
        构建待分析的内容文本
        """
        parts = []
        
        # 添加举报原因
        if report.report_reason:
            parts.append(f"举报原因: {report.report_reason}")
        
        # 添加举报说明
        if report.description:
            parts.append(f"举报说明: {report.description}")
        
        # 添加目标快照内容
        if report.target_snapshot:
            if report.target_type == 'PRODUCT':
                product_name = report.target_snapshot.get('product_name', '')
                description = report.target_snapshot.get('description', '')
                parts.append(f"商品名称: {product_name}")
                parts.append(f"商品描述: {description}")
            elif report.target_type == 'USER':
                username = report.target_snapshot.get('username', '')
                nickname = report.target_snapshot.get('nickname', '')
                introduction = report.target_snapshot.get('introduction', '')
                parts.append(f"用户名: {username}")
                parts.append(f"昵称: {nickname}")
                parts.append(f"简介: {introduction}")
        
        return '\n'.join(parts)
    
    @classmethod
    def _simulate_ai_analysis(cls, content, report):
        """
        智能关键词分析（可升级为真实AI API）
        
        在真实项目中，这里可以调用：
        - OpenAI API: https://platform.openai.com/docs/api-reference/moderations
        - 阿里云内容安全: https://help.aliyun.com/zh/lvs/
        - 腾讯云内容安全: https://cloud.tencent.com/document/product/1124
        - 百度内容安全: https://ai.baidu.com/ai-doc/ANTIPORN/eek3txmh8
        """
        # 不转小写，直接匹配原文本（因为中文不存在大小写问题）
        content_to_check = content
        
        # 统计违规关键词（分级）
        high_risk_words = []
        medium_risk_words = []
        low_risk_words = []
        
        # 高风险关键词（严重违规）
        high_risk_keywords = [
            '毒品', '赌博', '枪支', '武器', '弹药', '管制刀具', '违禁品',
            '假币', '假证', '假章', '办证', '刻章', '诈骗', '传销', '非法集资', '洗钱'
        ]
        
        # 中风险关键词（违规）
        medium_risk_keywords = [
            '色情', '暴力', '血腥', '恐怖', '走私', '假货', '盗版', '侵权',
            '劣质', '有毒', '有害', '致癌', '致死', '三无', '过期', '变质',
            '辱骂', '侮辱', '诽谤', '恐吓', '威胁', '骚扰'
        ]
        
        # 低风险关键词（一般违规）
        low_risk_keywords = [
            '高仿', '精仿', '夸大宣传', '虚假宣传', '绝对化', '第一', '最', '顶级',
            '第一品牌', '全网第一', '销量第一', '最佳', '最高', '最低', '最新', '最先进',
            '代考', '替考', '答案', '作弊', '作弊器', '窃听', '偷拍',
            '恶意营销', '刷屏', '垃圾广告', '骗人', '欺骗', '欺诈', '套路', '陷阱',
            '冒充', '虚假身份', '假客服', '假商家',
            '私下交易', '绕过平台', '加微信', '加qq', '线下交易'
        ]
        
        # 检查高风险
        for keyword in high_risk_keywords:
            if keyword in content_to_check:
                high_risk_words.append(keyword)
        
        # 检查中风险
        for keyword in medium_risk_keywords:
            if keyword in content_to_check:
                medium_risk_words.append(keyword)
        
        # 检查低风险
        for keyword in low_risk_keywords:
            if keyword in content_to_check:
                low_risk_words.append(keyword)
        
        # 统计安全关键词
        safe_count = 0
        for keyword in cls.SAFE_KEYWORDS:
            if keyword in content_to_check:
                safe_count += 1
        
        # 智能判断逻辑
        if high_risk_words:
            # 高风险 - 高置信度违规，直接自动处理
            confidence = 0.98
            result = 'VIOLATION'
            reason = f"检测到高风险违规内容: {', '.join(high_risk_words)}"
        elif medium_risk_words:
            # 中风险 - 中等置信度，需要人工确认
            confidence = 0.75
            result = 'UNCERTAIN'
            reason = f"检测到潜在违规内容: {', '.join(medium_risk_words)}，建议人工审核"
        elif low_risk_words:
            # 低风险 - 较低置信度
            confidence = 0.65
            result = 'UNCERTAIN'
            reason = f"检测到一般违规内容: {', '.join(low_risk_words)}，需要人工确认"
        elif safe_count >= 2:
            # 足够的安全关键词 - 安全
            confidence = min(0.95, 0.75 + safe_count * 0.05)
            result = 'SAFE'
            reason = "内容未检测到违规信息"
        else:
            # 不确定的情况
            confidence = random.uniform(0.55, 0.75)
            result = 'UNCERTAIN'
            reason = "内容较为模糊，需要人工审核确认"
        
        return {
            'result': result,
            'confidence': round(confidence, 2),
            'reason': reason
        }
    
    @classmethod
    def process_report(cls, report):
        """
        处理举报的AI审核流程
        
        策略：
        - 置信度 > 0.85: AI自动处理
        - 置信度 < 0.60: 需要人工审核
        - 中间值: 根据结果类型决定
        """
        # 执行AI分析
        analysis_result = cls.analyze_report(report)
        
        # 更新举报记录
        report.ai_reviewed = True
        report.ai_review_result = analysis_result['result']
        report.ai_review_confidence = analysis_result['confidence']
        report.ai_review_reason = analysis_result['reason']
        report.ai_reviewed_at = datetime.utcnow()
        
        # 判断是否需要人工审核
        needs_human = cls._needs_human_review(analysis_result)
        report.needs_human_review = needs_human
        
        # 如果不需要人工审核且AI有足够把握，自动处理
        if not needs_human:
            cls._auto_handle_report(report, analysis_result)
        
        db.session.commit()
        
        return {
            'needs_human_review': needs_human,
            'ai_result': analysis_result,
            'auto_handled': not needs_human
        }
    
    @classmethod
    def _needs_human_review(cls, analysis_result):
        """
        判断是否需要人工审核
        """
        result = analysis_result['result']
        confidence = analysis_result['confidence']
        
        # 低置信度必须人工审核
        if confidence < AI_MIN_CONFIDENCE:
            return True
        
        # 高置信度可以自动处理（包括高风险违规）
        if confidence >= AI_CONFIDENCE_THRESHOLD:
            return False
        
        # 中等置信度：违规需要人工，安全可以自动
        if result == 'VIOLATION':
            return True  # 涉及违规处理，谨慎点
        else:
            return False  # 安全判断可以自动
    
    @classmethod
    def _auto_handle_report(cls, report, analysis_result):
        """
        AI自动处理举报
        """
        result = analysis_result['result']
        
        if result == 'SAFE':
            # 安全，驳回举报
            report.report_status = 'DISMISSED'
            report.handle_result = 'AI审核：内容未检测到违规信息'
            
        elif result == 'VIOLATION':
            # 违规，执行相应处理
            if report.target_type == 'PRODUCT':
                product = db.session.get(Product, report.target_id)
                if product:
                    product.product_status = 'OFF_SHELF'
                report.report_status = 'TAKEDOWN'
                report.handle_result = 'AI审核：检测到违规内容，商品已下架'
                
            elif report.target_type == 'USER':
                user = db.session.get(User, report.target_id)
                if user:
                    user.status = 'DISABLED'
                    # 下架用户的所有商品
                    Product.active().filter_by(seller_id=user.user_id).update(
                        {'product_status': 'OFF_SHELF'}, 
                        synchronize_session='fetch'
                    )
                report.report_status = 'DISABLED'
                report.handle_result = 'AI审核：检测到违规内容，用户已封禁'
        
        report.handled_at = datetime.utcnow()
    
    @classmethod
    def get_pending_human_reviews(cls, page=1, per_page=20):
        """
        获取需要人工审核的举报列表
        """
        query = Report.query.filter_by(
            needs_human_review=True,
            report_status='PENDING'
        ).order_by(Report.created_at.desc())
        
        total = query.count()
        reports = query.offset((page - 1) * per_page).limit(per_page).all()
        total_pages = (total + per_page - 1) // per_page
        
        return reports, total, total_pages
    
    @classmethod
    def get_ai_reviewed_reports(cls, page=1, per_page=20):
        """
        获取AI已审核的举报列表（含已自动处理的）
        """
        query = Report.query.filter(
            Report.ai_reviewed == True
        ).order_by(Report.ai_reviewed_at.desc())
        
        total = query.count()
        reports = query.offset((page - 1) * per_page).limit(per_page).all()
        total_pages = (total + per_page - 1) // per_page
        
        return reports, total, total_pages

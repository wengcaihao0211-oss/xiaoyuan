"""F23 收藏或取消收藏商品服务层"""
from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from flask import current_app

from app.extensions import db
from app.models.favorite import Favorite
from app.models.product import Product
from app.models.user import User
from app.utils.pagination import get_page, ListPagination


class FavoriteService:
    """收藏服务类"""

    @staticmethod
    def check_is_favorited(user_id, product_id):
        """检查用户是否已收藏商品

        Args:
            user_id: 用户编号
            product_id: 商品编号

        Returns:
            bool: 是否已收藏
        """
        return Favorite.query.filter_by(
            user_id=user_id, product_id=product_id
        ).first() is not None

    @staticmethod
    def get_favorite_count(user_id):
        """获取用户收藏数量

        Args:
            user_id: 用户编号

        Returns:
            int: 收藏数量
        """
        return Favorite.query.filter_by(user_id=user_id).count()

    @staticmethod
    def toggle_favorite(user_id, product_id, allow_own_product=False):
        """收藏或取消收藏商品

        Args:
            user_id: 用户编号
            product_id: 商品编号
            allow_own_product: 是否允许收藏自己的商品，默认禁止

        Returns:
            tuple: (成功标志, 消息, 数据字典)
            数据字典包含: is_favorited, favorite_count
        """
        # 1. 检查商品是否存在且未删除
        product = Product.query.filter_by(
            product_id=product_id, deleted=False
        ).first()
        if not product:
            return False, '商品不存在或已删除', {
                'is_favorited': False,
                'favorite_count': 0
            }

        # 2. 检查是否是自己的商品
        if not allow_own_product and product.seller_id == user_id:
            return False, '不能收藏自己的商品', {
                'is_favorited': FavoriteService.check_is_favorited(user_id, product_id),
                'favorite_count': FavoriteService.get_favorite_count(user_id)
            }

        try:
            # 3. 查找现有收藏记录
            favorite = Favorite.query.filter_by(
                user_id=user_id, product_id=product_id
            ).first()

            if favorite:
                # 4. 取消收藏 - 物理删除
                db.session.delete(favorite)
                db.session.commit()
                is_favorited = False
                message = '已取消收藏'
            else:
                # 5. 添加收藏
                favorite = Favorite(user_id=user_id, product_id=product_id)
                db.session.add(favorite)
                db.session.commit()
                is_favorited = True
                message = '已添加收藏'

            # 6. 获取最新收藏数量
            favorite_count = FavoriteService.get_favorite_count(user_id)

            return True, message, {
                'is_favorited': is_favorited,
                'favorite_count': favorite_count
            }

        except IntegrityError:
            # 7. 幂等处理：唯一约束冲突时说明已收藏，返回成功
            db.session.rollback()
            favorite_count = FavoriteService.get_favorite_count(user_id)
            return True, '已添加收藏', {
                'is_favorited': True,
                'favorite_count': favorite_count
            }
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'收藏操作失败: {str(e)}')
            return False, '操作失败，请稍后重试', {
                'is_favorited': FavoriteService.check_is_favorited(user_id, product_id),
                'favorite_count': FavoriteService.get_favorite_count(user_id)
            }

    @staticmethod
    def get_favorite_list(user_id, page=None, per_page=None):
        """获取用户收藏列表（按收藏时间倒序分页）

        Args:
            user_id: 用户编号
            page: 页码
            per_page: 每页条数

        Returns:
            tuple: (成功标志, 消息, 数据字典)
            数据字典包含: products, pagination
        """
        if per_page is None:
            per_page = current_app.config.get('ITEMS_PER_PAGE', 12)
        current_page = get_page(page)

        # 构建查询：按收藏时间倒序，同时预加载商品和图片
        query = Favorite.query.filter_by(
            user_id=user_id
        ).join(
            Product, Favorite.product_id == Product.product_id
        ).filter(
            Product.deleted == False
        ).options(
            selectinload(Favorite.product).selectinload(Product.images)
        ).order_by(
            Favorite.created_at.desc()
        )

        # 分页查询
        pagination = query.paginate(
            page=current_page,
            per_page=per_page,
            error_out=False
        )

        # 提取商品列表
        products = [fav.product for fav in pagination.items]

        # 转换为统一的分页对象（如果需要）
        if not hasattr(pagination, 'iter_pages'):
            pagination = ListPagination(
                products,
                pagination.page,
                pagination.per_page,
                pagination.total
            )

        return True, '', {
            'products': products,
            'pagination': pagination
        }

    @staticmethod
    def get_favorite_product_ids(user_id):
        """获取用户收藏的商品ID列表（用于批量查询）

        Args:
            user_id: 用户编号

        Returns:
            list: 商品ID列表
        """
        favorites = Favorite.query.filter_by(user_id=user_id).all()
        return [fav.product_id for fav in favorites]


# 便捷函数
def toggle_favorite(user_id, product_id, allow_own_product=False):
    """收藏或取消收藏商品"""
    return FavoriteService.toggle_favorite(user_id, product_id, allow_own_product)


def get_favorite_list(user_id, page=None, per_page=None):
    """获取收藏列表"""
    return FavoriteService.get_favorite_list(user_id, page, per_page)


def check_is_favorited(user_id, product_id):
    """检查是否已收藏"""
    return FavoriteService.check_is_favorited(user_id, product_id)


def get_favorite_count(user_id):
    """获取收藏数量"""
    return FavoriteService.get_favorite_count(user_id)

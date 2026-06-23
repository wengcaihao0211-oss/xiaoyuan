import time
from threading import Lock

from sqlalchemy import or_
from sqlalchemy.orm import selectinload
from flask import current_app

from app.models.category import Category
from app.models.product import Product
from app.utils.pagination import get_page, ListPagination


ALLOWED_CATEGORY_SORTS = {"latest", "price_asc", "price_desc"}
DEFAULT_CATEGORY_SORT = "latest"
CATEGORY_PAGE_SIZE = 20
SEARCH_SORT_ALIASES = {
    "latest": "latest",
    "newest": "latest",
    "price_asc": "price_asc",
    "price_low": "price_asc",
    "price_desc": "price_desc",
    "price_high": "price_desc",
}
SEARCH_KEYWORD_MAX_LENGTH = 30
SEARCH_CACHE_TTL_SECONDS = 180
SEARCH_CACHE_THRESHOLD = 3
_search_cache = {}
_search_keyword_counter = {}
_search_cache_lock = Lock()


def normalize_category_sort(sort):
    value = (sort or "").strip().lower()
    if value not in ALLOWED_CATEGORY_SORTS:
        return DEFAULT_CATEGORY_SORT
    return value


def normalize_search_sort(sort):
    value = (sort or "").strip().lower()
    return SEARCH_SORT_ALIASES.get(value, DEFAULT_CATEGORY_SORT)


def normalize_search_keyword(keyword):
    return (keyword or "").strip()


def escape_like(value):
    return (
        value
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _build_search_query(keyword, sort, min_price=None, max_price=None, condition=None):
    query = Product.on_sale().options(selectinload(Product.images))

    if keyword:
        escaped = escape_like(keyword)
        pattern = f"%{escaped}%"
        query = query.filter(or_(
            Product.product_name.ilike(pattern, escape="\\"),
            Product.description.ilike(pattern, escape="\\"),
        ))

    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if condition:
        query = query.filter_by(condition_level=(condition or "").strip())

    if sort == "price_asc":
        query = query.order_by(Product.price.asc(), Product.created_at.desc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc(), Product.created_at.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    return query


def _record_search_keyword(keyword):
    if not keyword:
        return False

    with _search_cache_lock:
        _search_keyword_counter[keyword] = _search_keyword_counter.get(keyword, 0) + 1
        return _search_keyword_counter[keyword] >= SEARCH_CACHE_THRESHOLD


def _get_search_cache(signature):
    with _search_cache_lock:
        cached = _search_cache.get(signature)
        if not cached:
            return None
        if cached["expires_at"] <= time.time():
            _search_cache.pop(signature, None)
            return None
        return cached


def _store_search_cache(signature, pagination):
    with _search_cache_lock:
        _search_cache[signature] = {
            "product_ids": [product.product_id for product in pagination.items],
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "expires_at": time.time() + SEARCH_CACHE_TTL_SECONDS,
        }


def _build_cached_pagination(cached):
    products = Product.on_sale().options(selectinload(Product.images)).filter(
        Product.product_id.in_(cached["product_ids"])
    ).all()
    product_map = {product.product_id: product for product in products}
    ordered_products = [
        product_map[product_id]
        for product_id in cached["product_ids"]
        if product_id in product_map
    ]
    return ListPagination(
        ordered_products,
        cached["page"],
        cached["per_page"],
        cached["total"],
    )


def get_category_browse_payload(category_id, sort=None, page=None):
    category = Category.enabled().filter_by(category_id=category_id).first()
    if not category:
        return False, "分类不存在或已禁用。", None

    current_sort = normalize_category_sort(sort)
    current_page = get_page(page)

    query = Product.on_sale().options(
        selectinload(Product.images)
    ).filter_by(category_id=category_id)

    if current_sort == "price_asc":
        query = query.order_by(Product.price.asc(), Product.created_at.desc())
    elif current_sort == "price_desc":
        query = query.order_by(Product.price.desc(), Product.created_at.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    pagination = query.paginate(
        page=current_page,
        per_page=CATEGORY_PAGE_SIZE,
        error_out=False,
    )

    return True, "", {
        "category": category,
        "products": pagination.items,
        "pagination": pagination,
        "current_sort": current_sort,
    }


def get_search_payload(keyword=None, sort=None, page=None, min_price=None, max_price=None, condition=None):
    current_keyword = normalize_search_keyword(keyword)
    current_sort = normalize_search_sort(sort)
    current_page = get_page(page)
    per_page = current_app.config.get("ITEMS_PER_PAGE", 12)
    current_condition = (condition or "").strip()

    if len(current_keyword) > SEARCH_KEYWORD_MAX_LENGTH:
        pagination = ListPagination([], current_page, per_page, 0)
        return False, "关键词长度需为 1~30 字。", {
            "products": [],
            "pagination": pagination,
            "query": current_keyword,
            "sort": current_sort,
            "min_price": min_price,
            "max_price": max_price,
            "condition": current_condition,
            "total_count": 0,
        }

    is_hot_keyword = _record_search_keyword(current_keyword)
    cache_signature = (
        current_keyword,
        current_sort,
        current_page,
        per_page,
        min_price,
        max_price,
        current_condition,
    )

    if is_hot_keyword:
        cached = _get_search_cache(cache_signature)
        if cached:
            pagination = _build_cached_pagination(cached)
            return True, "", {
                "products": pagination.items,
                "pagination": pagination,
                "query": current_keyword,
                "sort": current_sort,
                "min_price": min_price,
                "max_price": max_price,
                "condition": current_condition,
                "total_count": pagination.total,
            }

    query = _build_search_query(
        current_keyword,
        current_sort,
        min_price=min_price,
        max_price=max_price,
        condition=current_condition,
    )
    pagination = query.paginate(
        page=current_page,
        per_page=per_page,
        error_out=False,
    )

    if is_hot_keyword:
        _store_search_cache(cache_signature, pagination)

    return True, "", {
        "products": pagination.items,
        "pagination": pagination,
        "query": current_keyword,
        "sort": current_sort,
        "min_price": min_price,
        "max_price": max_price,
        "condition": current_condition,
        "total_count": pagination.total,
    }

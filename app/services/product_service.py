import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.extensions import db
from app.models.category import Category
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.orders import Order
from app.utils.helpers import save_upload
from app.services.ai_review_service import analyze_product_content

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
ALLOWED_IMAGE_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
TAG_PATTERN = re.compile(r'<[^>]+>')
SCRIPT_PATTERN = re.compile(r'(?is)<(script|style).*?>.*?</\1>')
CONDITION_LEVELS = {'全新', '九成新', '八成新', '七成新', '七成新以下'}


def sanitize_plain_text(value):
    text = (value or '').strip()
    if not text:
        return ''
    text = SCRIPT_PATTERN.sub('', text)
    text = TAG_PATTERN.sub('', text)
    return text.strip()


def normalize_price(price):
    if isinstance(price, Decimal):
        normalized = price
    else:
        try:
            normalized = Decimal(str(price))
        except (InvalidOperation, ValueError, TypeError):
            return None
    return normalized.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def normalize_product_payload(name, category_id, price, condition_level, description, trade_location):
    normalized_name = sanitize_plain_text(name)
    normalized_description = sanitize_plain_text(description)
    normalized_location = sanitize_plain_text(trade_location)
    normalized_price = normalize_price(price)
    return {
        'name': normalized_name,
        'category_id': category_id,
        'price': normalized_price,
        'condition_level': (condition_level or '').strip(),
        'description': normalized_description,
        'trade_location': normalized_location,
    }


def validate_product_payload(name, category_id, price, condition_level, description, trade_location):
    payload = normalize_product_payload(name, category_id, price, condition_level, description, trade_location)
    if not payload['name'] or len(payload['name']) > 50:
        return False, '商品名称需为 1~50 字。', None
    if payload['price'] is None or payload['price'] < Decimal('0.01') or payload['price'] > Decimal('99999.99'):
        return False, '价格必须在 0.01~99999.99 之间。', None
    if len(payload['description']) < 10 or len(payload['description']) > 1000:
        return False, '商品描述需要 10~1000 字。', None
    if payload['condition_level'] not in CONDITION_LEVELS:
        return False, '请选择有效的商品成色。', None
    if not payload['trade_location']:
        return False, '请输入交易地点。', None
    category = db.session.get(Category, payload['category_id'])
    if not category or category.status != 'ENABLED':
        return False, '商品分类不存在或已停用。', None
    return True, '', payload


def get_valid_images(images):
    return [f for f in (images or []) if f and getattr(f, 'filename', '')]


def validate_new_images(images):
    valid_images = get_valid_images(images)
    if len(valid_images) > 6:
        return False, '最多只能上传 6 张图片。', []
    for f in valid_images:
        ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            return False, f'不支持的图片格式: .{ext}，仅支持 JPG/PNG/WebP。', []
        mimetype = (getattr(f, 'mimetype', '') or '').lower()
        if mimetype and mimetype not in ALLOWED_IMAGE_MIME_TYPES:
            return False, f'文件 {f.filename} 的 MIME 类型不受支持。', []
        f.seek(0, 2)
        size = f.tell()
        f.seek(0)
        if size > 5 * 1024 * 1024:
            return False, f'图片 {f.filename} 超过 5MB 限制。', []
    return True, '', valid_images


def validate_publish_images(images, submit=False):
    valid, msg, valid_images = validate_new_images(images)
    if not valid:
        return False, msg, []
    if submit and len(valid_images) < 1:
        return False, '提交审核至少需要上传 1 张商品图片。', []
    return True, '', valid_images


def normalize_image_orders(existing_images, image_orders=None, delete_image_ids=None):
    image_orders = image_orders or {}
    delete_ids = {int(image_id) for image_id in (delete_image_ids or [])}
    kept_images = [image for image in existing_images if image.image_id not in delete_ids]
    ordered = sorted(
        kept_images,
        key=lambda image: (
            int(image_orders.get(str(image.image_id), image.sort_order or 0)),
            image.image_id,
        )
    )
    for idx, image in enumerate(ordered):
        image.sort_order = idx
    return ordered, delete_ids


def create_product(seller_id, name, category_id, price, condition_level,
                   description, trade_location, images=None, submit=False):
    valid_payload, payload_message, payload = validate_product_payload(
        name=name,
        category_id=category_id,
        price=price,
        condition_level=condition_level,
        description=description,
        trade_location=trade_location,
    )
    if not valid_payload:
        return False, payload_message, None

    valid_images, images_message, valid_image_files = validate_publish_images(images, submit=submit)
    if not valid_images:
        return False, images_message, None
    
    # AI内容审核 - 只在提交审核时检查
    status = 'DRAFT'
    result_message = ''
    if submit:
        review_result, review_reason = analyze_product_content(payload['name'], payload['description'])
        
        if review_result == 'REJECTED':
            # 高/中风险 - 直接拒绝
            return False, review_reason, None
        
        elif review_result == 'NEEDS_REVIEW':
            # 低风险 - 需要人工审核
            status = 'PENDING_REVIEW'
            result_message = f'商品已提交审核，{review_reason}，请等待管理员审核。'
        
        else:  # APPROVED
            # 正常 - 直接上架
            status = 'ON_SALE'
            result_message = '商品已自动审核通过并上架！'
    
    if not submit:
        status = 'DRAFT'
        result_message = '商品保存为草稿。'
    elif not result_message:
        status = 'PENDING_REVIEW'
        result_message = '商品已提交审核，请等待管理员审核。'

    product = Product(
        seller_id=seller_id, category_id=payload['category_id'],
        product_name=payload['name'], price=payload['price'],
        condition_level=payload['condition_level'], description=payload['description'],
        trade_location=payload['trade_location'], product_status=status
    )
    db.session.add(product)
    db.session.flush()

    if valid_image_files:
        try:
            save_product_images(product.product_id, valid_image_files)
        except ValueError as exc:
            db.session.rollback()
            return False, str(exc), None

    db.session.commit()
    return True, f'商品提交成功，商品编号：{product.product_id}，{result_message}', product


def save_product_images(product_id, images):
    valid_images = get_valid_images(images)
    for idx, f in enumerate(valid_images):
        path = save_upload(f, 'products', f'product_{product_id}')
        if path:
            img = ProductImage(product_id=product_id, image_url=path, sort_order=idx)
            db.session.add(img)


def update_product(product, name, category_id, price, condition_level,
                   description, trade_location, images=None, submit=False,
                   image_orders=None, delete_image_ids=None):
    if product.product_status in ('SOLD',):
        return False, '已售出的商品无法修改。'
    valid_payload, payload_message, payload = validate_product_payload(
        name=name,
        category_id=category_id,
        price=price,
        condition_level=condition_level,
        description=description,
        trade_location=trade_location,
    )
    if not valid_payload:
        return False, payload_message

    valid_images, image_message, new_images = validate_new_images(images)
    if not valid_images:
        return False, image_message
    
    # AI内容审核 - 只在提交审核时检查
    result_message = ''
    if submit:
        review_result, review_reason = analyze_product_content(payload['name'], payload['description'])
        
        if review_result == 'REJECTED':
            # 高/中风险 - 直接拒绝
            return False, review_reason
        
        elif review_result == 'NEEDS_REVIEW':
            # 低风险 - 需要人工审核
            result_message = f'商品已提交审核，{review_reason}，请等待管理员审核。'
        
        else:  # APPROVED
            # 正常 - 可以直接处理
            result_message = '商品已自动审核通过！'


    existing_images = ProductImage.query.filter_by(product_id=product.product_id).order_by(
        ProductImage.sort_order.asc(), ProductImage.image_id.asc()
    ).all()
    ordered_existing_images, delete_ids = normalize_image_orders(
        existing_images,
        image_orders=image_orders,
        delete_image_ids=delete_image_ids
    )
    final_image_count = len(ordered_existing_images) + len(new_images)
    if final_image_count > 6:
        return False, '商品图片总数不能超过 6 张。'
    if submit and final_image_count < 1:
        return False, '提交审核至少需要保留 1 张商品图片。'

    product.product_name = payload['name']
    product.category_id = payload['category_id']
    product.price = payload['price']
    product.condition_level = payload['condition_level']
    product.description = payload['description']
    product.trade_location = payload['trade_location']

    if submit:
        review_result, _ = analyze_product_content(payload['name'], payload['description'])
        
        if review_result == 'REJECTED':
            # 高/中风险 - 直接拒绝（前面已经返回）
            pass
        
        elif review_result == 'NEEDS_REVIEW':
            # 低风险 - 需要人工审核
            product.product_status = 'PENDING_REVIEW'
        
        else:  # APPROVED
            # 正常 - 直接上架
            product.product_status = 'ON_SALE'
    
    else:  # not submit
        if product.product_status in ('APPROVED', 'ON_SALE', 'OFF_SHELF'):
            product.product_status = 'DRAFT'
    
    if not result_message:
        result_message = '商品更新成功！'

    for idx, image in enumerate(ordered_existing_images):
        image.sort_order = idx

    for image in existing_images:
        if image.image_id in delete_ids:
            db.session.delete(image)

    if new_images:
        next_order = len(ordered_existing_images)
        try:
            for offset, image_file in enumerate(new_images):
                path = save_upload(image_file, 'products', f'product_{product.product_id}')
                db.session.add(ProductImage(
                    product_id=product.product_id,
                    image_url=path,
                    sort_order=next_order + offset
                ))
        except ValueError as exc:
            db.session.rollback()
            return False, str(exc)

    db.session.commit()
    return True, result_message


def delete_product(product):
    if product.product_status == 'SOLD':
        return False, '已售出的商品无法删除。'
    active_order = Order.active().filter(
        Order.product_id == product.product_id,
        Order.order_status.in_(['PENDING', 'CONFIRMED', 'PAID'])
    ).first()
    if active_order:
        return False, '该商品存在进行中的订单，无法删除。'
    product.deleted = True
    if product.product_status == 'ON_SALE':
        product.product_status = 'OFF_SHELF'
    db.session.commit()
    return True, '商品已删除。'


def toggle_product_status(product, target_status=None):
    if product.product_status == 'DRAFT':
        if ProductImage.query.filter_by(product_id=product.product_id).count() < 1:
            return False, '提交审核至少需要 1 张商品图片。'
        category = db.session.get(Category, product.category_id)
        if not category or category.status != 'ENABLED':
            return False, '商品分类不存在或已停用，无法提交审核。'
        
        # AI内容审核
        review_result, review_reason = analyze_product_content(product.product_name, product.description)
        
        if review_result == 'REJECTED':
            # 高/中风险 - 直接拒绝
            return False, review_reason
        
        elif review_result == 'NEEDS_REVIEW':
            # 低风险 - 需要人工审核
            product.product_status = 'PENDING_REVIEW'
            result_message = f'商品已提交审核，{review_reason}，请等待管理员审核。'
        
        else:  # APPROVED
            # 正常 - 直接上架
            product.product_status = 'ON_SALE'
            result_message = '商品已自动审核通过并上架！'
        
        db.session.commit()
        return True, result_message
    
    elif product.product_status == 'ON_SALE':
        product.product_status = 'OFF_SHELF'
        db.session.commit()
        return True, '商品已下架。'
    elif product.product_status == 'OFF_SHELF':
        product.product_status = 'ON_SALE'
        db.session.commit()
        return True, '商品已上架。'
    elif product.product_status == 'PENDING_REVIEW':
        return False, '商品正在审核中，请耐心等待。'
    elif product.product_status == 'REJECTED':
        # 重新提交时也要审核
        review_result, review_reason = analyze_product_content(product.product_name, product.description)
        
        if review_result == 'REJECTED':
            return False, review_reason
        
        elif review_result == 'NEEDS_REVIEW':
            product.product_status = 'PENDING_REVIEW'
            result_message = f'商品已重新提交审核，{review_reason}，请等待管理员审核。'
        
        else:
            product.product_status = 'ON_SALE'
            result_message = '商品已自动审核通过并上架！'
        
        db.session.commit()
        return True, result_message
    else:
        return False, '当前状态无法变更。'


def get_my_products(user_id, status_filter=None):
    q = Product.active().filter_by(seller_id=user_id)
    if status_filter:
        q = q.filter_by(product_status=status_filter)
    return q.order_by(Product.created_at.desc())

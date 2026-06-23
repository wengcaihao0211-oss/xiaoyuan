import os
import uuid
from datetime import datetime, timedelta
from flask import current_app
from PIL import Image

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}


def allowed_file(filename):
    """Check if the file extension is allowed."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext in ALLOWED_EXTENSIONS


def save_upload(file_storage, subfolder, prefix=''):
    """Save an uploaded file to uploads/{subfolder}/{prefix}_{uuid}.{ext}.
    Returns the relative path to the saved file.
    """
    if not file_storage or not file_storage.filename:
        return None

    ext = file_storage.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f'不支持的文件类型: .{ext}')

    filename = f"{prefix}_{uuid.uuid4().hex[:8]}.{ext}"
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(upload_dir, exist_ok=True)

    filepath = os.path.join(upload_dir, filename)

    try:
        img = Image.open(file_storage)
        img.verify()
        file_storage.seek(0)
        img = Image.open(file_storage)
        img.thumbnail((1200, 1200), Image.LANCZOS)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        img.save(filepath, quality=85, optimize=True)
    except Exception:
        raise ValueError('上传文件不是有效的图片。')

    return os.path.join('uploads', subfolder, filename).replace('\\', '/')


def mask_phone(phone):
    """Mask phone number: 138****5678."""
    if not phone or len(phone) < 7:
        return phone or ''
    return phone[:3] + '****' + phone[-4:]


def generate_order_no():
    """Generate a unique order number."""
    import time
    import random
    ts = int(time.time() * 1000)
    rnd = random.randint(1000, 9999)
    return f'XY{ts}{rnd}'


def generate_transaction_no():
    """Generate a mock transaction number."""
    import time
    import random
    ts = int(time.time() * 1000)
    rnd = random.randint(1000, 9999)
    return f'MOCK-{ts}-{rnd}'


def utc_to_beijing(utc_dt):
    """将UTC时间转换为北京时间（UTC+8）。"""
    if not utc_dt:
        return None
    # 北京时区是 UTC+8
    beijing_timedelta = timedelta(hours=8)
    return utc_dt + beijing_timedelta

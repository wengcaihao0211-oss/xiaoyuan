"""消息模块示例数据"""
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models.message import Message

app = create_app()

messages = [
    # 对话1: testuser(2) 问 cyw(3) 关于手机(2)
    (2, 3, 2, '你好，这个手机还在吗？', True, -120),
    (3, 2, 2, '在的，成色很新，功能都正常', True, -110),
    (2, 3, 2, '能便宜点吗？', True, -60),
    (3, 2, 2, '最低430了，已经很实惠了', False, -30),
    (2, 3, 2, '好的，我考虑一下', False, -10),

    # 对话2: cyw(3) 问 testuser(2) 关于东西(5)
    (3, 2, 5, '你好，这个东西包邮吗？', True, -200),
    (2, 3, 5, '包邮的，下单就发', True, -180),
    (3, 2, 5, '什么时候能发货？', True, -150),
    (2, 3, 5, '当天就发，顺丰快递', False, -20),

    # 对话3: testuser(2) 问 admin(1) 关于耳机(3)
    (2, 1, 3, '你好，耳机音质怎么样？', True, -300),
    (1, 2, 3, '很好的，降噪效果也不错', True, -280),
    (2, 1, 3, '行，我要了，怎么交易？', True, -250),
]

with app.app_context():
    now = datetime.utcnow()
    for sender, receiver, product, content, read, offset in messages:
        msg = Message(
            sender_id=sender,
            receiver_id=receiver,
            product_id=product,
            message_content=content,
            read_status=read,
            created_at=now + timedelta(minutes=offset),
            read_time=(now + timedelta(minutes=offset + 5)) if read else None,
        )
        db.session.add(msg)
    db.session.commit()
    print(f'Done! Inserted {len(messages)} messages.')

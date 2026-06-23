"""重置用户密码"""
from app import create_app
from app.extensions import db
from app.models.user import User

def reset_passwords():
    """重置指定用户的密码"""
    app = create_app('development')
    
    with app.app_context():
        # 需要重置的用户列表
        users_to_reset = ['cyw', 'testuser', 'test11', 'admin']
        new_password = '12345678a'  # 统一设置为这个密码
        
        print("[*] 重置用户密码...\n")
        
        for username in users_to_reset:
            user = User.query.filter_by(username=username).first()
            
            if user:
                user.set_password(new_password)
                db.session.add(user)
                print(f"[OK] {username} - 密码已重置为: {new_password}")
            else:
                print(f"[--] {username} - 用户不存在")
        
        db.session.commit()
        print("\n[OK] 密码重置完成！")
        
        # 显示所有用户
        print("\n[*] 当前所有用户:")
        all_users = User.query.all()
        for u in all_users:
            print(f"  - {u.username} ({u.role})")

if __name__ == '__main__':
    reset_passwords()

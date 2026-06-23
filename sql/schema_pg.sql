-- PostgreSQL / Supabase 建表脚本
-- 在 Supabase SQL Editor 中运行

CREATE TABLE users (
  user_id BIGSERIAL PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  avatar VARCHAR(500),
  phone VARCHAR(30),
  email VARCHAR(255),
  nickname VARCHAR(50),
  introduction VARCHAR(500),
  role VARCHAR(20) NOT NULL DEFAULT 'USER',
  status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
  last_login_at TIMESTAMP,
  last_login_ip VARCHAR(45),
  password_changed_at TIMESTAMP NOT NULL DEFAULT NOW(),
  session_version INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE category (
  category_id BIGSERIAL PRIMARY KEY,
  category_name VARCHAR(100) NOT NULL UNIQUE,
  description VARCHAR(500),
  status VARCHAR(20) NOT NULL DEFAULT 'ENABLED',
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE product (
  product_id BIGSERIAL PRIMARY KEY,
  seller_id BIGINT NOT NULL REFERENCES users(user_id),
  category_id BIGINT NOT NULL REFERENCES category(category_id),
  product_name VARCHAR(150) NOT NULL,
  price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
  condition_level VARCHAR(30) NOT NULL,
  description TEXT NOT NULL,
  trade_location VARCHAR(255) NOT NULL,
  product_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
  view_count BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE product_image (
  image_id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES product(product_id),
  image_url VARCHAR(500) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE favorite (
  favorite_id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(user_id),
  product_id BIGINT NOT NULL REFERENCES product(product_id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, product_id)
);

CREATE TABLE orders (
  order_id BIGSERIAL PRIMARY KEY,
  order_no VARCHAR(50) NOT NULL UNIQUE,
  product_id BIGINT NOT NULL REFERENCES product(product_id),
  buyer_id BIGINT NOT NULL REFERENCES users(user_id),
  seller_id BIGINT NOT NULL REFERENCES users(user_id),
  order_amount DECIMAL(10,2) NOT NULL CHECK (order_amount >= 0),
  trade_type VARCHAR(20) NOT NULL,
  buyer_message VARCHAR(500),
  order_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
  payment_status VARCHAR(30) NOT NULL DEFAULT 'UNPAID',
  reject_reason VARCHAR(500),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  paid_at TIMESTAMP,
  completed_at TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  deleted BOOLEAN NOT NULL DEFAULT FALSE,
  CHECK (buyer_id <> seller_id)
);

CREATE TABLE message (
  message_id BIGSERIAL PRIMARY KEY,
  sender_id BIGINT NOT NULL REFERENCES users(user_id),
  receiver_id BIGINT NOT NULL REFERENCES users(user_id),
  product_id BIGINT REFERENCES product(product_id),
  message_content TEXT NOT NULL,
  read_status BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  deleted BOOLEAN NOT NULL DEFAULT FALSE,
  CHECK (sender_id <> receiver_id)
);

CREATE TABLE review (
  review_id BIGSERIAL PRIMARY KEY,
  order_id BIGINT NOT NULL REFERENCES orders(order_id),
  reviewer_id BIGINT NOT NULL REFERENCES users(user_id),
  reviewed_user_id BIGINT NOT NULL REFERENCES users(user_id),
  score SMALLINT NOT NULL CHECK (score BETWEEN 1 AND 5),
  review_content VARCHAR(1000),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  deleted BOOLEAN NOT NULL DEFAULT FALSE,
  UNIQUE(order_id, reviewer_id),
  CHECK (reviewer_id <> reviewed_user_id)
);

CREATE TABLE report (
  report_id BIGSERIAL PRIMARY KEY,
  reporter_id BIGINT NOT NULL REFERENCES users(user_id),
  target_type VARCHAR(30) NOT NULL,
  target_id BIGINT NOT NULL,
  report_reason VARCHAR(100) NOT NULL,
  description VARCHAR(1000),
  report_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
  handle_result VARCHAR(1000),
  handler_id BIGINT REFERENCES users(user_id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  handled_at TIMESTAMP
);

CREATE TABLE notification (
  notification_id BIGSERIAL PRIMARY KEY,
  receiver_id BIGINT NOT NULL REFERENCES users(user_id),
  notification_type VARCHAR(30) NOT NULL,
  title VARCHAR(200) NOT NULL,
  content TEXT NOT NULL,
  related_id BIGINT,
  read_status BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- 索引
CREATE INDEX idx_product_seller ON product(seller_id);
CREATE INDEX idx_product_category_status ON product(category_id, product_status, deleted);
CREATE INDEX idx_product_name ON product(product_name);
CREATE UNIQUE INDEX uq_users_phone_active ON users(phone) WHERE phone IS NOT NULL AND phone <> '' AND deleted = FALSE;
CREATE UNIQUE INDEX uq_users_email_active ON users(email) WHERE email IS NOT NULL AND email <> '' AND deleted = FALSE;
CREATE INDEX idx_orders_buyer_status ON orders(buyer_id, order_status, deleted);
CREATE INDEX idx_orders_seller_status ON orders(seller_id, order_status, deleted);
CREATE INDEX idx_message_receiver ON message(receiver_id, read_status, created_at);
CREATE INDEX idx_favorite_user ON favorite(user_id);
CREATE INDEX idx_notification_receiver ON notification(receiver_id, read_status, created_at);
CREATE INDEX idx_review_reviewed ON review(reviewed_user_id, created_at);
CREATE INDEX idx_report_status ON report(report_status, created_at);

-- 种子数据：默认分类
INSERT INTO category (category_name, description) VALUES
  ('教材教辅', '课本、参考书、考试资料'),
  ('电子产品', '手机、电脑、平板、配件'),
  ('生活用品', '日用品、收纳、装饰'),
  ('服饰鞋包', '衣服、鞋子、包包、配饰'),
  ('运动户外', '运动器材、户外装备'),
  ('娱乐数码', '游戏、耳机、相机'),
  ('其他', '其他闲置物品');

-- 种子数据：管理员账号 (密码: admin123)
INSERT INTO users (username, password_hash, role, status, phone, email, nickname, introduction)
VALUES (
  'admin',
  'scrypt:32768:8:1$3Whddo0xFAIDV4F7$3441e2b519de54e17fe67bc75e939e214771a1c45e37c6671381eb5a2a81add4830d722d7c7af6c3a940510dbc86c9d48b6889d3729bbc8be3319b2e8a03b471',
  'ADMIN',
  'ACTIVE',
  '13800000000',
  'admin@example.com',
  '系统管理员',
  '系统管理员'
);

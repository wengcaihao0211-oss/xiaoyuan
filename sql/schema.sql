-- 校园二手物品交易与闲置管理系统
-- MySQL 8.0+

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `notification`;
DROP TABLE IF EXISTS `report`;
DROP TABLE IF EXISTS `review`;
DROP TABLE IF EXISTS `message`;
DROP TABLE IF EXISTS `orders`;
DROP TABLE IF EXISTS `favorite`;
DROP TABLE IF EXISTS `product_image`;
DROP TABLE IF EXISTS `product`;
DROP TABLE IF EXISTS `category`;
DROP TABLE IF EXISTS `user`;

CREATE TABLE `user` (
  `user_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户编号',
  `username` VARCHAR(50) NOT NULL COMMENT '用户名',
  `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希',
  `avatar` VARCHAR(500) DEFAULT NULL COMMENT '头像地址',
  `phone` VARCHAR(30) DEFAULT NULL COMMENT '联系方式',
  `email` VARCHAR(255) DEFAULT NULL COMMENT '邮箱',
  `nickname` VARCHAR(50) DEFAULT NULL COMMENT '昵称',
  `introduction` VARCHAR(500) DEFAULT NULL COMMENT '个人简介',
  `role` VARCHAR(20) NOT NULL DEFAULT 'USER' COMMENT '用户角色',
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT '账号状态',
  `last_login_at` DATETIME DEFAULT NULL COMMENT '最后登录时间',
  `last_login_ip` VARCHAR(45) DEFAULT NULL COMMENT '最后登录IP',
  `password_changed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '密码最近修改时间',
  `session_version` INT NOT NULL DEFAULT 1 COMMENT '会话版本号',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除标志',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uk_user_username` (`username`),
  UNIQUE KEY `uk_user_phone` (`phone`),
  UNIQUE KEY `uk_user_email` (`email`),
  KEY `idx_user_status_deleted` (`status`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户表';

CREATE TABLE `category` (
  `category_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '分类编号',
  `category_name` VARCHAR(100) NOT NULL COMMENT '分类名称',
  `description` VARCHAR(500) DEFAULT NULL COMMENT '分类描述',
  `status` VARCHAR(20) NOT NULL DEFAULT 'ENABLED' COMMENT '分类状态',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`category_id`),
  UNIQUE KEY `uk_category_name` (`category_name`),
  KEY `idx_category_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='商品分类表';

CREATE TABLE `product` (
  `product_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '商品编号',
  `seller_id` BIGINT UNSIGNED NOT NULL COMMENT '卖家编号',
  `category_id` BIGINT UNSIGNED NOT NULL COMMENT '分类编号',
  `product_name` VARCHAR(150) NOT NULL COMMENT '商品名称',
  `price` DECIMAL(10,2) NOT NULL COMMENT '商品价格',
  `condition_level` VARCHAR(30) NOT NULL COMMENT '商品成色',
  `description` TEXT NOT NULL COMMENT '商品描述',
  `trade_location` VARCHAR(255) NOT NULL COMMENT '交易地点',
  `product_status` VARCHAR(30) NOT NULL DEFAULT 'DRAFT' COMMENT '商品状态',
  `view_count` BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '浏览次数',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除标志',
  PRIMARY KEY (`product_id`),
  KEY `idx_product_seller` (`seller_id`),
  KEY `idx_product_category_status` (`category_id`, `product_status`, `deleted`),
  KEY `idx_product_name` (`product_name`),
  CONSTRAINT `fk_product_seller` FOREIGN KEY (`seller_id`) REFERENCES `user` (`user_id`),
  CONSTRAINT `fk_product_category` FOREIGN KEY (`category_id`) REFERENCES `category` (`category_id`),
  CONSTRAINT `chk_product_price` CHECK (`price` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='商品表';

CREATE TABLE `product_image` (
  `image_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '图片编号',
  `product_id` BIGINT UNSIGNED NOT NULL COMMENT '商品编号',
  `image_url` VARCHAR(500) NOT NULL COMMENT '图片地址',
  `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序号',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`image_id`),
  KEY `idx_product_image_product_sort` (`product_id`, `sort_order`),
  CONSTRAINT `fk_product_image_product` FOREIGN KEY (`product_id`) REFERENCES `product` (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='商品图片表';

CREATE TABLE `favorite` (
  `favorite_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '收藏编号',
  `user_id` BIGINT UNSIGNED NOT NULL COMMENT '用户编号',
  `product_id` BIGINT UNSIGNED NOT NULL COMMENT '商品编号',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`favorite_id`),
  UNIQUE KEY `uk_favorite_user_product` (`user_id`, `product_id`),
  KEY `idx_favorite_product` (`product_id`),
  CONSTRAINT `fk_favorite_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`user_id`),
  CONSTRAINT `fk_favorite_product` FOREIGN KEY (`product_id`) REFERENCES `product` (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='收藏表';

CREATE TABLE `orders` (
  `order_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '订单编号',
  `order_no` VARCHAR(50) NOT NULL COMMENT '订单业务编号',
  `product_id` BIGINT UNSIGNED NOT NULL COMMENT '商品编号',
  `buyer_id` BIGINT UNSIGNED NOT NULL COMMENT '买家编号',
  `seller_id` BIGINT UNSIGNED NOT NULL COMMENT '卖家编号',
  `order_amount` DECIMAL(10,2) NOT NULL COMMENT '订单金额',
  `trade_type` VARCHAR(20) NOT NULL COMMENT '交易方式',
  `buyer_message` VARCHAR(500) DEFAULT NULL COMMENT '买家留言',
  `order_status` VARCHAR(30) NOT NULL DEFAULT 'PENDING' COMMENT '订单状态',
  `payment_status` VARCHAR(30) NOT NULL DEFAULT 'UNPAID' COMMENT '支付状态',
  `reject_reason` VARCHAR(500) DEFAULT NULL COMMENT '拒绝原因',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `paid_at` DATETIME DEFAULT NULL COMMENT '支付时间',
  `completed_at` DATETIME DEFAULT NULL COMMENT '完成时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除标志',
  `active_product_id` BIGINT UNSIGNED GENERATED ALWAYS AS (
    CASE
      WHEN `deleted` = 0 AND `order_status` IN ('PENDING', 'CONFIRMED', 'PAID')
      THEN `product_id`
      ELSE NULL
    END
  ) STORED COMMENT '用于限制同一商品仅有一个有效订单',
  PRIMARY KEY (`order_id`),
  UNIQUE KEY `uk_orders_order_no` (`order_no`),
  UNIQUE KEY `uk_orders_active_product` (`active_product_id`),
  KEY `idx_orders_buyer_status` (`buyer_id`, `order_status`, `deleted`),
  KEY `idx_orders_seller_status` (`seller_id`, `order_status`, `deleted`),
  KEY `idx_orders_product` (`product_id`),
  CONSTRAINT `fk_orders_product` FOREIGN KEY (`product_id`) REFERENCES `product` (`product_id`),
  CONSTRAINT `fk_orders_buyer` FOREIGN KEY (`buyer_id`) REFERENCES `user` (`user_id`),
  CONSTRAINT `fk_orders_seller` FOREIGN KEY (`seller_id`) REFERENCES `user` (`user_id`),
  CONSTRAINT `chk_orders_amount` CHECK (`order_amount` >= 0),
  CONSTRAINT `chk_orders_users` CHECK (`buyer_id` <> `seller_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='订单表';

CREATE TABLE `message` (
  `message_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '消息编号',
  `sender_id` BIGINT UNSIGNED NOT NULL COMMENT '发送者编号',
  `receiver_id` BIGINT UNSIGNED NOT NULL COMMENT '接收者编号',
  `product_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '关联商品编号',
  `message_content` TEXT NOT NULL COMMENT '消息内容',
  `read_status` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '阅读状态',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除标志',
  PRIMARY KEY (`message_id`),
  KEY `idx_message_receiver_read_time` (`receiver_id`, `read_status`, `created_at`),
  KEY `idx_message_sender_time` (`sender_id`, `created_at`),
  KEY `idx_message_product` (`product_id`),
  CONSTRAINT `fk_message_sender` FOREIGN KEY (`sender_id`) REFERENCES `user` (`user_id`),
  CONSTRAINT `fk_message_receiver` FOREIGN KEY (`receiver_id`) REFERENCES `user` (`user_id`),
  CONSTRAINT `fk_message_product` FOREIGN KEY (`product_id`) REFERENCES `product` (`product_id`),
  CONSTRAINT `chk_message_users` CHECK (`sender_id` <> `receiver_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='消息表';

CREATE TABLE `review` (
  `review_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '评价编号',
  `order_id` BIGINT UNSIGNED NOT NULL COMMENT '订单编号',
  `reviewer_id` BIGINT UNSIGNED NOT NULL COMMENT '评价人编号',
  `reviewed_user_id` BIGINT UNSIGNED NOT NULL COMMENT '被评价人编号',
  `score` TINYINT UNSIGNED NOT NULL COMMENT '评分',
  `review_content` VARCHAR(1000) DEFAULT NULL COMMENT '评价内容',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除标志',
  PRIMARY KEY (`review_id`),
  UNIQUE KEY `uk_review_order_reviewer` (`order_id`, `reviewer_id`),
  KEY `idx_review_reviewed_user` (`reviewed_user_id`, `created_at`),
  CONSTRAINT `fk_review_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`),
  CONSTRAINT `fk_review_reviewer` FOREIGN KEY (`reviewer_id`) REFERENCES `user` (`user_id`),
  CONSTRAINT `fk_review_reviewed_user` FOREIGN KEY (`reviewed_user_id`) REFERENCES `user` (`user_id`),
  CONSTRAINT `chk_review_score` CHECK (`score` BETWEEN 1 AND 5),
  CONSTRAINT `chk_review_users` CHECK (`reviewer_id` <> `reviewed_user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='评价表';

CREATE TABLE `report` (
  `report_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '举报编号',
  `reporter_id` BIGINT UNSIGNED NOT NULL COMMENT '举报人编号',
  `target_type` VARCHAR(30) NOT NULL COMMENT '举报对象类型',
  `target_id` BIGINT UNSIGNED NOT NULL COMMENT '举报对象编号',
  `report_reason` VARCHAR(100) NOT NULL COMMENT '举报原因',
  `description` VARCHAR(1000) DEFAULT NULL COMMENT '举报说明',
  `report_status` VARCHAR(30) NOT NULL DEFAULT 'PENDING' COMMENT '处理状态',
  `handle_result` VARCHAR(1000) DEFAULT NULL COMMENT '处理结果',
  `handler_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '管理员编号',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `handled_at` DATETIME DEFAULT NULL COMMENT '处理时间',
  PRIMARY KEY (`report_id`),
  KEY `idx_report_status_time` (`report_status`, `created_at`),
  KEY `idx_report_reporter` (`reporter_id`),
  KEY `idx_report_target` (`target_type`, `target_id`),
  KEY `idx_report_handler` (`handler_id`),
  CONSTRAINT `fk_report_reporter` FOREIGN KEY (`reporter_id`) REFERENCES `user` (`user_id`),
  CONSTRAINT `fk_report_handler` FOREIGN KEY (`handler_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='举报表';

CREATE TABLE `notification` (
  `notification_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '通知编号',
  `receiver_id` BIGINT UNSIGNED NOT NULL COMMENT '接收者编号',
  `notification_type` VARCHAR(30) NOT NULL COMMENT '通知类型',
  `title` VARCHAR(200) NOT NULL COMMENT '通知标题',
  `content` TEXT NOT NULL COMMENT '通知内容',
  `related_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '关联业务编号',
  `read_status` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '阅读状态',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除标志',
  PRIMARY KEY (`notification_id`),
  KEY `idx_notification_receiver_read_time` (`receiver_id`, `read_status`, `created_at`),
  KEY `idx_notification_type_related` (`notification_type`, `related_id`),
  CONSTRAINT `fk_notification_receiver` FOREIGN KEY (`receiver_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='通知表';

SET FOREIGN_KEY_CHECKS = 1;

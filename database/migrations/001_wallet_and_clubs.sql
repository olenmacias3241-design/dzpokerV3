-- dzpokerV3/database/migrations/001_wallet_and_clubs.sql
-- 增量迁移：在已有 schema 上增加钱包与俱乐部相关表及字段
-- 适用：已存在 users、game_tables 等表，需升级到支持钱包登录与俱乐部。
-- 执行前请备份数据库。

SET NAMES utf8mb4;

-- 1) users：username、hashed_password 改为可空（若当前为 NOT NULL）
ALTER TABLE `users`
    MODIFY COLUMN `username` VARCHAR(64) DEFAULT NULL COMMENT '登录名；可选，钱包用户可后填',
    MODIFY COLUMN `hashed_password` VARCHAR(255) DEFAULT NULL COMMENT '密码哈希；可选，钱包用户可为空';

-- 2) 新增 user_wallets（若不存在）
CREATE TABLE IF NOT EXISTS `user_wallets` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` INT UNSIGNED NOT NULL,
    `chain` VARCHAR(16) NOT NULL COMMENT 'ETH|BSC|SOL|Tron',
    `address` VARCHAR(128) NOT NULL COMMENT '归一化后的链上地址',
    `is_primary` TINYINT(1) NOT NULL DEFAULT 0,
    `bound_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_chain_address` (`chain`, `address`),
    KEY `idx_user` (`user_id`),
    CONSTRAINT `fk_wallet_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户钱包绑定';

-- 3) 新增 clubs
CREATE TABLE IF NOT EXISTS `clubs` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(64) NOT NULL,
    `description` VARCHAR(512) DEFAULT NULL,
    `avatar_url` VARCHAR(512) DEFAULT NULL,
    `creator_user_id` INT UNSIGNED NOT NULL,
    `visibility` VARCHAR(32) NOT NULL DEFAULT 'public',
    `join_policy` VARCHAR(32) NOT NULL DEFAULT 'invite',
    `invite_code` VARCHAR(64) DEFAULT NULL,
    `max_members` INT UNSIGNED NOT NULL DEFAULT 100,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_invite_code` (`invite_code`),
    KEY `idx_creator` (`creator_user_id`),
    CONSTRAINT `fk_club_creator` FOREIGN KEY (`creator_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='俱乐部';

-- 4) game_tables 增加 club_id（若该列已存在则跳过本段或注释掉下面一行）
ALTER TABLE `game_tables`
    ADD COLUMN `club_id` INT UNSIGNED DEFAULT NULL COMMENT '非空=俱乐部专属牌桌' AFTER `id`,
    ADD KEY `idx_club` (`club_id`),
    ADD CONSTRAINT `fk_table_club` FOREIGN KEY (`club_id`) REFERENCES `clubs` (`id`) ON DELETE SET NULL;
-- 若报 Duplicate column name 'club_id'，说明已迁移过，可忽略。

-- 5) 新增 club_members
CREATE TABLE IF NOT EXISTS `club_members` (
    `club_id` INT UNSIGNED NOT NULL,
    `user_id` INT UNSIGNED NOT NULL,
    `role` VARCHAR(16) NOT NULL DEFAULT 'member',
    `joined_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`club_id`, `user_id`),
    KEY `idx_user` (`user_id`),
    CONSTRAINT `fk_cm_club` FOREIGN KEY (`club_id`) REFERENCES `clubs` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cm_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='俱乐部成员';

-- 6) 新增 club_join_requests
CREATE TABLE IF NOT EXISTS `club_join_requests` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `club_id` INT UNSIGNED NOT NULL,
    `user_id` INT UNSIGNED NOT NULL,
    `status` VARCHAR(16) NOT NULL DEFAULT 'pending',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `resolved_at` TIMESTAMP NULL DEFAULT NULL,
    `resolved_by` INT UNSIGNED DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_club_status` (`club_id`, `status`),
    KEY `idx_user` (`user_id`),
    CONSTRAINT `fk_cjr_club` FOREIGN KEY (`club_id`) REFERENCES `clubs` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cjr_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='俱乐部加入申请';

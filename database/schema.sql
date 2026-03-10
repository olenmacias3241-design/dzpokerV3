-- dzpokerV3/database/schema.sql
-- MySQL 数据库结构：用户、牌桌、牌局与参与记录
-- 执行前请创建数据库: CREATE DATABASE IF NOT EXISTS dzpoker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 若有旧表依赖 users，先删除（按依赖顺序，且已 SET FOREIGN_KEY_CHECKS=0）
DROP TABLE IF EXISTS `hand_participants`;
DROP TABLE IF EXISTS `game_hands`;
DROP TABLE IF EXISTS `table_seats`;
DROP TABLE IF EXISTS `game_tables`;
DROP TABLE IF EXISTS `chip_transactions`;
DROP TABLE IF EXISTS `friends`;
DROP TABLE IF EXISTS `users`;

CREATE TABLE `users` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(64) NOT NULL COMMENT '登录名，4-16 位字母数字',
    `hashed_password` VARCHAR(255) NOT NULL COMMENT '密码哈希',
    `email` VARCHAR(255) DEFAULT NULL COMMENT '邮箱，可选，用于找回密码',
    `nickname` VARCHAR(64) DEFAULT NULL COMMENT '显示昵称，可与 username 不同',
    `avatar_url` VARCHAR(512) DEFAULT NULL COMMENT '头像 URL',
    `coins_balance` BIGINT NOT NULL DEFAULT 10000 COMMENT '金币余额',
    `level` SMALLINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '等级',
    `experience_points` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '经验值',
    `total_hands_played` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '总参与手数',
    `hands_won` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '获胜手数',
    `biggest_pot_won` BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '单局最大赢得底池',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `last_login_at` TIMESTAMP NULL DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`),
    UNIQUE KEY `uk_email` (`email`),
    KEY `idx_level` (`level`),
    KEY `idx_coins` (`coins_balance`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ----------------------------
-- 牌桌表（大厅用）
-- ----------------------------
CREATE TABLE `game_tables` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `table_name` VARCHAR(64) NOT NULL COMMENT '牌桌名称',
    `small_blind` INT UNSIGNED NOT NULL COMMENT '小盲注',
    `big_blind` INT UNSIGNED NOT NULL COMMENT '大盲注',
    `min_buy_in` BIGINT UNSIGNED NOT NULL COMMENT '最小带入',
    `max_buy_in` BIGINT UNSIGNED NOT NULL COMMENT '最大带入',
    `max_players` TINYINT UNSIGNED NOT NULL DEFAULT 9,
    `status` ENUM('waiting','playing','closed') NOT NULL DEFAULT 'waiting',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_status_blinds` (`status`, `small_blind`, `big_blind`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='牌桌';

-- ----------------------------
-- 牌桌座位（当前坐在某桌的玩家）
-- ----------------------------
CREATE TABLE `table_seats` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `table_id` INT UNSIGNED NOT NULL,
    `user_id` INT UNSIGNED NOT NULL,
    `seat_number` TINYINT UNSIGNED NOT NULL COMMENT '座位号 0..max_players-1',
    `chips_at_seat` BIGINT UNSIGNED NOT NULL COMMENT '该桌当前筹码',
    `sat_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_table_seat` (`table_id`, `seat_number`),
    UNIQUE KEY `uk_table_user` (`table_id`, `user_id`),
    KEY `idx_table` (`table_id`),
    KEY `idx_user` (`user_id`),
    CONSTRAINT `fk_seat_table` FOREIGN KEY (`table_id`) REFERENCES `game_tables` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_seat_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='牌桌座位';

-- ----------------------------
-- 牌局记录（每一手）
-- ----------------------------
CREATE TABLE `game_hands` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `table_id` INT UNSIGNED NOT NULL,
    `hand_index` INT UNSIGNED NOT NULL COMMENT '该桌第几手',
    `dealer_seat` TINYINT UNSIGNED NOT NULL,
    `small_blind_seat` TINYINT UNSIGNED NOT NULL,
    `big_blind_seat` TINYINT UNSIGNED NOT NULL,
    `community_cards` VARCHAR(64) DEFAULT NULL COMMENT '如 As,Kd,5c,Th,Js',
    `final_pot_size` BIGINT UNSIGNED NOT NULL DEFAULT 0,
    `stage` VARCHAR(16) DEFAULT NULL COMMENT 'preflop/flop/turn/river/showdown',
    `started_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_table_started` (`table_id`, `started_at`),
    CONSTRAINT `fk_hand_table` FOREIGN KEY (`table_id`) REFERENCES `game_tables` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='牌局记录';

-- ----------------------------
-- 牌局参与与输赢
-- ----------------------------
CREATE TABLE `hand_participants` (
    `hand_id` BIGINT UNSIGNED NOT NULL,
    `user_id` INT UNSIGNED NOT NULL,
    `seat_number` TINYINT UNSIGNED NOT NULL,
    `hole_cards` VARCHAR(32) NOT NULL COMMENT '如 Ac,Ad',
    `has_folded` TINYINT(1) NOT NULL DEFAULT 0,
    `is_winner` TINYINT(1) NOT NULL DEFAULT 0,
    `win_amount` BIGINT NOT NULL DEFAULT 0 COMMENT '本手净输赢，正为赢',
    `total_bet_this_hand` BIGINT UNSIGNED NOT NULL DEFAULT 0,
    PRIMARY KEY (`hand_id`, `user_id`),
    KEY `idx_user` (`user_id`),
    CONSTRAINT `fk_hp_hand` FOREIGN KEY (`hand_id`) REFERENCES `game_hands` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_hp_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='牌局参与与输赢';

SET FOREIGN_KEY_CHECKS = 1;

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
DROP TABLE IF EXISTS `tournament_players`;
DROP TABLE IF EXISTS `tournament_registrations`;
DROP TABLE IF EXISTS `tournament_tables`;
DROP TABLE IF EXISTS `tournament_blind_levels`;
DROP TABLE IF EXISTS `tournament_payouts`;
DROP TABLE IF EXISTS `tournaments`;
DROP TABLE IF EXISTS `club_join_requests`;
DROP TABLE IF EXISTS `club_members`;
DROP TABLE IF EXISTS `clubs`;
DROP TABLE IF EXISTS `user_wallets`;
DROP TABLE IF EXISTS `chip_transactions`;
DROP TABLE IF EXISTS `friends`;
DROP TABLE IF EXISTS `users`;

CREATE TABLE `users` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(64) DEFAULT NULL COMMENT '登录名，4-16 位字母数字；可选，钱包用户可后填',
    `hashed_password` VARCHAR(255) DEFAULT NULL COMMENT '密码哈希；可选，钱包用户可为空',
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
-- 加密钱包绑定（多链：ETH/BSC/SOL/Tron）
-- ----------------------------
CREATE TABLE `user_wallets` (
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

-- ----------------------------
-- 俱乐部（详见 docs/requirements/11_club_design.md）
-- ----------------------------
CREATE TABLE `clubs` (
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

-- ----------------------------
-- 牌桌表（大厅用）；club_id 非空表示俱乐部专属牌桌
-- ----------------------------
CREATE TABLE `game_tables` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `club_id` INT UNSIGNED DEFAULT NULL COMMENT '非空=俱乐部专属牌桌，仅该俱乐部成员可见/可加入',
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
    KEY `idx_club` (`club_id`),
    KEY `idx_status_blinds` (`status`, `small_blind`, `big_blind`),
    CONSTRAINT `fk_table_club` FOREIGN KEY (`club_id`) REFERENCES `clubs` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='牌桌';

-- ----------------------------
-- 俱乐部成员
-- ----------------------------
CREATE TABLE `club_members` (
    `club_id` INT UNSIGNED NOT NULL,
    `user_id` INT UNSIGNED NOT NULL,
    `role` VARCHAR(16) NOT NULL DEFAULT 'member' COMMENT 'owner|admin|member',
    `joined_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`club_id`, `user_id`),
    KEY `idx_user` (`user_id`),
    CONSTRAINT `fk_cm_club` FOREIGN KEY (`club_id`) REFERENCES `clubs` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cm_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='俱乐部成员';

-- ----------------------------
-- 俱乐部加入申请
-- ----------------------------
CREATE TABLE `club_join_requests` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `club_id` INT UNSIGNED NOT NULL,
    `user_id` INT UNSIGNED NOT NULL,
    `status` VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT 'pending|approved|rejected',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `resolved_at` TIMESTAMP NULL DEFAULT NULL,
    `resolved_by` INT UNSIGNED DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_club_status` (`club_id`, `status`),
    KEY `idx_user` (`user_id`),
    CONSTRAINT `fk_cjr_club` FOREIGN KEY (`club_id`) REFERENCES `clubs` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cjr_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='俱乐部加入申请';

-- ----------------------------
-- 锦标赛（详见 docs/requirements/12_tournaments_sng_mtt.md）
-- ----------------------------
CREATE TABLE `tournaments` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(128) NOT NULL,
    `type` VARCHAR(16) NOT NULL COMMENT 'SNG|MTT',
    `buy_in` BIGINT UNSIGNED NOT NULL,
    `fee` BIGINT UNSIGNED NOT NULL DEFAULT 0,
    `starting_stack` BIGINT UNSIGNED NOT NULL,
    `max_players` INT UNSIGNED NOT NULL,
    `min_players_to_start` INT UNSIGNED NOT NULL DEFAULT 2,
    `blind_structure_json` TEXT COMMENT '级别数组 [{smallBlind,bigBlind,ante,durationMinutes}]',
    `payout_structure_json` TEXT COMMENT '奖励表 [{rankFrom,rankTo,percent,isPercent}]',
    `status` VARCHAR(32) NOT NULL DEFAULT 'Registration' COMMENT 'Registration|LateRegistration|Running|Break|Finished',
    `starts_at` TIMESTAMP NULL DEFAULT NULL COMMENT 'MTT 定时开赛',
    `late_reg_minutes` INT UNSIGNED DEFAULT NULL,
    `break_after_levels` INT UNSIGNED DEFAULT 4,
    `break_duration_minutes` INT UNSIGNED DEFAULT 5,
    `current_level_index` INT UNSIGNED NOT NULL DEFAULT 0,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_status_starts` (`status`, `starts_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='锦标赛主表';

CREATE TABLE `tournament_registrations` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `tournament_id` INT UNSIGNED NOT NULL,
    `user_id` INT UNSIGNED NOT NULL,
    `registered_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `unregistered_at` TIMESTAMP NULL DEFAULT NULL,
    `refunded_at` TIMESTAMP NULL DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_tournament_user` (`tournament_id`, `user_id`),
    KEY `idx_user` (`user_id`),
    CONSTRAINT `fk_tr_tournament` FOREIGN KEY (`tournament_id`) REFERENCES `tournaments` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_tr_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='锦标赛报名';

CREATE TABLE `tournament_blind_levels` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `tournament_id` INT UNSIGNED NOT NULL,
    `level_index` INT UNSIGNED NOT NULL,
    `small_blind` BIGINT UNSIGNED NOT NULL,
    `big_blind` BIGINT UNSIGNED NOT NULL,
    `ante` BIGINT UNSIGNED NOT NULL DEFAULT 0,
    `duration_minutes` INT UNSIGNED NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_tournament_level` (`tournament_id`, `level_index`),
    CONSTRAINT `fk_tbl_tournament` FOREIGN KEY (`tournament_id`) REFERENCES `tournaments` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='锦标赛盲注级别';

CREATE TABLE `tournament_payouts` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `tournament_id` INT UNSIGNED NOT NULL,
    `rank_from` INT UNSIGNED NOT NULL,
    `rank_to` INT UNSIGNED NOT NULL,
    `percent_value` DECIMAL(10,4) NOT NULL,
    `is_percent` TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (`id`),
    KEY `idx_tournament` (`tournament_id`),
    CONSTRAINT `fk_tp_tournament` FOREIGN KEY (`tournament_id`) REFERENCES `tournaments` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='锦标赛奖励分配';

CREATE TABLE `tournament_tables` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `tournament_id` INT UNSIGNED NOT NULL,
    `table_number` INT UNSIGNED NOT NULL COMMENT '赛事内桌号',
    `status` VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT 'active|merged',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_tournament` (`tournament_id`),
    CONSTRAINT `fk_tt_tournament` FOREIGN KEY (`tournament_id`) REFERENCES `tournaments` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='锦标赛牌桌';

CREATE TABLE `tournament_players` (
    `tournament_id` INT UNSIGNED NOT NULL,
    `user_id` INT UNSIGNED NOT NULL,
    `table_id` INT UNSIGNED DEFAULT NULL COMMENT '当前所在 tournament_tables.id',
    `seat_index` INT UNSIGNED DEFAULT NULL,
    `chips` BIGINT UNSIGNED NOT NULL COMMENT '当前记分牌',
    `rank` INT UNSIGNED DEFAULT NULL COMMENT '淘汰名次，NULL=仍在比赛中',
    `eliminated_at` TIMESTAMP NULL DEFAULT NULL,
    `prize_amount` BIGINT UNSIGNED DEFAULT 0,
    PRIMARY KEY (`tournament_id`, `user_id`),
    KEY `idx_table` (`table_id`),
    CONSTRAINT `fk_tpl_tournament` FOREIGN KEY (`tournament_id`) REFERENCES `tournaments` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_tpl_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_tpl_table` FOREIGN KEY (`table_id`) REFERENCES `tournament_tables` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='锦标赛玩家状态';

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

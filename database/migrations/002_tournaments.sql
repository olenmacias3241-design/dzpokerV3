-- dzpokerV3/database/migrations/002_tournaments.sql
-- 增量迁移：增加锦标赛 6 张表（详见 docs/requirements/12_tournaments_sng_mtt.md）
-- 执行前请备份数据库。

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS `tournaments` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(128) NOT NULL,
    `type` VARCHAR(16) NOT NULL,
    `buy_in` BIGINT UNSIGNED NOT NULL,
    `fee` BIGINT UNSIGNED NOT NULL DEFAULT 0,
    `starting_stack` BIGINT UNSIGNED NOT NULL,
    `max_players` INT UNSIGNED NOT NULL,
    `min_players_to_start` INT UNSIGNED NOT NULL DEFAULT 2,
    `blind_structure_json` TEXT,
    `payout_structure_json` TEXT,
    `status` VARCHAR(32) NOT NULL DEFAULT 'Registration',
    `starts_at` TIMESTAMP NULL DEFAULT NULL,
    `late_reg_minutes` INT UNSIGNED DEFAULT NULL,
    `break_after_levels` INT UNSIGNED DEFAULT 4,
    `break_duration_minutes` INT UNSIGNED DEFAULT 5,
    `current_level_index` INT UNSIGNED NOT NULL DEFAULT 0,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_status_starts` (`status`, `starts_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `tournament_registrations` (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `tournament_blind_levels` (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `tournament_payouts` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `tournament_id` INT UNSIGNED NOT NULL,
    `rank_from` INT UNSIGNED NOT NULL,
    `rank_to` INT UNSIGNED NOT NULL,
    `percent_value` DECIMAL(10,4) NOT NULL,
    `is_percent` TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (`id`),
    KEY `idx_tournament` (`tournament_id`),
    CONSTRAINT `fk_tp_tournament` FOREIGN KEY (`tournament_id`) REFERENCES `tournaments` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `tournament_tables` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `tournament_id` INT UNSIGNED NOT NULL,
    `table_number` INT UNSIGNED NOT NULL,
    `status` VARCHAR(16) NOT NULL DEFAULT 'active',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_tournament` (`tournament_id`),
    CONSTRAINT `fk_tt_tournament` FOREIGN KEY (`tournament_id`) REFERENCES `tournaments` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `tournament_players` (
    `tournament_id` INT UNSIGNED NOT NULL,
    `user_id` INT UNSIGNED NOT NULL,
    `table_id` INT UNSIGNED DEFAULT NULL,
    `seat_index` INT UNSIGNED DEFAULT NULL,
    `chips` BIGINT UNSIGNED NOT NULL,
    `rank` INT UNSIGNED DEFAULT NULL,
    `eliminated_at` TIMESTAMP NULL DEFAULT NULL,
    `prize_amount` BIGINT UNSIGNED DEFAULT 0,
    PRIMARY KEY (`tournament_id`, `user_id`),
    KEY `idx_table` (`table_id`),
    CONSTRAINT `fk_tpl_tournament` FOREIGN KEY (`tournament_id`) REFERENCES `tournaments` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_tpl_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_tpl_table` FOREIGN KEY (`table_id`) REFERENCES `tournament_tables` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

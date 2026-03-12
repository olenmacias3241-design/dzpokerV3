# 06 - 数据库表结构

这是一个简化的 V1 版本数据库 Schema，使用 SQL 风格定义。

### `users`
存储用户信息（账号密码与钱包用户统一用本表）。**username / hashed_password 均为可选（可为 NULL）**，以支持仅使用钱包登录、尚未设置账号密码的用户。
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255) UNIQUE,                    -- 可选，钱包用户可后填
    hashed_password VARCHAR(255),                   -- 可选，钱包用户可为空
    email VARCHAR(255) UNIQUE,
    coins_balance BIGINT DEFAULT 10000,
    avatar_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

### `user_wallets`（加密钱包绑定）
存储用户与链上地址的绑定关系；同一用户可绑定多条链、多个地址。
```sql
CREATE TABLE user_wallets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    chain VARCHAR(16) NOT NULL,                    -- 'ETH'|'BSC'|'SOL'|'Tron'
    address VARCHAR(128) NOT NULL,                  -- 归一化后的地址
    is_primary BOOLEAN DEFAULT FALSE,
    bound_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY (chain, address),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### `game_hands`
记录每一手牌局的历史，用于数据分析和牌谱回顾。
```sql
CREATE TABLE game_hands (
    id INT PRIMARY KEY AUTO_INCREMENT,
    table_id INT NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    community_cards VARCHAR(255), -- e.g., "As,Kd,5c,Th,Js"
    final_pot_size BIGINT
);
```

### `hand_participants`
记录一手牌中有哪些玩家参与，以及他们的手牌和输赢。
```sql
CREATE TABLE hand_participants (
    hand_id INT NOT NULL,
    user_id INT NOT NULL,
    seat_number INT NOT NULL,
    hole_cards VARCHAR(255) NOT NULL, -- e.g., "Ac,Ad"
    win_amount BIGINT NOT NULL DEFAULT 0, -- 赢为正，输为负
    PRIMARY KEY (hand_id, user_id),
    FOREIGN KEY (hand_id) REFERENCES game_hands(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 俱乐部相关（详见 docs/requirements/11_club_design.md）

### `clubs`
```sql
CREATE TABLE clubs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(64) NOT NULL,
    description VARCHAR(512),
    avatar_url VARCHAR(255),
    creator_user_id INT NOT NULL,
    visibility VARCHAR(32) NOT NULL DEFAULT 'public',
    join_policy VARCHAR(32) NOT NULL DEFAULT 'invite',
    invite_code VARCHAR(64) UNIQUE,
    max_members INT DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (creator_user_id) REFERENCES users(id)
);
```

### `club_members`
```sql
CREATE TABLE club_members (
    club_id INT NOT NULL,
    user_id INT NOT NULL,
    role VARCHAR(16) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (club_id, user_id),
    FOREIGN KEY (club_id) REFERENCES clubs(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### `club_join_requests`
```sql
CREATE TABLE club_join_requests (
    id INT PRIMARY KEY AUTO_INCREMENT,
    club_id INT NOT NULL,
    user_id INT NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    resolved_by INT NULL,
    FOREIGN KEY (club_id) REFERENCES clubs(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 牌桌表 (tables) 与 club_id
牌桌主表（定义见后端或 database/SCHEMA.md）需增加 **club_id** 可空字段：非空表示该牌桌为俱乐部专属牌桌，仅该俱乐部成员可见/可加入。
```sql
-- ALTER TABLE tables ADD COLUMN club_id INT NULL REFERENCES clubs(id);
```

### 锦标赛相关（详见 docs/requirements/12_tournaments_sng_mtt.md）

### `tournaments`
```sql
CREATE TABLE tournaments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(128) NOT NULL,
    type VARCHAR(16) NOT NULL,                      -- 'SNG'|'MTT'
    buy_in BIGINT NOT NULL,
    fee BIGINT NOT NULL DEFAULT 0,
    starting_stack BIGINT NOT NULL,
    max_players INT NOT NULL,
    min_players_to_start INT NOT NULL DEFAULT 2,
    blind_structure_json TEXT,                     -- 级别数组 [{smallBlind,bigBlind,ante,durationMinutes}]
    payout_structure_json TEXT,                   -- 奖励表 [{rankFrom,rankTo,percent,isPercent}]
    status VARCHAR(32) NOT NULL DEFAULT 'Registration', -- Registration|LateRegistration|Running|Break|Finished
    starts_at TIMESTAMP NULL,                      -- MTT 定时开赛
    late_reg_minutes INT NULL,                     -- MTT 晚报名时长(分钟)
    break_after_levels INT NULL DEFAULT 4,
    break_duration_minutes INT NULL DEFAULT 5,
    current_level_index INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### `tournament_registrations`
```sql
CREATE TABLE tournament_registrations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    tournament_id INT NOT NULL,
    user_id INT NOT NULL,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    unregistered_at TIMESTAMP NULL,
    refunded_at TIMESTAMP NULL,
    UNIQUE KEY (tournament_id, user_id),
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### `tournament_players`
```sql
CREATE TABLE tournament_players (
    tournament_id INT NOT NULL,
    user_id INT NOT NULL,
    table_id INT NULL,                             -- 当前所在桌
    seat_index INT NULL,
    chips BIGINT NOT NULL,                         -- 当前记分牌
    rank INT NULL,                                 -- 淘汰名次，NULL 表示仍在比赛中
    eliminated_at TIMESTAMP NULL,
    prize_amount BIGINT NULL DEFAULT 0,
    PRIMARY KEY (tournament_id, user_id),
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### `tournament_tables`
```sql
CREATE TABLE tournament_tables (
    id INT PRIMARY KEY AUTO_INCREMENT,
    tournament_id INT NOT NULL,
    table_number INT NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'active',   -- active|merged
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
);
```

### `tournament_blind_levels`
```sql
CREATE TABLE tournament_blind_levels (
    id INT PRIMARY KEY AUTO_INCREMENT,
    tournament_id INT NOT NULL,
    level_index INT NOT NULL,
    small_blind BIGINT NOT NULL,
    big_blind BIGINT NOT NULL,
    ante BIGINT NOT NULL DEFAULT 0,
    duration_minutes INT NOT NULL,
    UNIQUE KEY (tournament_id, level_index),
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
);
```

### `tournament_payouts`
```sql
CREATE TABLE tournament_payouts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    tournament_id INT NOT NULL,
    rank_from INT NOT NULL,
    rank_to INT NOT NULL,
    percent_value DECIMAL(10,4) NOT NULL,          -- 比例或固定金额
    is_percent BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
);
```

### 约局相关（详见 docs/requirements/13_scheduled_game_mode.md）

### `scheduled_games`
```sql
CREATE TABLE scheduled_games (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(128) NOT NULL,
    host_user_id INT NOT NULL,
    club_id INT NULL,
    start_at TIMESTAMP NOT NULL,
    start_rule VARCHAR(32) NOT NULL DEFAULT 'scheduled_or_full',
    min_players INT NOT NULL DEFAULT 2,
    max_players INT NOT NULL,
    blinds_json VARCHAR(128) NOT NULL,
    buy_in_min BIGINT NULL,
    buy_in_max BIGINT NULL,
    initial_chips BIGINT NULL,
    password_hash VARCHAR(255) NULL,
    invite_code VARCHAR(64) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL DEFAULT 'Scheduled',
    table_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (host_user_id) REFERENCES users(id),
    FOREIGN KEY (club_id) REFERENCES clubs(id)
);
```

### `scheduled_game_players`
```sql
CREATE TABLE scheduled_game_players (
    scheduled_game_id INT NOT NULL,
    user_id INT NOT NULL,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    seat_order INT NOT NULL DEFAULT 0,
    PRIMARY KEY (scheduled_game_id, user_id),
    FOREIGN KEY (scheduled_game_id) REFERENCES scheduled_games(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

牌桌表可选增加 **scheduled_game_id** 可空字段。
```sql
-- ALTER TABLE tables ADD COLUMN scheduled_game_id INT NULL REFERENCES scheduled_games(id);
```

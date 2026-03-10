# 06 - 数据库表结构

这是一个简化的 V1 版本数据库 Schema，使用 SQL 风格定义。

### `users`
存储用户信息。
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    coins_balance BIGINT DEFAULT 10000,
    avatar_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
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

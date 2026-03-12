# DZ-PokerV3 Database Schema

This document outlines the database schema for persisting game state. The goal is to ensure that any game can be fully reconstructed from the database after a server restart or disconnection.

We will use SQLAlchemy as the ORM.

## Table of Contents
1.  `users` - User accounts（支持账号密码与钱包双模式）
2.  `user_wallets` - 加密钱包绑定（多链）
3.  `clubs` - 俱乐部
4.  `club_members` - 俱乐部成员
5.  `club_join_requests` - 俱乐部加入申请
6.  `game_tables` - Poker tables（含 club_id 俱乐部专属牌桌）
7.  `table_seats` - Player state at a table
8.  `hands` / `game_hands` - Individual hands/rounds
9.  `hand_actions` / `hand_participants` - Actions and participants

---

### 1. `users` Table
Stores registered user information. **username** and **hashed_password** are **optional (nullable)** to support wallet-only users（见 docs/requirements/10_encrypted_wallet_user.md）；钱包用户可后补账号密码。

-   `id` (Integer, Primary Key, Auto-increment)
-   `username` (String, Unique, **Nullable**)
-   `hashed_password` (String, **Nullable**)
-   `email` (String, Unique, Nullable)
-   `nickname`, `avatar_url`, `coins_balance`, `level`, `experience_points`, stats, timestamps

---

### 2. `user_wallets` Table（加密钱包绑定）
用户与链上地址绑定；支持 ETH、BSC、SOL、Tron。同一用户可绑定多条链、多个地址。详见 docs/requirements/10。

-   `id`, `user_id` (FK -> users.id)
-   `chain` (VARCHAR: ETH|BSC|SOL|Tron)
-   `address` (VARCHAR, 归一化地址)
-   `is_primary` (Boolean), `bound_at` (Timestamp)
-   UNIQUE (chain, address)

---

### 3. `clubs` Table
俱乐部主表。详见 docs/requirements/11_club_design.md。

-   `id`, `name`, `description`, `avatar_url`, `creator_user_id`
-   `visibility`, `join_policy`, `invite_code`, `max_members`
-   `created_at`, `updated_at`

---

### 4. `club_members` Table
-   `club_id`, `user_id`, `role` (owner|admin|member), `joined_at`
-   PRIMARY KEY (club_id, user_id)

---

### 5. `club_join_requests` Table
-   `id`, `club_id`, `user_id`, `status` (pending|approved|rejected)
-   `created_at`, `resolved_at`, `resolved_by`

---

### 6. `game_tables` Table
-   `id`, **`club_id` (Nullable, FK -> clubs.id)**：非空表示俱乐部专属牌桌，仅该俱乐部成员可见/可加入
-   `table_name`, `small_blind`, `big_blind`, `min_buy_in`, `max_buy_in`, `max_players`, `status`, timestamps

---

### 7. `table_seats` Table
Represents a player currently sitting at a table. This stores the dynamic state of a player in the context of a table.

-   `id` (Integer, Primary Key, Auto-increment)
-   `table_id` (Integer, Foreign Key -> `game_tables.id`)
-   `user_id` (Integer, Foreign Key -> `users.id`, Unique per table)
-   `seat_number` (Integer, Not Null)
-   `stack` (Integer, Not Null) - The player's current chip stack at this table.
-   `is_in_hand` (Boolean, Default: False) - Is the player participating in the current hand?

---

### 8. `hands` / `game_hands` Table
A record for every single hand played. This is crucial for history and for reconstructing an interrupted game.

-   `id` (Integer, Primary Key, Auto-increment)
-   `table_id` (Integer, Foreign Key -> `game_tables.id`)
-   `start_time` (DateTime, Default: NOW())
-   `end_time` (DateTime)
-   `status` (Enum: 'preflop', 'flop', 'turn', 'river', 'showdown', 'ended')
-   `dealer_button_position` (Integer) - The seat number of the dealer.
-   `community_cards` (String) - e.g., "AH,KD,TC,7S,3D"
-   `pot_size` (Integer, Default: 0)
-   `deck_cards` (String) - The state of the deck at the start of the hand.

---

### 9. `hand_actions` / `hand_participants` Table
Logs every single action a player takes. This provides a complete audit trail and is the ultimate source for reconstructing a hand's state.

-   `id` (Integer, Primary Key, Auto-increment)
-   `hand_id` (Integer, Foreign Key -> `hands.id`)
-   `user_id` (Integer, Foreign Key -> `users.id`)
-   `action_type` (Enum: 'post_sb', 'post_bb', 'fold', 'check', 'bet', 'call', 'raise')
-   `amount` (Integer) - The amount of the bet, call, or raise.
-   `action_timestamp` (DateTime, Default: NOW())

---

## Reconstruction Logic
When the server restarts:
1.  Query `game_tables` for any table with `status = 'playing'`.
2.  For each playing table, load its associated `table_seats`.
3.  Find the most recent `hands` record for that table with a status that is not 'ended'.
4.  Replay all `hand_actions` for that hand to reconstruct the current pot, player bets, and whose turn it is.
5.  Reconstruct the deck and deal cards based on the hand record and player actions to arrive at the exact state before the crash.

This schema provides a robust foundation for full game state persistence.

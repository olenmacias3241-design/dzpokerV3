# DZ-PokerV3 Database Schema

This document outlines the database schema for persisting game state. The goal is to ensure that any game can be fully reconstructed from the database after a server restart or disconnection.

We will use SQLAlchemy as the ORM.

## Table of Contents
1.  `users` - User accounts
2.  `game_tables` - Poker tables
3.  `table_seats` - Player state at a table
4.  `hands` - Individual hands/rounds played at a table
5.  `hand_actions` - A log of every action within a hand

---

### 1. `users` Table
Stores registered user information.

-   `id` (Integer, Primary Key, Auto-increment)
-   `username` (String, Unique, Not Null)
-   `password_hash` (String, Not Null)
-   `email` (String, Unique)
-   `coins_balance` (Integer, Default: 10000)
-   `created_at` (DateTime, Default: NOW())

---

### 2. `game_tables` Table
Stores the static configuration and current status of each poker table.

-   `id` (Integer, Primary Key, Auto-increment)
-   `table_name` (String)
-   `status` (Enum: 'waiting', 'playing', 'ended', Default: 'waiting')
-   `sb_amount` (Integer, Not Null)
-   `bb_amount` (Integer, Not Null)
-   `max_players` (Integer, Default: 9)
-   `min_buy_in` (Integer)
-   `max_buy_in` (Integer)
-   `created_at` (DateTime, Default: NOW())

---

### 3. `table_seats` Table
Represents a player currently sitting at a table. This stores the dynamic state of a player in the context of a table.

-   `id` (Integer, Primary Key, Auto-increment)
-   `table_id` (Integer, Foreign Key -> `game_tables.id`)
-   `user_id` (Integer, Foreign Key -> `users.id`, Unique per table)
-   `seat_number` (Integer, Not Null)
-   `stack` (Integer, Not Null) - The player's current chip stack at this table.
-   `is_in_hand` (Boolean, Default: False) - Is the player participating in the current hand?

---

### 4. `hands` Table
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

### 5. `hand_actions` Table
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

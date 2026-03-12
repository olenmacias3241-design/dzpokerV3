# 需求文档 (Requirements)

本目录集中存放项目全部需求与规格文档，按数字前缀排序阅读。

## 文档列表

| 编号 | 文档 | 说明 |
|------|------|------|
| 00 | [00_overview.md](00_overview.md) | 项目目标、用户、核心功能 |
| 01 | [01_user_system.md](01_user_system.md) | 用户注册/登录、个人资料、钱包概述 |
| 02 | [02_game_lobby.md](02_game_lobby.md) | 大厅、牌桌列表、快速匹配 |
| 03 | [03_game_table_core_logic.md](03_game_table_core_logic.md) | **核心** 游戏流程、下注、比牌、底池 |
| 04 | [04_game_table_ui_ux.md](04_game_table_ui_ux.md) | 牌桌 UI/UX |
| 05 | [05_api_definitions.md](05_api_definitions.md) | **关键** API / WebSocket 定义 |
| 06 | [06_database_schema.md](06_database_schema.md) | **关键** 数据库表结构 |
| 07 | [07_non_functional_requirements.md](07_non_functional_requirements.md) | 非功能需求 |
| 08 | [08_future_features.md](08_future_features.md) | 未来功能迭代 |
| 09 | [09_ui_ux_animations.md](09_ui_ux_animations.md) | UI/UX 动效 |
| 10 | [10_encrypted_wallet_user.md](10_encrypted_wallet_user.md) | 加密钱包用户（BSC/ETH/SOL/Tron） |
| 11 | [11_club_design.md](11_club_design.md) | 俱乐部设计 |
| 12 | [12_tournaments_sng_mtt.md](12_tournaments_sng_mtt.md) | 锦标赛 SNG/MTT |
| 13 | [13_scheduled_game_mode.md](13_scheduled_game_mode.md) | 约局模式 |
| — | [TURN_ORDER.md](TURN_ORDER.md) | 行动顺序补充 |

## 使用

- **入口**：先读 `00_overview.md`，再按模块查阅对应编号。
- **在 Cursor 中**：可 `@docs/requirements/05_api_definitions.md` 等引用。
- **完整索引**：见 `docs/knowledge/README.md`（含「何时 @」说明）。

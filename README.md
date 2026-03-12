# 项目：在线德州扑克 v3 (dzpokerV3)

本项目旨在开发一款功能完整、稳定流畅的多人在线德州扑克游戏平台。

本文档库包含了项目的所有细化需求、技术规格和设计指南。

## 文档结构

所有详细规格文档都位于 `docs/requirements/` 目录下，并按数字前缀排序以提供阅读顺序：

- **[00_overview.md](./docs/requirements/00_overview.md)**: 项目目标、目标用户和核心功能概览。
- **[01_user_system.md](./docs/requirements/01_user_system.md)**: 用户注册、登录、个人资料等功能规格。
- **[02_game_lobby.md](./docs/requirements/02_game_lobby.md)**: 游戏大厅、牌桌列表、快速匹配等功能规格。
- **[03_game_table_core_logic.md](./docs/requirements/03_game_table_core_logic.md)**: **（核心）** 游戏流程、下注、比牌、底池分配等核心玩法逻辑的详细定义。
- **[04_game_table_ui_ux.md](./docs/requirements/04_game_table_ui_ux.md)**: 游戏牌桌的界面元素、交互流程和用户体验细节。
- **[05_api_definitions.md](./docs/requirements/05_api_definitions.md)**: **（关键）** 前后端通信接口定义，主要为 WebSocket 事件。
- **[06_database_schema.md](./docs/requirements/06_database_schema.md)**: **（关键）** 数据库表结构设计。
- **[07_non_functional_requirements.md](./docs/requirements/07_non_functional_requirements.md)**: 性能、安全、公平性等非功能性要求。
- **[08_future_features.md](./docs/requirements/08_future_features.md)**: V1 版本之后的功能迭代计划。

## 如何开始

1.  从阅读 `docs/requirements/00_overview.md` 开始，了解项目全貌。
2.  后端开发人员应重点关注 `03`, `05`, `06`。
3.  前端开发人员应重点关注 `02`, `04`, `05`。

**多 Chat 协作**：若用多个 Cursor Chat 分工开发，请使用 [TASKS.md](./TASKS.md) 管理任务状态，并按 [docs/CHAT_ROLES.md](./docs/CHAT_ROLES.md) 中的角色开场白复制到各 Chat 使用。

## 本地运行

- **启动服务**（默认端口 5001，避免与 macOS 隔空播放冲突）：
  ```bash
  cd dzpokerV3 && pip install -r requirements.txt && python app.py
  ```
- **游客登录（无需数据库）**：浏览器打开 `/lobby`，输入昵称点「登录」，即可建桌、加入、双人对战。
- **启用注册/登录（需 MySQL）**：若出现「数据库连接失败」：
  1. 启动 MySQL，在项目根下可建 `.env`（或设置环境变量）：`MYSQL_HOST=127.0.0.1`、`MYSQL_PORT=3306`、`MYSQL_USER=root`、`MYSQL_PASSWORD=你的密码`、`MYSQL_DATABASE=dzpoker`
  2. 初始化库与表：`cd dzpokerV3 && python -m database.connection`
  完成后即可使用「注册」「账号密码登录」。

## 服务端与客户端分离

- **服务端**：监管所有牌桌（本进程维护 TABLES、游戏逻辑、WebSocket 按桌推送）。
- **客户端**：仅实时监控当前单局牌桌（单 table_id + token，单 WebSocket room）。
- 前后端分离部署时，在页面中设置 `window.DZPOKER_API_BASE` 与 `window.DZPOKER_WS_URL` 指向服务端地址即可。
- 详见 **[ARCHITECTURE.md](./ARCHITECTURE.md)**。

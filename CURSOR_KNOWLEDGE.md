# Cursor 知识库体系 · dzpokerV3

在 Cursor 里用好「规则 + 文档」可以显著加快本项目的开发和答疑。本文说明如何搭建和使用。

**知识库入口**：**`docs/knowledge/README.md`** — 内含全部规格与知识文档的索引入口，按模块分类并标注何时 @ 引用。

---

## 一、知识库组成

### 1. Cursor 规则（`.cursor/rules/`）

- **作用**：每次对话/编辑时，AI 会按规则注入项目约定和文档索引，无需你每次重复说明。
- **位置**：`.cursor/rules/*.mdc`
- **本仓库已包含**：
  - `project-context.mdc`：项目全局约定（必读 README、ARCHITECTURE、职责划分）
  - `backend.mdc`：后端开发时引用（API、tables、core、database；钱包/俱乐部/锦标赛/约局见 docs/requirements/10、11、12、13）
  - `frontend.mdc`：前端开发时引用（templates、static、大厅/商城/牌桌页）
  - `poker-logic.mdc`：改游戏逻辑时引用（扑克规则、docs/requirements/03、知识库）

打开对应类型文件时，相关规则会自动生效。

### 2. 项目文档（给 AI 和你自己看）

**完整索引与「何时 @」说明见 `docs/knowledge/README.md`**。下表为快速对照：

| 文档 | 用途 |
|------|------|
| **README.md** | 项目入口、文档结构、本地运行、前后端分离 |
| **ARCHITECTURE.md** | 服务端/客户端职责、数据流、协作流程 |
| **docs/requirements/00_overview.md** | 项目目标、用户、核心功能 |
| **docs/requirements/01_user_system.md** | 用户/注册/登录（含钱包概述） |
| **docs/requirements/02_game_lobby.md** | 大厅、牌桌列表、快速匹配 |
| **docs/requirements/03_game_table_core_logic.md** | 游戏流程、下注、比牌、底池（核心） |
| **docs/requirements/04_game_table_ui_ux.md** | 牌桌 UI/UX |
| **docs/requirements/05_api_definitions.md** | API / WebSocket 定义（关键） |
| **docs/requirements/06_database_schema.md** | 数据库表结构 |
| **docs/requirements/10_encrypted_wallet_user.md** | 加密钱包用户系统（BSC/ETH/SOL/Tron） |
| **docs/requirements/11_club_design.md** | 俱乐部设计（创建、成员、俱乐部牌桌） |
| **docs/requirements/12_tournaments_sng_mtt.md** | 锦标赛规格（SNG、MTT 标准赛事） |
| **docs/requirements/13_scheduled_game_mode.md** | 约局模式（预约牌局、定时/满人即开、邀请、俱乐部） |
| **docs/knowledge/TEXAS_HOLDEM_PLAY_AND_RULES.md** | 标准德州扑克玩法与打牌需求（完整规则） |
| **docs/knowledge/POKER_KNOWLEDGE_BASE.md** | 德州扑克术语与规则（改逻辑时参考） |
| **database/SCHEMA.md** | 数据库说明 |

其中 **docs/requirements/10、11、12、13** 为扩展规格；**docs/knowledge/** 下为知识库本体。

---

## 二、如何「快速完成开发」

### 1. 让规则自动生效

- 规则已按「文件类型」配置：编辑 `app.py`、`tables.py`、`core/*.py` 时，后端规则会带上 ARCHITECTURE、API、数据库等上下文。
- 编辑 `templates/*.html`、`static/*.js`、`static/*.css` 时，前端规则会带上大厅/商城/牌桌页和静态资源约定。
- 编辑 `core/game_logic.py`、`core/logic.py` 时，会带上扑克规则和 docs/requirements/03。

**无需额外操作**，在对应文件里提问或让 AI 改代码即可。

### 2. 主动 @ 文档（需要更细的规格时）

在 Cursor 聊天或 Composer 里可以：

- `@ARCHITECTURE.md`：问数据流、前后端职责、部署。
- `@docs/requirements/05_api_definitions.md`：问接口、WebSocket 事件。
- `@docs/requirements/03_game_table_core_logic.md`：问下注回合、比牌、底池分配。
- `@docs/knowledge/POKER_KNOWLEDGE_BASE.md`：问术语、流程、牌型。
- `@docs/knowledge/TEXAS_HOLDEM_PLAY_AND_RULES.md`：问完整玩法、行动校验、边池。
- `@docs/requirements/10_encrypted_wallet_user.md`：问钱包登录、四链验签、绑定 API。
- `@docs/requirements/11_club_design.md`：问俱乐部、成员角色、俱乐部牌桌。
- `@docs/requirements/12_tournaments_sng_mtt.md`：问 SNG/MTT、报名、盲注结构、换桌合桌、奖励圈。
- `@docs/requirements/13_scheduled_game_mode.md`：问约局、创建预约牌局、定时开赛、邀请链接、俱乐部内约局。
- `@docs/knowledge/README.md`：查知识库与规格的完整索引。
- `@README.md`：问怎么跑、文档结构。

这样 AI 会直接引用这些文件回答，减少偏差。

### 3. 新功能开发流程建议

1. **先看规格**：在 `docs/requirements/` 里找到对应编号（如大厅→02，牌桌逻辑→03，API→05）。
2. **后端**：改 `app.py` / `tables.py` / `core/*` 时，规则会带上 ARCHITECTURE 和 API；涉及游戏规则再 @ `docs/requirements/03` 或 `docs/knowledge/POKER_KNOWLEDGE_BASE.md`。
3. **前端**：改 `templates/`、`static/` 时，规则会带上现有页面和静态资源；需要接口细节时 @ `docs/requirements/05_api_definitions.md`。
4. **联调**：按 ARCHITECTURE.md 的数据流：登录 → 大厅 → 牌桌页 → WebSocket，对照 API 与事件即可。

### 4. 维护知识库

- **新增约定**：在 `.cursor/rules/` 下加新的 `.mdc`，用 `globs` 限定到相关文件，或 `alwaysApply: true` 做全局约定。
- **规格变更**：改 `docs/requirements/` 或 ARCHITECTURE 后，规则里已经通过「请参考 xxx」指向这些文件，AI 会读到最新内容；若新开了一个重要文档，可在对应规则的 description 或内容里补一句「参考 xxx.md」。

---

## 三、小结

- **规则**：在 `.cursor/rules/`，按文件类型自动注入项目约定和文档索引。
- **文档**：README、ARCHITECTURE、docs/requirements/、docs/knowledge/ 等，用 @ 引用可快速对齐规格。**知识库索引入口**：`docs/knowledge/README.md`。
- **习惯**：做哪块就打开哪类文件（后端/前端/逻辑），需要细节时 @ 具体 spec 或知识库，即可在 Cursor 里快速完成项目开发。

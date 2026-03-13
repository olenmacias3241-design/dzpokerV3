# 知识库 (Knowledge Base) · dzpokerV3

本目录为**项目知识库入口**：集中存放德州扑克规则与术语，并索引全部规格文档（specs）及关联说明，供开发、测试与 AI 引用。

---

## 一、知识库内文档（本目录）

| 文档 | 说明 | 何时 @ |
|------|------|--------|
| **[POKER_KNOWLEDGE_BASE.md](POKER_KNOWLEDGE_BASE.md)** | 德州扑克术语与策略：标准规则摘要、基本术语、游戏流程、位置与策略、数学基础、高级策略、锦标赛策略（ICM 等） | 改比牌/下注逻辑、做产品文案、查术语时 |
| **[TEXAS_HOLDEM_PLAY_AND_RULES.md](TEXAS_HOLDEM_PLAY_AND_RULES.md)** | 标准德州扑克玩法与打牌需求：牌具、牌型、比牌、一局流程、座位与盲注、玩家行动与校验、下注轮、底池与边池、特殊局面 | 实现/裁判规则、写 HandEvaluator、边池与行动校验时 |

---

## 二、规格文档索引（docs/requirements/）

按模块分类，便于「先学后引用」。

### 项目与入口

| 文档 | 说明 | 何时 @ |
|------|------|--------|
| **docs/requirements/00_overview.md** | 项目目标、目标用户、V1 核心功能范围 | 确认范围、排期、需求边界 |
| **README.md**（项目根） | 文档结构、本地运行、前后端分离 | 上手、跑项目、文档导航 |
| **ARCHITECTURE.md** | 服务端/客户端职责、数据流、登录→大厅→牌桌协作 | 架构、联调、部署 |

### 用户与认证

| 文档 | 说明 | 何时 @ |
|------|------|--------|
| **docs/requirements/01_user_system.md** | 用户系统：账号密码注册/登录、个人资料；双模式概述（含钱包） | 做登录、个人页、用户资料 |
| **docs/requirements/10_encrypted_wallet_user.md** | 加密钱包用户：BSC/ETH/SOL/Tron 四条链、Challenge 验签、绑定/解绑、API | 做钱包登录、多链验签、绑定逻辑 |

### 大厅与牌桌

| 文档 | 说明 | 何时 @ |
|------|------|--------|
| **docs/requirements/02_game_lobby.md** | 大厅：牌桌列表、快速开始、加入牌桌 | 做大厅页、匹配、加入桌 |
| **docs/requirements/03_game_table_core_logic.md** | 游戏核心逻辑摘要：一局流程、状态机、下注轮、比牌、边池 | 做/改 game_logic、理解流程 |
| **docs/requirements/04_game_table_ui_ux.md** | 牌桌 UI/UX | 做牌桌界面、动效、交互 |
| **docs/requirements/05_api_definitions.md** | API 与 WebSocket 事件定义（game:state_update、game:action 等） | 前后端联调、事件约定 |

### 游戏规则（裁判与实现依据）

| 文档 | 说明 | 何时 @ |
|------|------|--------|
| **docs/knowledge/TEXAS_HOLDEM_PLAY_AND_RULES.md** | 完整玩法与打牌需求（见上文「知识库内文档」） | 比牌、边池、行动合法性、特殊局面 |
| **docs/knowledge/POKER_KNOWLEDGE_BASE.md** | 术语与策略（见上文） | 牌型、位置、术语、策略参考 |

### 俱乐部

| 文档 | 说明 | 何时 @ |
|------|------|--------|
| **docs/requirements/11_club_design.md** | 俱乐部：创建/编辑/解散、成员与角色（Owner/Admin/Member）、邀请与审批、俱乐部牌桌 | 做俱乐部功能、俱乐部大厅、准入校验 |

### 约局

| 文档 | 说明 | 何时 @ |
|------|------|--------|
| **docs/requirements/13_scheduled_game_mode.md** | 约局模式：创建预约牌局、定时开赛/满人即开、邀请链接、报名与名单、俱乐部内约局、自动开桌（参考 WePoker/HHPoker） | 做约局、私局、好友组局、定时开桌 |

### 锦标赛

| 文档 | 说明 | 何时 @ |
|------|------|--------|
| **docs/requirements/12_tournaments_sng_mtt.md** | SNG（坐满即开）与 MTT（多桌定时赛）：报名、Late Reg、盲注结构、换桌合桌、决赛桌、奖励圈与泡沫、Hand-for-Hand、API 与库表 | 做 SNG/MTT、报名大厅、赛事状态、奖励发放 |

### 数据与非功能

| 文档 | 说明 | 何时 @ |
|------|------|--------|
| **docs/requirements/06_database_schema.md** | 数据库表结构：users、user_wallets、game_hands、clubs、tournaments 等 | 建表、改表、查字段 |
| **docs/requirements/14_multi_ui_config.md** | 多 UI 版本配置：主题/UI 版本/字体/动效/音效、本地与服务端存储、API、URL 参数 | 做主题切换、设置页、多皮肤 |
| **docs/requirements/07_non_functional_requirements.md** | 非功能需求 | 性能、安全、可用性 |
| **docs/requirements/08_future_features.md** | 未来功能（V1.5–V3）与各 spec 引用 | 排期、迭代范围 |
| **docs/requirements/09_ui_ux_animations.md** | UI/UX 动效 | 做动效与体验 |

---

## 三、使用方式

### 在 Cursor 中引用（@）

- 问规则/比牌/术语：`@docs/knowledge/POKER_KNOWLEDGE_BASE.md` 或 `@docs/knowledge/TEXAS_HOLDEM_PLAY_AND_RULES.md`
- 问接口与事件：`@docs/requirements/05_api_definitions.md`
- 问游戏流程与状态机：`@docs/requirements/03_game_table_core_logic.md`
- 问钱包登录与多链：`@docs/requirements/10_encrypted_wallet_user.md`
- 问俱乐部：`@docs/requirements/11_club_design.md`
- 问约局（预约牌局、定时开桌、邀请）：`@docs/requirements/13_scheduled_game_mode.md`
- 问 SNG/MTT：`@docs/requirements/12_tournaments_sng_mtt.md`
- 问库表：`@docs/requirements/06_database_schema.md`
- 问多 UI 版本/主题/设置：`@docs/requirements/14_multi_ui_config.md`

### 开发前建议

1. **先看入口**：README.md、ARCHITECTURE.md、docs/requirements/00_overview.md。
2. **按模块看规格**：用户→01/10，大厅→02，牌桌逻辑→03/05，规则→docs/knowledge/，俱乐部→11，约局→13，锦标赛→12，数据→06。
3. **改逻辑时**：03 + docs/knowledge/TEXAS_HOLDEM_PLAY_AND_RULES.md + POKER_KNOWLEDGE_BASE.md（术语）。

---

## 四、关联关系简图

```
README / ARCHITECTURE
    ├── docs/requirements/00 概述
    ├── docs/requirements/01 用户 ── docs/requirements/10 钱包
    ├── docs/requirements/02 大厅
    ├── docs/requirements/03 核心逻辑 ── docs/knowledge/TEXAS_HOLDEM_PLAY_AND_RULES
    │                      └── docs/knowledge/POKER_KNOWLEDGE_BASE
    ├── docs/requirements/04 牌桌 UI
    ├── docs/requirements/05 API/WS
    ├── docs/requirements/06 数据库 ←── 10, 11, 12, 13 均扩展表结构
    ├── docs/requirements/11 俱乐部
    ├── docs/requirements/13 约局
    └── docs/requirements/12 锦标赛 SNG/MTT
```

---

**维护**：新增或重要变更规格时，请同步更新本文档索引及项目根目录 `CURSOR_KNOWLEDGE.md`。

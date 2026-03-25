# dzpokerV3 项目规范

## 项目简介
在线德州扑克平台，游戏币模式（非真金白银）。
- 后端：Python + Flask + Flask-SocketIO，端口 **5001**（不用 5000，macOS 隔空播放占用）
- 前端：纯 HTML/CSS/JS，无框架，单页应用
- 数据库：MySQL + SQLAlchemy（游客模式无需 DB）

## 启动与常用命令

```bash
# 后端启动
python app.py

# 初始化数据库（首次部署或表不存在时）
python3 -c "from database import Base, engine; Base.metadata.create_all(bind=engine)"

# 安装 MySQL 认证依赖（sha256_password/caching_sha2_password）
python3 -m pip install cryptography

# 语法检查
python3 -m py_compile app.py core/game_logic.py tables.py bots.py

# 后端 API 测试
pytest tests/api/

# 前端开发（如有 npm 构建）
npm run dev
```

## 关键文件与职责

| 文件 | 职责 |
|------|------|
| `app.py` | Flask 入口，HTTP 路由 + WebSocket 事件注册 |
| `tables.py` | 牌桌管理（TABLES 字典）、入座、开局、处理行动 |
| `bots.py` | 机器人后台线程 `_bot_loop`，每 0.5s 轮询，逐个执行 |
| `core/game_logic.py` | 游戏状态机：`handle_player_action`、`find_next_player`、`advance_to_next_stage` |
| `core/pot_manager.py` | 主池/边池计算与分配 |
| `database/__init__.py` | SQLAlchemy 模型 + SessionLocal |
| `static/script.js` | 前端 WebSocket + UI 更新 |

## 架构约定

### 机器人执行规则 ⚠️
**不要**在 `process_action` 或 `start_game` 中同步执行机器人行动。
必须由 `bots._bot_loop` 后台线程驱动，每次只执行一个 bot，执行完广播后 break。

### find_next_player 两条路径 ⚠️
1. `amount_to_call > 0`：找 `bet_this_round < amount_to_call` 的玩家
2. `amount_to_call == 0`：找 `has_acted == False` 的玩家（翻牌/转牌/河牌圈关键！）

缺少 case 2 会导致翻牌圈第一人 check 后本街立即结束。

### 两套认证体系
| 方式 | token 格式 | 关键 |
|------|-----------|------|
| 游客 | UUID str | `tables.login()` 自动写入 `_tokens` |
| DB 用户 | JWT str | **必须手动写入 `_tokens`**，否则所有游戏 API 返回 401 |

`/api/auth/login` 和 `/api/auth/register` 末尾必须写入 `tables._tokens[token] = user_id`。

### DB import 保护
`tables.py` 顶部 import 数据库模型必须用 try/except 保护：
```python
try:
    from database import User, Hand, HandAction
except Exception:
    User = Hand = HandAction = None
```
使用前检查 `if Hand is not None`。

### HandAction 字段约束
只能传：`hand_id, user_id, action_type, amount`。
**不存在** `action_order`、`stage` 字段。

### Hand FK 保护
`start_game()` 创建 Hand 时 `table_id` FK 可能失败，用 try/except 静默处理，失败时 `t["current_hand_id"] = None` 继续游戏。

## 前端约定

### apiBase 陷阱 ⚠️
**禁止**用 `window.DZPOKER.apiUrl('')` 获取 base URL（返回 `"/"` 导致 `"//api/..."` CORS 报错）。

统一用本地函数，每次 fetch 传完整路径：
```js
function apiUrl(path) {
    return (window.DZPOKER && window.DZPOKER.apiUrl) ? window.DZPOKER.apiUrl(path) : path;
}
fetch(apiUrl('/api/clubs'), { ... })
```
受影响文件：`clubs.js`、`tournaments.js`、`tournament_detail.js`、`club_detail.html`、`wallet-login.js`

### CSS 布局
- `.poker-table` 的 `margin-bottom` 必须 ≥ 175px，否则底部座位被操作栏遮挡
- 筹码须作为 `#player-seats` 的绝对定位子元素，不放在座位 div 内

## 规格文档索引
- `docs/requirements/03_game_table_core_logic.md` — 游戏核心逻辑（最重要）
- `docs/requirements/04_game_table_ui_ux.md` — 牌桌 UI/UX
- `docs/requirements/05_api_definitions.md` — WebSocket + HTTP API
- `docs/knowledge/POKER_KNOWLEDGE_BASE.md` — 德州扑克规则知识库
- `docs/knowledge/TEXAS_HOLDEM_PLAY_AND_RULES.md` — 完整玩法规则

## 当前进行中任务（2026-03-19）
1. 俱乐部 auth 统一到 Bearer/JWT
2. 俱乐部 leave 接口
3. Tournaments 字段 camelCase 对齐
4. SNG 游戏桥接（start_tournament_game + elimination hook + payout）
5. Admin API 创建赛事 + 种子脚本

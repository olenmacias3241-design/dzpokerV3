# 批量与多客户端测试说明及结果

本文档记录「运行批量/多客户端测试并记录」任务的执行方式与简要结果。详见 TASKS.md 后端任务。

## 如何运行

### 1. 批量单元测试（无需启动服务）

在项目根目录执行：

```bash
python3 scripts/run_batch_tests.py
```

- 自动执行 `tests/` 下所有 `test_*.py`（unittest discover）。
- 自动执行根目录下的 `test_pot_distribution.py`、`test_side_pots.py`（若存在）。

### 2. 多客户端 HTTP 测试（需先启动服务端）

1. 启动服务：`python app.py`（默认端口 8080）。
2. 另开终端执行：

```bash
python3 scripts/run_multi_client_test.py
```

可选参数：`--base-url http://127.0.0.1:8080`、`--timeout 10`。

流程：2 个客户端登录 → 建桌 → 两人入座 → 等待机器人填满并开局 → 两个客户端分别拉取牌桌状态并校验。

### 3. 后端 API 接口测试（tests/api，需先启动服务端）

1. 启动服务：`python app.py`（默认端口 8080）。
2. 在项目根目录执行：

```bash
python tests/api/run_api_tests.py
# 或
pytest tests/api -v
```

可选环境变量：`DZPOKER_API_BASE=http://127.0.0.1:8080`。

---

## 后端 API 测试报告（tests/api）

**执行时间**：最近一次（服务端本地运行，端口 8080）  
**用例总数**：26

### 结果汇总

| 结果 | 数量 |
|------|------|
| 通过 | 18 |
| 跳过 | 5 |
| 失败 | 3 |

### 通过的用例（18）

- **健康**：`TestPing::test_ping_returns_200`
- **游客登录**：`TestGuestLogin::test_login_success`、`test_login_empty_username_fails`
- **auth/me**：`TestAuthMe::test_auth_me_without_token_returns_401`
- **大厅**：`TestLobby::test_lobby_tables_list`、`test_lobby_create_table`、`test_lobby_quick_start_requires_token`、`test_lobby_quick_start_with_token`
- **牌桌**：`TestTableStateAndSit::test_get_table_state_with_token`、`test_sit_success`、`test_leave_table`
- **对局**：`TestTableStartAndGame::test_game_state_requires_auth`；`TestTableAction::test_action_requires_auth`、`test_action_with_token_when_not_playing`、`test_emote_with_token`
- **商城**：`TestMall::test_mall_products`
- **机器人**：`TestAddBot::test_add_bot_requires_table`、`test_add_bot_success`

### 跳过的用例（5）

- `TestAuthRegisterLogin::test_auth_register` — 数据库未配置或测试用户已存在
- `TestAuthRegisterLogin::test_auth_login` — 数据库未配置或无测试账号
- `TestTableStartAndGame::test_game_state_with_token` — 牌桌未开局时无 game_state，跳过
- `TestClubs::test_clubs_list` — 俱乐部服务依赖数据库或未实现
- `TestReplay::test_replay_hands_list` — 回放依赖数据库

### 失败的用例（3）及原因

| 用例 | 预期 | 实际 | 说明 |
|------|------|------|------|
| `TestAuthMe::test_auth_me_with_guest_token` | 200 | 500 | 使用游客 token 调 `/api/auth/me` 时服务端返回 500，可能依赖 DB 或 JWT 实现 |
| `TestTableStateAndSit::test_get_table_state_requires_token` | 404 | 200 | 无 token 时当前实现仍返回 200（含 `my_seat: -1`），与用例“无 token 应 404”的假设不符 |
| `TestTableStartAndGame::test_start_game_after_two_players` | 200 | 400 | 两人入座后机器人自动开局，再调 start 返回 400「游戏已在进行中」 |

以上失败为**用例假设与当前后端行为不一致**，需产品/后端确认预期后再决定是改用例还是改实现。

---

## 牌桌打牌逻辑测试

### 4. 游戏逻辑单元测试（tests/test_game_logic.py，无需服务端）

```bash
pytest tests/test_game_logic.py -v
```

| 用例 | 结果 | 说明 |
|------|------|------|
| test_start_new_hand | 通过 | 发底牌、下盲注、pot/amount_to_call、首动玩家 UTG |
| test_player_action_fold | 通过 | 弃牌后行动权移交下一玩家 |
| test_player_action_call | 通过 | 跟注后筹码与底池更新 |
| test_player_action_raise | 通过 | 加注后 amount_to_call、last_raiser_id 更新 |
| test_end_of_preflop_round | **失败** | Preflop 轮 p1 call、p2 call、p3 check 后，预期进入 Flop，实际仍为 PREFLOP；`find_next_player` / `advance_to_next_stage` 在 BB check 时未正确结束本街 |

**结论**：底牌圈下注轮结束条件（回到 BB 且 BB check）后应自动进入翻牌圈，当前逻辑未推进阶段，需修 `core/game_logic.py`。

### 5. 打牌流程集成测试（tests/api/test_play_hand.py，需服务端）

模拟两人入座、开局、轮流 check/call 并发牌直至本局结束。

```bash
# 先启动服务：python app.py
pytest tests/api/test_play_hand.py -v -s
```

- 跳过条件：设置 `SKIP_PLAY_HAND=1` 可跳过。
- 若服务未启动会报 `ConnectionRefusedError`，需先确保服务在运行再执行。

---

## 前端页面 E2E 测试（tests/frontend）

使用 Playwright 对大厅、登录、牌桌页进行浏览器端测试。

### 6. 运行方式

1. 安装依赖：`pip install -r requirements.txt`，然后 `playwright install chromium`。
2. 启动服务端：`python app.py`（默认 8080）。
3. 在项目根目录执行：

```bash
pytest tests/frontend -v
# 有界面：pytest tests/frontend -v --headed
# 或：python tests/frontend/run_frontend_tests.py
```

可选环境变量：`DZPOKER_API_BASE=http://127.0.0.1:8080`。

### 用例说明

| 文件 | 用例 |
|------|------|
| test_lobby_page.py | 大厅页加载、牌桌列表区域、创建牌桌面板、筛选控件 |
| test_login_page.py | 登录页加载、表单输入、注册链接 |
| test_table_page.py | 无参数时提示、带 table+token 时游戏区/入座区、行动按钮存在 |

部分用例（牌桌页带 token）会先调 API 建桌、入座再打开页面，服务未启动时会 skip。

若服务未启动，所有前端 E2E 用例会因 `ERR_CONNECTION_REFUSED` 失败，需先执行 `python app.py` 再运行测试。

---

## 最近一次运行结果（记录用）

| 项目 | 结果 | 说明 |
|------|------|------|
| tests/ (unittest) | 17 个用例，1 个失败 | 失败：`test_game_logic.test_end_of_preflop_round`（期望 Preflop 结束后进入 Flop，当前实现未在该用例中推进阶段） |
| test_pot_distribution.py | 失败 | 依赖已废弃的 `PotManager` 类，当前 `core.pot_manager` 仅提供 `calculate_side_pots` / `distribute_pots`，需后续对齐或移除该脚本 |
| test_side_pots.py | 通过 | 使用 `core.pot_manager.calculate_side_pots` 等现有接口 |
| 多客户端测试 | 通过 | 2 客户端登录→建桌→入座→拉取状态通过（需服务端已启动） |

## 相关文件

- 批量测试入口：`scripts/run_batch_tests.py`
- 多客户端测试：`scripts/run_multi_client_test.py`
- 单元测试目录：`tests/`

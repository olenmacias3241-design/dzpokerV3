# 多 Chat 角色与开场白

**重要**：Cursor 里**没有**「选角色」的菜单或按钮，角色需要你**手动**设定：新开一个 Chat 后，从下面复制对应角色的整段文字，**粘贴到新 Chat 里作为第一条消息发送**，这个 Chat 就会按该角色工作。

---

## 怎么「选」角色（3 步）

1. **新开一个 Chat**（Cursor 左侧点 New Chat 或快捷键）。
2. **打开本文件** `docs/CHAT_ROLES.md`，在下面找到你要的角色（主控 / 后端 / 前端 / 联调）。
3. **复制该角色「开场白」里的整段文字**（从「我是本项目的」到「……然后等我给你具体任务」），**粘贴到新 Chat 的输入框，发送**。

之后在这个 Chat 里派任务即可，AI 会按该角色的职责和阅读清单来响应。

---

## 1. 主控 / 产品 Chat

**职责**：拆任务、排优先级、更新 TASKS.md、验收、协调依赖。

**开场白（复制到新 Chat）：**

```
我是本项目的【主控 Chat】。我只负责：
- 阅读并更新项目根目录的 TASKS.md（任务拆解、状态、依赖）；
- 根据 MEMORY.md、memory/ 和 PROJECT_STATUS.md 判断优先级；
- 不做具体代码实现，只做任务描述、验收标准和协调。

每次开始前请先读：TASKS.md、README.md、PROJECT_STATUS.md（若存在）。然后等我给你具体指令（例如「把大厅前端任务拆成 3 个子任务」或「验收牌桌页 WebSocket 同步」）。
```

---

## 2. 后端 Chat

**职责**：服务端逻辑、API、数据库、WebSocket 服务端、测试脚本。不改前端页面或样式。

**开场白（复制到新 Chat）：**

```
我是本项目的【后端 Chat】。我只负责：
- 修改 app.py、tables.py、core/、services/、database/、api 路由、WebSocket 事件等后端代码；
- 遵守 docs/requirements/05_api_definitions.md 和 ARCHITECTURE.md，若有接口变更需更新 05 或相关 API 文档；
- 不修改 templates/、static/ 下的前端页面和样式（最多只改 API 返回格式或文档）。

每次开始前请先读：TASKS.md（看后端任务与状态）、docs/requirements/05_api_definitions.md、ARCHITECTURE.md、docs/requirements/03_game_table_core_logic.md。然后等我给你具体任务（例如「实现 xxx 接口」或「修 xxx bug」）。
```

---

## 3. 前端 Chat

**职责**：大厅、牌桌、登录等页面，HTML/CSS/JS，调用后端 API 与 WebSocket，不改后端业务逻辑。

**开场白（复制到新 Chat）：**

```
我是本项目的【前端 Chat】。我只负责：
- 修改 templates/、static/（HTML/CSS/JS），包括大厅、牌桌、登录页等；
- 对接后端 API 和 WebSocket（见 docs/requirements/05_api_definitions.md），不修改后端代码；
- 遵守 docs/requirements/04_game_table_ui_ux.md、docs/requirements/02_game_lobby.md、TABLE_LAYOUT_GUIDE.md，保持 script.js / lobby.js 等与现有 API 一致。

每次开始前请先读：TASKS.md（看前端任务与状态）、docs/requirements/05_api_definitions.md、docs/requirements/04_game_table_ui_ux.md、docs/requirements/02_game_lobby.md。然后等我给你具体任务（例如「实现大厅牌桌列表」或「修牌桌页 xxx 布局」）。
```

---

## 4. 联调 / 集成 Chat

**职责**：端到端流程、部署、环境配置、简单自动化测试；不深入改后端业务或前端组件实现。

**开场白（复制到新 Chat）：**

```
我是本项目的【联调 Chat】。我只负责：
- 端到端流程验证（大厅→入座→开局→下注→比牌）、部署与运行环境（Docker/脚本/配置）；
- 阅读 ARCHITECTURE.md、DEPLOYMENT.md、README.md，编写或调整启动/测试脚本；
- 不深入修改 core/ 游戏逻辑或前端组件实现，只做「能跑通、能部署」的集成与文档。

每次开始前请先读：TASKS.md（看联调/集成任务）、ARCHITECTURE.md、README.md。然后等我给你具体任务（例如「写一个 E2E 测试脚本」或「补全 .env 示例」）。
```

---

## 使用建议

1. **新开一个 Chat** 就选一个角色，把对应开场白**完整粘贴**为第一条消息。
2. 派具体任务时可以说：「按 TASKS.md 里前端任务『大厅页：牌桌列表』来做，做完把状态改成已完成。」
3. 若某个 Chat 需要临时越界（例如后端 Chat 改了一行 template 里的 API 地址），在 TASKS.md 或 MEMORY 里记一笔，避免其他 Chat 重复改。
4. 每天或每轮迭代结束，主控 Chat 可读一遍 TASKS.md 和 memory/，把重要进展摘要进 MEMORY.md。

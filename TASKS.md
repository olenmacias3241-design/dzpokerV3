# TASKS.md - 待办清单

要谁做啥：**开个 Chat 说「做 TASKS 第 x 条」**或把那条复制过去就行。

---

## 待办（共 7 条，按你通知顺序来）

1. **【前端】把大厅和牌桌页做到能看、好用**  
   当前观感差、没法看。目标：有清晰层次、布局不乱、按钮/信息易读；参考 docs/requirements/09、PROJECT_STATUS 高优先级 UI；PC+手机都要能看。

2. **【前端】入座跳转**  
   大厅点入座后，跳到牌桌页且带上 token：`/table?id=xx&token=xx`。

3. **【前端】牌桌页：操作栏 + 底池/公共牌**  
   弃牌/跟注/下注/All-in 按钮，以及底池、公共牌展示；script.js 已对接 API，把 UI 接好。

4. **【前端】牌桌页：WebSocket 实时同步**  
   join_table + game:state_update，状态变化即时刷新。

5. **【前端】响应式与移动端**  
   按钮至少 44px，PC+手机都能用；参考 docs/requirements/09。

6. **【联调】端到端跑通**  
   大厅 → 入座 → 开局 → 下注 → 比牌，手动或简单脚本跑通一整局。

7. **【前端】登录/注册页对接 auth API**（可选、后期）  
   等后端 auth 就绪再做。

---

## 已知问题（修的人看）

- 前端多处布局/样式异常、显示不全（打开大厅、牌桌页可见）→ 给前端。
- 大厅页底部「创建牌桌」等按钮跑出容器（footer 溢出）→ 给前端；查 style_new.css 是否加载、footer 是否贴底。

更多历史任务/流程见 [docs/TASKS_ARCHIVE.md](docs/TASKS_ARCHIVE.md)。

---

## 相关文档

- [README.md](./README.md) [PROJECT_STATUS.md](./PROJECT_STATUS.md)
- [ARCHITECTURE.md](./ARCHITECTURE.md) [docs/requirements/05_api_definitions.md](./docs/requirements/05_api_definitions.md)
- 角色说明（需要时）：[docs/CHAT_ROLES.md](docs/CHAT_ROLES.md)

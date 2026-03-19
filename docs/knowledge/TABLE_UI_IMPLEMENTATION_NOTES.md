# 牌桌前端实现笔记 · Table UI Implementation Notes

**供 Agent 改牌桌 UI 时引用**：记录牌桌页（game area）的 DOM 结构、CSS 约定与注意事项，改布局、修重叠或加新元素时先看本文，避免破坏定位或遗漏约定。规格见 **docs/requirements/04_game_table_ui_ux.md**。

---

## 1. 牌桌整体结构

- **容器**：`.game-area` → `.game-main` → `.poker-table`（椭圆桌面）。
- **桌面内**：
  - `.table-center`：绝对居中（`top: 46%`，`left: 50%`，`transform: translate(-50%, -50%)`），内含：阶段、公共牌、底池（主池 + 本街最高下注/需跟注 + 边池）、上次行动。
  - `#player-seats`：`position: absolute; inset: 0`，座位按椭圆分布，由 JS 设置每个座位的 `top/left/transform`。

**注意**：不要给 `.player-seat` 设 `display: flex` 等改变块级布局的属性，否则会破坏基于百分比的定位与 transform，导致座位错位。

---

## 2. 座位 DOM 结构（有人的座位）

由 **static/script.js** 在 `renderTable()` 中拼接，顺序为：

```text
.player-seat
├── .seat-chips-on-table     （绝对定位，依 data-seat-display 放在座位一侧）
├── .seat-emote-outside      （绝对定位，表情气泡）
├── .seat-main               （仅此块做横向 flex）
│   ├── .player-hand-wrap
│   │   └── .player-hand    （2 张底牌）
│   └── .player-info
│       └── .player-meta    （头像、徽章、名字、下注、All-in、牌型等）
└── .seat-countdown          （行动倒计时条）
```

- **手牌与信息**：仅在 `.seat-main` 内 `display: flex; flex-direction: row`，手牌左、信息右，`gap: 4px`。
- **弃牌**：座位根节点加 class `player-seat-folded`，灰化样式为 `.player-seat-folded .player-hand .card-back`。

---

## 3. 筹码与中央区域防重叠

- **底部座位**（`data-seat-display="0"|"1"|"5"|"6"`）：筹码在座位上方，`transform: translate(-50%, -18px)`，与中央信息留出间距。
- **其他座位**：筹码偏移 `6px`，贴近头像。
- **中央**：`.table-center` 使用 `top: 46%`，底池/边池 margin 与字号已收紧，减少与底部座位重叠。

---

## 4. 底池与边池

- **主池**：`.pot` 内 `.pot-row-main` + `#pot-display`，其下为 `#street-bet-call-display`、`#side-pots-display`。
- **边池**：
  - 有 `state.side_pots` 且 `length > 0` 时显示，一行展示，项之间用 ` · ` 分隔（CSS `::before`）。
  - 无边池时：`#side-pots-display` 的 `innerHTML = ''`、`style.display = 'none'`，逻辑在 `renderTable()` 中与 `state.side_pots` 同步。

---

## 5. 行动区（.actions）

- 无横条包裹，直接包含：「开始对局」按钮、`#deal-controls`、`#insurance-controls`、`#action-controls`（弃牌/过牌/跟注/下注/All-in + 下注滑块 + 预设 + `#my-console` + 表情栏）。
- 控制台与行动按钮的显示/隐藏由 JS 根据 `mySeat >= 0 && myChips > 0` 及当前是否轮到己方控制。

---

## 6. 相关文件

| 用途     | 文件 |
|----------|------|
| 结构     | templates/index.html（牌桌、底池、行动区） |
| 样式     | static/style.css（座位、筹码、中央、边池、行动区） |
| 逻辑     | static/script.js（renderTable、座位 HTML、边池/本街显示） |

日常改布局时：**只改 `.seat-main` 内部或 `.table-center` 内部**，避免动 `.player-seat` 的 display/position，以免桌面分布乱掉。

# MEMORY.md · 长期记忆

**供 Agent 在后续会话中加载**：项目与协作中的决策、约定和教训，用于延续上下文、避免重复踩坑。

---

## 牌桌前端布局约定（2025-03-13）

- **座位结构**：每个座位（`.player-seat`）内顺序为：筹码（绝对定位）、表情（绝对定位）、**`.seat-main`**（手牌 + 用户信息）、倒计时。手牌与信息**只在 `.seat-main` 内**做横向 flex，**不要**给 `.player-seat` 设 `display: flex`，否则会破坏桌面椭圆定位（`top/left/transform`）。
- **手牌与信息**：2 张手牌在左（`.player-hand-wrap`）、头像/名字/下注在右（`.player-info` → `.player-meta`），统一所有有人的座位；弃牌灰化用 class `.player-seat-folded` 作用在 `.player-hand .card-back`。
- **桌面中央与底部**：中央区域（主池、本街最高下注、边池）用 `.table-center { top: 46% }` 略上移，避免与底部座位筹码重叠；底部座位（data-seat-display 0/1/5/6）筹码偏移设为 `-18px`，与中央留出间距。
- **边池**：有数据时一行展示（`white-space: nowrap` + `.side-pot-item` inline + `·` 分隔），无 `side_pots` 或空数组时清空 DOM 并 `display: none`。
- **行动区**：弃牌/过牌/下注等按钮上方不再保留横条（已移除 `.actions-top-row`），「开始对局」直接放在 `.actions` 下。

改牌桌 UI 时优先查：`memory/2025-03-13.md`、`docs/knowledge/TABLE_UI_IMPLEMENTATION_NOTES.md`。

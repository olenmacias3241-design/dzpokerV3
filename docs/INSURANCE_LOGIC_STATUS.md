# 保险逻辑检查说明

## 结论摘要

- **当前线上路径**（`tables.py` + `core/game_logic.py` + GameWrapper）：**未实现保险**。`tables.resolve_insurance` 为存根，仅清空 `pending_insurance`（且 GameWrapper 从未设置该字段），`game_logic.advance_to_next_stage` 中无全员 All-in 检测与保险挂起。
- **完整实现**在 `core/logic.py` 的 `Game` 类中（触发条件、胜率、保费、输时赔付、比牌后结算），但该引擎**未被 app/tables 使用**。

## 代码位置

| 位置 | 说明 |
|------|------|
| `core/logic.py` | `Game.pending_insurance`、`resolve_insurance()`、`_advance_to_next_street` 中 flop/turn 全员 All-in 时挂起、比牌后保险结算；**未被 tables 使用**。 |
| `core/game_logic.py` | 当前 app 使用的 dict 引擎；`advance_to_next_stage` 无保险分支，无 `pending_insurance`。 |
| `tables.py` | `resolve_insurance(table_id, token, amount)` 仅做 `t["game"].pending_insurance = None`；GameWrapper.`pending_insurance` 固定为 `None`。 |
| `app.py` | 提供 `/api/tables/<id>/insurance` 与 WS `insurance`，调用 `tables.resolve_insurance`；`deal_next_street` 在存在 `pending_insurance` 时先 `resolve_insurance(0)` 再发牌。 |

## 已做修复（本迭代）

- 在 **game_logic** 中：在进入 TURN/RIVER 前若「全员 All-in」则挂起并设置 `game_state['pending_insurance']`，并实现 `resolve_insurance(game_state, amount)` 与 runout+比牌+保险结算。
- 在 **tables** 中：`resolve_insurance` 改为调用 `game_logic.resolve_insurance(wrapper.state, amount)` 并写回 state；GameWrapper 的 get_state 将 `state.get('pending_insurance')` 暴露给前端。

详见本次提交中的 `core/game_logic.py` 与 `tables.py` 修改。

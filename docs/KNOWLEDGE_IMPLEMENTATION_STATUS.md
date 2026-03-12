# 知识库规则实现状态

对照 `docs/knowledge/TEXAS_HOLDEM_PLAY_AND_RULES.md` 附录 B 与正文，当前后端实现情况。

## 附录 B 检查清单

| 项 | 状态 | 说明 |
|----|------|------|
| 牌型 10 档齐全，含顺子、同花、同花顺、A-2-3-4-5 | 已实现 | `core/hand_evaluator.py`：10 档牌型，Wheel 支持，返回可比元组 |
| 同牌型比较与踢脚、平分与奇数筹码规则正确 | 已实现 | 踢脚在 rank 元组内；`pot_manager.distribute_pots` 奇数筹码给离 Dealer 最近者 |
| Preflop 行动顺序：UTG 到 BB；Flop/Turn/River 从 BT 下家起 | 已实现 | `game_logic.start_new_hand` / `advance_to_next_stage` |
| 两人桌 BT=SB，BB 先行动 | 已实现 | `start_new_hand` 中 `num_players == 2` 时 SB 先行动 |
| 盲注不足时 All-in 处理 | 已实现 | SB/BB 用 `min(amount, stack)` 并设 `is_all_in` |
| Check/Call/Bet/Raise/Fold/All-In 合法性校验 | 已实现 | 轮到谁、Check 条件、Bet 仅当 amount_to_call==0、Raise 最小加注、All-In |
| 下注轮结束条件与提前结束（仅剩一人） | 已实现 | `find_next_player` 结束条件；Fold 后若仅剩一人立即结束并分池 |
| 多边池分配顺序与资格 | 已实现 | `pot_manager` 按档位算池、含弃牌玩家投入、从最后一池往前分配 |
| 超时默认行动（Fold 或 Call/Check） | 待产品配置 | 产品/接口层配置，未在 core 写死 |
| 洗牌在服务端、随机算法可靠 | 已实现 | `core/cards.py` 使用 `random.shuffle`（Fisher-Yates） |

## 涉及文件

- **core/hand_evaluator.py**：牌型评估、可比 rank 元组、find_winners
- **core/pot_manager.py**：边池计算（含弃牌）、分配与奇数筹码
- **core/game_logic.py**：行动校验、RAISE 本街投入、仅剩一人结束、分池时传 player_order/dealer_pid
- **core/bot_ai.py**：evaluate_hand 调用改为 (hole, community)、使用 rank 元组 level

**最后更新**：2026-03-12

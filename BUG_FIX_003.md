# Bug 修复记录 #3

**Bug ID:** #3  
**发现人:** 佳佳（@Jiajiatest_bot）  
**修复人:** 胖子  
**修复时间:** 2026-03-11 10:25

---

## Bug 描述

**标题:** 2人对局（Heads-Up）时，行动顺序错误

**严重程度:** 🔴 严重

**测试场景:** 测试场景 1.2.1 - 2人对局行动顺序

**复现步骤:**
1. 创建2人牌桌
2. 两个玩家加入
3. 开始游戏
4. 观察底牌圈第一个行动者

**预期结果:**
- 庄位（Button）= 小盲注（SB）
- SB 先行动

**实际结果:**
- 庄位（Button）≠ 小盲注（SB）
- BB 先行动（错误）

**测试日志证据:**
```
Game stage: preflop
SB player ID: None
Current actor: guest_c6f72a0e <-- (玩家2/BB)
❌ TEST FAILED: Player 1 should be the SB
```

---

## 根本原因

在 `core/game_logic.py` 的 `start_new_hand()` 函数中，盲注位置的计算没有区分2人对局和多人对局：

**错误代码:**
```python
sb_pos = (dealer_pos + 1) % num_players  # 错误！
bb_pos = (dealer_pos + 2) % num_players
```

**问题分析:**

在2人对局中，如果 `dealer_pos = 0`：
- `sb_pos = (0 + 1) % 2 = 1` → 玩家2 是 SB
- `bb_pos = (0 + 2) % 2 = 0` → 玩家1 是 BB

但实际上应该是：
- 玩家1（dealer_pos=0）是 SB（**庄位就是SB**）
- 玩家2（pos=1）是 BB

**德州扑克规则:**
- **多人对局:** 庄位 → SB → BB → UTG
- **2人对局:** 庄位 = SB，庄位下一位 = BB

---

## 修复方案

**文件:** `core/game_logic.py` - `start_new_hand()`

**修复代码:**
```python
# 2人对局特殊处理：庄位 = SB
if num_players == 2:
    sb_pos = dealer_pos  # 庄位就是 SB
    bb_pos = (dealer_pos + 1) % num_players  # 庄位下一位是 BB
else:
    # 多人对局：庄位下一位是 SB，再下一位是 BB
    sb_pos = (dealer_pos + 1) % num_players
    bb_pos = (dealer_pos + 2) % num_players
```

---

## 验证步骤

1. 重启服务器
2. 创建2人牌桌
3. 两个玩家加入
4. 开始游戏
5. 验证：
   - 庄位玩家是 SB
   - SB 先行动
   - BB 后行动

---

## 影响范围

- ✅ 2人对局的盲注位置
- ✅ 2人对局的行动顺序
- ✅ 不影响多人对局

---

## 相关文档

- 测试计划：`/Users/taoyin/.openclaw/workspace-test/TEST_PLAN.md`
- 修复补丁：`/Users/taoyin/.openclaw/workspace/dzpokerV3/LOGIC_FIX_PATCH.md`

---

**状态:** ✅ 已修复，等待验证

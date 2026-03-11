# Bug 修复记录 #4

**Bug ID:** #4  
**发现人:** 佳佳（@Jiajiatest_bot）  
**修复人:** 胖子  
**修复时间:** 2026-03-11 10:55

---

## Bug 描述

**标题:** 2人对局中 sb_player_id 状态字段为空 (None)

**严重程度:** 🟡 中等

**测试场景:** 测试场景 1.2.1 - 2人对局行动顺序

**复现步骤:**
1. 创建2人牌桌
2. 两个玩家加入
3. 开始游戏
4. 通过 API 获取游戏状态
5. 检查 `sb_player_id` 字段

**预期结果:**
- `sb_player_id` 应该是庄位玩家的 ID
- `bb_player_id` 应该是另一个玩家的 ID

**实际结果:**
- `sb_player_id` 为 `None`
- `bb_player_id` 为 `None`
- 虽然行动顺序是正确的，但状态字段缺失

**测试日志证据:**
```
SB player ID: None <-- 依然是空的
Current actor: guest_5a75111e <-- (行动权是正确的)
❌ TEST FAILED: State error: sb_player_id should not be None
```

---

## 根本原因

在 `tables.py` 的 `get_state()` 函数中，虽然从内部 `game_state` 中读取了 `sb_player_id` 和 `bb_player_id`（第126-127行），但是在构建返回给 API 的 `out` 字典时（第189-217行），**没有把这两个字段包含进去**。

**问题代码:**
```python
out = {
    "stage": stage_name.lower() if stage_name else "preflop",
    "current_player_id": cur_pid,
    "dealer_idx": dealer_idx,
    "sb_idx": sb_idx,  # 只有索引，没有 player_id
    "bb_idx": bb_idx,  # 只有索引，没有 player_id
    # ... 其他字段
}
# 缺少 sb_player_id 和 bb_player_id
```

**为什么会这样：**
- 内部 `game_state` 正确设置了 `sb_player_id` 和 `bb_player_id`
- 但是 `get_state()` 只返回了 `sb_idx` 和 `bb_idx`（座位索引）
- 测试脚本需要的是 `player_id`，而不是座位索引

---

## 修复方案

**文件:** `tables.py` - `get_state()`

**修复代码:**
```python
out = {
    "stage": stage_name.lower() if stage_name else "preflop",
    "current_player_id": cur_pid,
    "dealer_idx": dealer_idx,
    "sb_idx": sb_idx,
    "bb_idx": bb_idx,
    "sb_player_id": s.get("sb_player_id"),  # 新增
    "bb_player_id": s.get("bb_player_id"),  # 新增
    # ... 其他字段
}
```

---

## 验证步骤

1. 重启服务器
2. 运行测试场景 1.2.1（2人对局）
3. 验证：
   - `sb_player_id` 不为 `None`
   - `bb_player_id` 不为 `None`
   - `sb_player_id` 等于第一个行动者的 ID

---

## 影响范围

- ✅ API 返回的游戏状态现在包含 `sb_player_id` 和 `bb_player_id`
- ✅ 不影响游戏逻辑（逻辑本身是正确的）
- ✅ 只是修复了 API 返回的数据完整性

---

## 相关 Bug

- Bug #3：2人对局行动顺序错误（已修复）
- 本 Bug 是 Bug #3 的后续问题

---

**状态:** ✅ 已修复，等待验证

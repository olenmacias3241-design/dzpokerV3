# 德州扑克业务逻辑审查报告

**审查时间：** 2026-03-11  
**审查范围：** 主业务逻辑、边池逻辑、保险逻辑  
**审查文件：**
- `core/game_logic.py` - 新引擎（基于字典状态）
- `core/logic.py` - 旧引擎（基于对象）
- `tables.py` - 牌桌管理

---

## 🔍 发现的问题

### 1. 打牌逻辑问题

#### 问题 1.1：翻牌后第一个行动者计算错误
**位置：** `core/game_logic.py` - `advance_to_next_stage()`

**问题描述：**
```python
# 当前代码（错误）
first_active_player = None
for i in range(1, num_players + 1):
    player_id = player_ids[(dealer_pos + i) % num_players]
    # ...
```

**标准规则：**
- 翻牌/转牌/河牌圈：第一个行动者应该是 **庄位（Button）的下一位**（即小盲注位置）
- 如果小盲注已弃牌或 All-in，则继续顺时针找下一个可行动的玩家

**当前实现：**
- 使用 `dealer_pos` 作为起点，但 `dealer_pos` 是在 `player_order` 中的索引
- 应该使用 **庄位玩家的 player_id** 在 `player_ids` 中的位置

**修复建议：**
```python
# 找到庄位玩家在 player_ids 中的索引
dealer_player_id = game_state['players'][player_ids[dealer_pos]]  # 这里有问题
# 应该是：
# 1. game_state 中应该存储 dealer_player_id
# 2. 或者 player_order 就是按座位顺序排列的
```

#### 问题 1.2：底牌圈第一个行动者计算错误
**位置：** `core/game_logic.py` - `start_new_hand()`

**问题描述：**
```python
# 当前代码
utg_pos = (bb_pos + 1) % num_players
first_to_act_id = active_player_ids[utg_pos]
```

**标准规则：**
- 底牌圈：第一个行动者是 **大盲注（BB）的下一位**（UTG）
- 2人对局：小盲注（SB）先行动

**当前实现：**
- 看起来是正确的，但需要确认 `bb_pos` 是在 `active_player_ids` 中的索引
- 2人对局的特殊处理缺失

**修复建议：**
```python
# 2人对局特殊处理
if num_players == 2:
    first_to_act_id = sb_player_id  # 小盲注先行动
else:
    utg_pos = (bb_pos + 1) % num_players
    first_to_act_id = active_player_ids[utg_pos]
```

#### 问题 1.3：下注轮结束判断不准确
**位置：** `core/game_logic.py` - `find_next_player()`

**问题描述：**
```python
# 当前代码
if last_raiser and next_player_id == last_raiser:
    return None, True
```

**标准规则：**
- 下注轮结束条件：
  1. 所有未弃牌且未 All-in 的玩家都已行动
  2. 所有人的本街投入都相等（等于 `amount_to_call`）
  3. 已经回到最后加注者，且最后加注者也已跟齐

**当前实现：**
- 只检查是否回到 `last_raiser`
- 没有检查 `last_raiser` 自己是否已经跟齐（虽然加注者本身已经是最高投入）

**潜在问题：**
- 如果 `last_raiser` 是 BB，且底牌圈无人加注，BB 应该有机会行动（可以 Check 或 Raise）
- 当前代码可能会在 BB 未行动时就结束底牌圈

**修复建议：**
```python
# 底牌圈特殊处理：BB 是初始 "加注者"，但仍需给他行动机会
if game_state.get('stage') == GameStage.PREFLOP:
    bb_player_id = game_state.get('bb_player_id')
    if last_raiser == bb_player_id:
        # 检查 BB 是否已经行动过
        bb_state = game_state['players'][bb_player_id]
        if not bb_state.get('has_acted_this_street'):
            # BB 还没行动，继续
            if next_player_id == bb_player_id:
                return bb_player_id, False
```

#### 问题 1.4：玩家行动标记缺失
**位置：** `core/game_logic.py` - `handle_player_action()`

**问题描述：**
- 当前代码没有标记玩家"已行动"（`has_acted`）
- 这导致无法准确判断下注轮是否结束

**标准规则：**
- 每个玩家行动后，应该标记 `has_acted = True`
- 进入新街时，重置所有玩家的 `has_acted = False`

**修复建议：**
```python
# 在每个行动处理后添加
player_state['has_acted'] = True

# 在 advance_to_next_stage() 中重置
for player_id, player_state in game_state['players'].items():
    if player_state.get('is_active'):
        player_state['has_acted'] = False
```

---

### 2. 边池逻辑问题

#### 问题 2.1：边池计算时机错误
**位置：** `core/game_logic.py` - `advance_to_next_stage()` 的 `SHOWDOWN` 分支

**问题描述：**
```python
# 当前代码在 SHOWDOWN 时才计算边池
elif next_stage == GameStage.SHOWDOWN:
    # ...
    pots = pot_manager.calculate_side_pots(players_for_pot)
```

**标准规则：**
- 边池应该在 **每个下注轮结束时** 计算和显示
- 玩家需要知道当前有多少个边池，每个边池的金额

**当前实现：**
- 只在最后比牌时计算边池
- 玩家在游戏过程中看不到边池信息

**修复建议：**
```python
# 在每次 advance_to_next_stage() 时计算边池
def advance_to_next_stage(game_state):
    # ... 发牌逻辑 ...
    
    # 计算当前边池（用于显示）
    players_for_pot = {}
    for pid, pstate in game_state['players'].items():
        players_for_pot[pid] = {
            'total_bet_this_hand': pstate.get('total_bet_this_hand', 0),
            'is_folded': not pstate.get('is_in_hand', False)
        }
    game_state['current_pots'] = pot_manager.calculate_side_pots(players_for_pot)
    
    # ... 继续 ...
```

#### 问题 2.2：边池计算逻辑可能有误
**位置：** 需要检查 `pot_manager.calculate_side_pots()` 的实现

**标准边池算法：**
1. 找出所有不同的投入金额（All-in 金额）
2. 按金额从小到大排序
3. 对每个金额级别：
   - 计算该级别的边池金额 = (当前级别 - 上一级别) × 参与人数
   - 记录有资格赢取该边池的玩家（投入 >= 该级别且未弃牌）

**示例：**
- 玩家A：投入 100（All-in）
- 玩家B：投入 200（All-in）
- 玩家C：投入 300

**正确的边池：**
- 主池：100 × 3 = 300（A, B, C 都有资格）
- 边池1：(200-100) × 2 = 200（B, C 有资格）
- 边池2：(300-200) × 1 = 100（只有 C 有资格）

**需要验证：**
- `pot_manager.calculate_side_pots()` 是否正确实现了这个算法
- 是否处理了弃牌玩家（弃牌玩家的投入进入边池，但他们没有资格赢取）

#### 问题 2.3：边池分配逻辑
**位置：** `core/game_logic.py` - `advance_to_next_stage()` 的 `SHOWDOWN` 分支

**问题描述：**
```python
# 当前代码
winnings = pot_manager.distribute_pots(pots, hand_ranks, players_for_pot)
```

**标准规则：**
- 从最后一个边池（最小的边池）开始分配
- 每个边池独立比较有资格的玩家的牌型
- 平分时需要处理余数（通常给位置靠前的玩家）

**需要验证：**
- `pot_manager.distribute_pots()` 是否从后往前分配
- 是否正确处理平分和余数

---

### 3. 保险逻辑问题

#### 问题 3.1：保险触发条件不明确
**位置：** `core/logic.py` - `_advance_to_next_street()`

**问题描述：**
```python
# 当前代码
if self.insurance_enabled and len(all_in_indices) >= 2:
    leading_idx, equities = self._compute_equity(all_in_indices)
    if leading_idx is not None:
        equity = equities.get(leading_idx, 0)
        # ...
        if 0 < equity < 1 and leader.is_human and leader.chips > 0:
            # 提供保险
```

**标准保险规则：**
- 保险通常在 **转牌或河牌前** 提供
- 只有当 **领先玩家有听牌风险** 时才提供
- 保险费 = 底池 × (1 - 胜率)

**当前实现：**
- 在任何阶段都可能触发保险
- 没有限制在转牌/河牌前

**修复建议：**
```python
# 只在转牌前或河牌前提供保险
if self.insurance_enabled and len(all_in_indices) >= 2:
    # 只在 flop 或 turn 阶段提供保险
    if self.stage in ('flop', 'turn'):
        leading_idx, equities = self._compute_equity(all_in_indices)
        # ...
```

#### 问题 3.2：保险赔率计算
**位置：** `core/logic.py` - `resolve_insurance()`

**问题描述：**
```python
# 当前代码
payout = premium_amount / max(equity, 0.01)
```

**标准保险赔率：**
- 公平赔率 = 1 / (1 - 胜率)
- 例如：胜率 70%，则赔率 = 1 / 0.3 = 3.33
- 保费 = 想要保护的金额 / 赔率

**当前实现：**
- 使用 `premium / equity`，这是错误的
- 应该是 `premium / (1 - equity)`

**修复建议：**
```python
# 正确的赔率计算
payout = premium_amount / max(1 - equity, 0.01)
```

#### 问题 3.3：保险结算逻辑
**位置：** `core/logic.py` - `_do_showdown()`

**问题描述：**
```python
# 当前代码
if insurance_buyer_chips_before is not None and chips_after == insurance_buyer_chips_before:
    self.players[idx].chips += buy["payout_if_lose"]
```

**标准保险结算：**
- 如果购买者输了（没有赢得任何边池），赔付保险金
- 如果购买者赢了，保费归庄家（或对手）

**当前实现：**
- 通过比较筹码判断是否输了
- 这个逻辑基本正确，但不够精确

**潜在问题：**
- 如果购买者赢了一个小边池，但输了主池，应该如何处理？
- 标准做法：保险只保护主池，不保护边池

**修复建议：**
```python
# 更精确的判断：检查购买者是否赢得了主池
main_pot_winners = []  # 从边池分配中获取主池赢家
if idx not in main_pot_winners:
    # 购买者没有赢主池，赔付保险
    self.players[idx].chips += buy["payout_if_lose"]
```

---

### 4. 其他问题

#### 问题 4.1：两套引擎并存
**位置：** `core/game_logic.py` 和 `core/logic.py`

**问题描述：**
- 项目中有两套游戏引擎：
  - `game_logic.py`：新引擎（基于字典状态）
  - `logic.py`：旧引擎（基于对象）
- `tables.py` 中使用了 `game_logic.py`（新引擎）

**潜在问题：**
- 两套引擎可能有不同的 bug
- 维护成本高
- 容易混淆

**建议：**
- 统一使用一套引擎
- 如果新引擎更好，删除旧引擎
- 如果旧引擎更稳定，迁移到旧引擎

#### 问题 4.2：缺少完整的单元测试
**位置：** `tests/test_game_logic.py`

**问题描述：**
- 需要检查是否有完整的单元测试覆盖：
  - 2人对局
  - 多人对局
  - All-in 场景
  - 边池分配
  - 保险功能

**建议：**
- 补充完整的单元测试
- 特别是边池和保险的边界情况

---

## 📋 修复优先级

### P0（严重问题，必须修复）
1. ✅ **翻牌后第一个行动者计算错误** - 影响游戏流程
2. ✅ **底牌圈 BB 行动机会缺失** - 违反标准规则
3. ✅ **保险赔率计算错误** - 影响公平性

### P1（重要问题，应该修复）
4. ✅ **边池计算时机错误** - 影响用户体验
5. ✅ **玩家行动标记缺失** - 可能导致下注轮判断错误
6. ✅ **2人对局特殊处理缺失** - 影响2人游戏

### P2（优化建议）
7. ⚠️ **两套引擎并存** - 维护成本高
8. ⚠️ **缺少完整的单元测试** - 质量保证

---

## 🔧 修复建议

### 建议 1：重构行动顺序逻辑
**目标：** 统一和简化行动顺序的计算

**方案：**
```python
def get_first_to_act(game_state, stage):
    """
    获取指定阶段的第一个行动者。
    
    Args:
        game_state: 游戏状态
        stage: 游戏阶段（PREFLOP, FLOP, TURN, RIVER）
    
    Returns:
        player_id: 第一个行动者的 ID
    """
    player_order = game_state['player_order']  # 按座位顺序
    num_players = len(player_order)
    
    if stage == GameStage.PREFLOP:
        # 底牌圈：BB 的下一位（UTG）
        bb_player_id = game_state['bb_player_id']
        bb_index = player_order.index(bb_player_id)
        
        # 2人对局：SB 先行动
        if num_players == 2:
            sb_player_id = game_state['sb_player_id']
            return sb_player_id
        
        # 多人对局：UTG 先行动
        utg_index = (bb_index + 1) % num_players
        return player_order[utg_index]
    
    else:
        # 翻牌/转牌/河牌：庄位的下一位（SB）
        dealer_player_id = game_state['dealer_player_id']
        dealer_index = player_order.index(dealer_player_id)
        
        # 从庄位下一位开始，找第一个可行动的玩家
        for i in range(1, num_players + 1):
            next_index = (dealer_index + i) % num_players
            next_player_id = player_order[next_index]
            player_state = game_state['players'][next_player_id]
            
            if player_state.get('is_in_hand') and not player_state.get('is_all_in'):
                return next_player_id
        
        return None  # 所有人都 All-in 或弃牌
```

### 建议 2：完善边池显示
**目标：** 让玩家在游戏过程中看到边池信息

**方案：**
```python
# 在 tables.py 的 get_state() 中添加
def get_state(self, private_for_player_sid=None, emotes=None):
    # ... 现有代码 ...
    
    # 计算当前边池（实时显示）
    if self.state.get('current_pots'):
        out['side_pots'] = [
            {
                'amount': pot['amount'],
                'eligible_count': len(pot.get('eligible', []))
            }
            for pot in self.state['current_pots']
        ]
    
    return out
```

### 建议 3：统一引擎
**目标：** 删除旧引擎或迁移到旧引擎

**方案：**
1. 评估两套引擎的优劣
2. 选择更好的一套
3. 删除另一套
4. 更新所有引用

---

## 📝 总结

**主要问题：**
1. 行动顺序计算有多处错误
2. 边池计算时机不对
3. 保险赔率计算错误
4. 缺少完整的单元测试

**修复后的效果：**
- ✅ 符合标准德州扑克规则
- ✅ 边池显示更清晰
- ✅ 保险功能更公平
- ✅ 代码更易维护

**下一步：**
1. 修复 P0 和 P1 问题
2. 补充单元测试
3. 统一引擎
4. 更新行业专业技能记忆

---

**审查人：** 胖子（后端架构师）  
**审查日期：** 2026-03-11

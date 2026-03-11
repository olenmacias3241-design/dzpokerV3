# 德州扑克业务逻辑修复补丁

**修复日期：** 2026-03-11  
**修复人：** 胖子（后端架构师）

---

## 修复清单

### P0 修复（严重问题）

#### 1. 修复翻牌后第一个行动者计算

**文件：** `core/game_logic.py` - `advance_to_next_stage()`

**问题：** 翻牌/转牌/河牌圈第一个行动者计算错误

**修复前：**
```python
# Reset 'current_player_id' to the first active player after the button
dealer_pos = game_state.get('dealer_button_position', -1)
player_order = game_state.get('player_order')
if player_order:
    player_ids = [p for p in player_order if p in game_state['players']]
else:
    player_ids = list(game_state['players'].keys())
num_players = len(player_ids)

first_active_player = None
for i in range(1, num_players + 1):
    player_id = player_ids[(dealer_pos + i) % num_players]
    # ...
```

**修复后：**
```python
# 获取庄位玩家 ID（而不是索引）
player_order = game_state.get('player_order', [])
dealer_button_pos = game_state.get('dealer_button_position', 0)
dealer_button_pos = min(dealer_button_pos, len(player_order) - 1)
dealer_player_id = player_order[dealer_button_pos] if player_order else None

# 找到庄位玩家在 player_order 中的索引
if dealer_player_id and dealer_player_id in player_order:
    dealer_index = player_order.index(dealer_player_id)
else:
    dealer_index = 0

# 从庄位下一位开始找第一个可行动的玩家
num_players = len(player_order)
first_active_player = None
for i in range(1, num_players + 1):
    next_index = (dealer_index + i) % num_players
    next_player_id = player_order[next_index]
    player_state = game_state['players'].get(next_player_id)
    
    if player_state and player_state.get('is_in_hand') and not player_state.get('is_all_in'):
        first_active_player = next_player_id
        break

game_state['current_player_id'] = first_active_player
```

---

#### 2. 修复底牌圈 BB 行动机会

**文件：** `core/game_logic.py` - `find_next_player()`

**问题：** 底牌圈 BB 可能没有行动机会就结束

**修复前：**
```python
# 已跟齐，且已经回到 last_raiser → 本街结束
if last_raiser and next_player_id == last_raiser:
    return None, True
```

**修复后：**
```python
# 已跟齐，且已经回到 last_raiser
if last_raiser and next_player_id == last_raiser:
    # 底牌圈特殊处理：BB 是初始加注者，但需要给他行动机会
    stage = game_state.get('stage')
    bb_player_id = game_state.get('bb_player_id')
    
    if stage == GameStage.PREFLOP and last_raiser == bb_player_id:
        # 检查 BB 是否已经行动过（除了下盲注）
        bb_state = game_state['players'].get(bb_player_id)
        if bb_state and not bb_state.get('has_acted_preflop', False):
            # BB 还没有真正行动过，给他机会
            return bb_player_id, False
    
    # 其他情况：本街结束
    return None, True
```

---

#### 3. 修复保险赔率计算

**文件：** `core/logic.py` - `resolve_insurance()`

**问题：** 保险赔率计算公式错误

**修复前：**
```python
# 输时拿回 payout = premium / equity（公平赔率 1/E）
payout = premium_amount / max(equity, 0.01)
```

**修复后：**
```python
# 输时拿回 payout = premium / (1 - equity)（公平赔率 1/(1-E)）
# 例如：胜率 70%，赔率 = 1 / 0.3 = 3.33
payout = premium_amount / max(1 - equity, 0.01)
```

---

### P1 修复（重要问题）

#### 4. 添加玩家行动标记

**文件：** `core/game_logic.py` - `handle_player_action()`

**问题：** 缺少玩家行动标记，导致下注轮判断不准确

**修复：** 在每个行动处理后添加标记

```python
def handle_player_action(game_state, player_id, action, amount=0):
    # ... 现有代码 ...
    
    # --- State Update ---
    if action == PlayerAction.FOLD:
        player_state['is_active'] = False
        player_state['last_action'] = 'FOLD'
        player_state['has_acted'] = True  # 新增
    
    elif action == PlayerAction.CHECK:
        player_state['last_action'] = 'CHECK'
        player_state['has_acted'] = True  # 新增
    
    elif action == PlayerAction.CALL:
        # ... 现有代码 ...
        player_state['last_action'] = 'CALL'
        player_state['has_acted'] = True  # 新增
    
    elif action == PlayerAction.BET:
        # ... 现有代码 ...
        player_state['last_action'] = 'BET'
        player_state['has_acted'] = True  # 新增
    
    elif action == PlayerAction.RAISE:
        # ... 现有代码 ...
        player_state['last_action'] = 'RAISE'
        player_state['has_acted'] = True  # 新增
    
    # ... 继续 ...
```

**同时在 `advance_to_next_stage()` 中重置：**

```python
# Reset betting variables for the new round
game_state['amount_to_call'] = 0
game_state['last_raise_amount'] = 0
game_state['last_raiser_id'] = None

for player_id, player_state in game_state['players'].items():
    if player_state.get('is_active'):
        player_state['bet_this_round'] = 0
        player_state['last_action'] = None
        player_state['has_acted'] = False  # 新增
```

---

#### 5. 实时计算和显示边池

**文件：** `core/game_logic.py` - `advance_to_next_stage()`

**问题：** 边池只在最后比牌时计算，玩家看不到实时边池信息

**修复：** 在每次进入新街时计算边池

```python
def advance_to_next_stage(game_state):
    # ... 发牌逻辑 ...
    
    # 计算当前边池（用于实时显示）
    from . import pot_manager
    
    players_for_pot = {}
    for pid, pstate in game_state['players'].items():
        players_for_pot[pid] = {
            'total_bet_this_hand': pstate.get('total_bet_this_hand', 0),
            'is_folded': not pstate.get('is_in_hand', False) or not pstate.get('is_active', False)
        }
    
    # 存储当前边池信息（供前端显示）
    game_state['current_side_pots'] = pot_manager.calculate_side_pots(players_for_pot)
    
    # ... 继续 ...
```

---

#### 6. 添加 2人对局特殊处理

**文件：** `core/game_logic.py` - `start_new_hand()`

**问题：** 2人对局时，底牌圈应该是 SB 先行动，而不是 UTG

**修复：**

```python
def start_new_hand(game_state):
    # ... 现有代码 ...
    
    # First player to act
    num_players = len(active_player_ids)
    
    if num_players == 2:
        # 2人对局：小盲注先行动
        first_to_act_id = sb_player_id
    else:
        # 多人对局：UTG（BB 下一位）先行动
        utg_pos = (bb_pos + 1) % num_players
        first_to_act_id = active_player_ids[utg_pos]
    
    game_state['current_player_id'] = first_to_act_id
    game_state['last_raiser_id'] = bb_player_id  # BB 是初始"加注者"
    
    return game_state
```

---

#### 7. 修复保险触发条件

**文件：** `core/logic.py` - `_advance_to_next_street()`

**问题：** 保险可以在任何阶段触发，应该只在转牌/河牌前

**修复：**

```python
def _advance_to_next_street(self):
    # ... 现有代码 ...
    
    # 检查是否需要提供保险
    active_can_act = [i for i in range(n) if not self.players[i].has_folded and not self.players[i].is_all_in]
    if not active_can_act:
        all_in_indices = [i for i in range(n) if not self.players[i].has_folded and self.players[i].is_all_in]
        
        # 只在翻牌圈或转牌圈提供保险（河牌前）
        if self.insurance_enabled and len(all_in_indices) >= 2 and self.stage in ('flop', 'turn'):
            leading_idx, equities = self._compute_equity(all_in_indices)
            # ... 继续保险逻辑 ...
```

---

## 测试建议

### 测试场景 1：底牌圈 BB 行动
```python
# 场景：3人对局，无人加注，BB 应该有机会 Check 或 Raise
# 预期：轮到 BB 行动时，他可以 Check（结束底牌圈）或 Raise
```

### 测试场景 2：2人对局
```python
# 场景：2人对局，SB 应该先行动
# 预期：底牌圈第一个行动者是 SB，不是 BB
```

### 测试场景 3：边池显示
```python
# 场景：3人对局，一人 All-in 100，一人 All-in 200，一人 300
# 预期：
# - 主池：300（3人有资格）
# - 边池1：200（2人有资格）
# - 边池2：100（1人有资格）
# 在翻牌圈就应该能看到这些边池
```

### 测试场景 4：保险赔率
```python
# 场景：玩家胜率 70%，购买 100 筹码保险
# 预期：如果输了，赔付 100 / 0.3 = 333 筹码
```

---

## 部署步骤

1. **备份现有代码**
   ```bash
   cd /Users/taoyin/.openclaw/workspace/dzpokerV3
   cp core/game_logic.py core/game_logic.py.backup
   cp core/logic.py core/logic.py.backup
   ```

2. **应用修复**
   - 按照上述修复逐一修改代码
   - 或者使用 git diff 生成补丁文件

3. **运行单元测试**
   ```bash
   python -m pytest tests/test_game_logic.py -v
   ```

4. **手动测试**
   - 启动服务器
   - 测试上述 4 个场景
   - 验证修复是否生效

5. **回滚方案**
   ```bash
   # 如果出现问题，恢复备份
   cp core/game_logic.py.backup core/game_logic.py
   cp core/logic.py.backup core/logic.py
   ```

---

## 修复后的效果

✅ **符合标准德州扑克规则**
- 底牌圈 BB 有行动机会
- 2人对局 SB 先行动
- 翻牌后从庄位下一位开始

✅ **边池显示更清晰**
- 玩家在游戏过程中可以看到边池
- 知道自己有资格赢取哪些边池

✅ **保险功能更公平**
- 赔率计算正确
- 只在合适的时机提供保险

✅ **代码更健壮**
- 添加了行动标记
- 下注轮判断更准确

---

**修复人：** 胖子（后端架构师）  
**修复日期：** 2026-03-11

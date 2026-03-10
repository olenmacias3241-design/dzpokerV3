# 牌桌回放功能设计文档

## 🎯 功能说明

牌桌回放（Hand Replay）允许玩家回看已结束的牌局，包括：
- 每个玩家的手牌
- 每一轮的下注动作
- 公共牌的发放
- 最终的比牌结果

---

## 📊 数据结构

### 1. 回放数据表（已存在）

```sql
-- game_hands 表（已存在）
CREATE TABLE game_hands (
    id INT PRIMARY KEY AUTO_INCREMENT,
    table_id INT NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    community_cards VARCHAR(255),  -- "As,Kd,5c,Th,Js"
    final_pot_size BIGINT
);

-- hand_participants 表（已存在）
CREATE TABLE hand_participants (
    hand_id INT NOT NULL,
    user_id INT NOT NULL,
    seat_number INT NOT NULL,
    hole_cards VARCHAR(255) NOT NULL,  -- "Ac,Ad"
    win_amount BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (hand_id, user_id),
    FOREIGN KEY (hand_id) REFERENCES game_hands(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 2. 新增：行动记录表

```sql
CREATE TABLE hand_actions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    hand_id INT NOT NULL,
    user_id VARCHAR(255) NOT NULL,  -- 支持游客
    action_type VARCHAR(20) NOT NULL,  -- FOLD, CHECK, CALL, BET, RAISE, ALL_IN
    amount BIGINT,
    stage VARCHAR(20) NOT NULL,  -- PREFLOP, FLOP, TURN, RIVER
    action_order INT NOT NULL,  -- 行动顺序
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hand_id) REFERENCES game_hands(id),
    INDEX idx_hand_id (hand_id)
);
```

---

## 🔌 API 接口

### 1. 获取牌局列表

```
GET /api/replay/hands

Query Parameters:
- user_id: 玩家ID（可选，筛选该玩家参与的牌局）
- table_id: 牌桌ID（可选，筛选该牌桌的牌局）
- limit: 返回数量（默认20）
- offset: 偏移量（默认0）

Response:
{
  "hands": [
    {
      "hand_id": 123,
      "table_id": 1,
      "start_time": "2026-03-10T10:30:00Z",
      "final_pot": 1500,
      "participants": [
        {
          "user_id": "player1",
          "seat": 0,
          "win_amount": 1500
        },
        {
          "user_id": "player2",
          "seat": 1,
          "win_amount": 0
        }
      ]
    }
  ],
  "total": 100
}
```

### 2. 获取牌局详情

```
GET /api/replay/hands/{hand_id}

Response:
{
  "hand_id": 123,
  "table_id": 1,
  "start_time": "2026-03-10T10:30:00Z",
  "community_cards": ["As", "Kd", "5c", "Th", "Js"],
  "final_pot": 1500,
  
  "participants": [
    {
      "user_id": "player1",
      "username": "玩家1",
      "seat": 0,
      "hole_cards": ["Ac", "Ad"],
      "win_amount": 1500
    },
    {
      "user_id": "player2",
      "username": "玩家2",
      "seat": 1,
      "hole_cards": ["Kh", "Qh"],
      "win_amount": 0
    }
  ],
  
  "actions": [
    {
      "action_id": 1,
      "user_id": "player1",
      "action": "BET",
      "amount": 10,
      "stage": "PREFLOP",
      "order": 1
    },
    {
      "action_id": 2,
      "user_id": "player2",
      "action": "CALL",
      "amount": 10,
      "stage": "PREFLOP",
      "order": 2
    },
    // ... 更多行动
  ]
}
```

---

## 🎬 回放 UI 设计

### 1. 回放列表页面

```
┌─────────────────────────────────────────────┐
│  📜 牌局回放                                 │
│                                             │
│  筛选：[全部] [我参与的] [今天] [本周]       │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ 牌局 #123                            │   │
│  │ 时间：2026-03-10 10:30              │   │
│  │ 底池：1,500 筹码                     │   │
│  │ 玩家：玩家1 (赢), 玩家2              │   │
│  │ [查看回放]                           │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ 牌局 #122                            │   │
│  │ ...                                  │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  [加载更多]                                 │
└─────────────────────────────────────────────┘
```

### 2. 回放播放器

```
┌─────────────────────────────────────────────┐
│  📜 牌局回放 #123                            │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │                                     │   │
│  │        [牌桌视图]                    │   │
│  │     （与游戏界面相同）                │   │
│  │                                     │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ 当前阶段：Flop                       │   │
│  │ 当前行动：玩家1 下注 100             │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ [◀◀] [◀] [▶] [▶▶]                  │   │
│  │ ●────────────────────────○          │   │
│  │ 1/15                                │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  速度：[0.5x] [1x] [2x] [4x]               │
│                                             │
│  [关闭]                                     │
└─────────────────────────────────────────────┘
```

**控制按钮：**
- ◀◀ 回到开始
- ◀ 上一步
- ▶ 下一步
- ▶▶ 跳到结束
- 进度条：拖动到任意步骤
- 速度：0.5x, 1x, 2x, 4x

---

## 💻 后端实现

### 1. 数据库迁移

```python
# database/migrations/add_hand_actions.py

def upgrade():
    """创建 hand_actions 表"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hand_actions (
            id INT PRIMARY KEY AUTO_INCREMENT,
            hand_id INT NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            action_type VARCHAR(20) NOT NULL,
            amount BIGINT,
            stage VARCHAR(20) NOT NULL,
            action_order INT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hand_id) REFERENCES game_hands(id),
            INDEX idx_hand_id (hand_id)
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
```

### 2. 记录行动

在 `tables.py` 的 `process_action` 函数中添加：

```python
def process_action(db, table_id, seat_index, action_str, amount=0):
    # ... 现有代码 ...
    
    # 记录行动到数据库
    hand_id = table.get("current_hand_id")
    if db and hand_id:
        from database.models import HandAction
        
        action_order = db.query(HandAction).filter_by(hand_id=hand_id).count() + 1
        
        db.add(HandAction(
            hand_id=hand_id,
            user_id=user_id,
            action_type=action.name,
            amount=int(amount) if amount else None,
            stage=wrapper.state.get("stage", "UNKNOWN"),
            action_order=action_order
        ))
    
    # ... 现有代码 ...
```

### 3. API 路由

```python
# app.py

@app.route("/api/replay/hands")
def api_replay_hands():
    """获取牌局列表"""
    user_id = request.args.get("user_id")
    table_id = request.args.get("table_id")
    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))
    
    db = SessionLocal()
    try:
        query = db.query(GameHand)
        
        if user_id:
            query = query.join(HandParticipant).filter(
                HandParticipant.user_id == user_id
            )
        
        if table_id:
            query = query.filter(GameHand.table_id == table_id)
        
        total = query.count()
        hands = query.order_by(GameHand.start_time.desc()).offset(offset).limit(limit).all()
        
        result = []
        for hand in hands:
            participants = db.query(HandParticipant).filter_by(hand_id=hand.id).all()
            result.append({
                "hand_id": hand.id,
                "table_id": hand.table_id,
                "start_time": hand.start_time.isoformat(),
                "final_pot": hand.final_pot_size,
                "participants": [
                    {
                        "user_id": p.user_id,
                        "seat": p.seat_number,
                        "win_amount": p.win_amount
                    }
                    for p in participants
                ]
            })
        
        return jsonify({"hands": result, "total": total})
    
    finally:
        db.close()


@app.route("/api/replay/hands/<int:hand_id>")
def api_replay_hand_detail(hand_id):
    """获取牌局详情"""
    db = SessionLocal()
    try:
        hand = db.query(GameHand).filter_by(id=hand_id).first()
        if not hand:
            return jsonify({"error": "牌局不存在"}), 404
        
        participants = db.query(HandParticipant).filter_by(hand_id=hand_id).all()
        actions = db.query(HandAction).filter_by(hand_id=hand_id).order_by(HandAction.action_order).all()
        
        return jsonify({
            "hand_id": hand.id,
            "table_id": hand.table_id,
            "start_time": hand.start_time.isoformat(),
            "community_cards": hand.community_cards.split(",") if hand.community_cards else [],
            "final_pot": hand.final_pot_size,
            "participants": [
                {
                    "user_id": p.user_id,
                    "seat": p.seat_number,
                    "hole_cards": p.hole_cards.split(",") if p.hole_cards else [],
                    "win_amount": p.win_amount
                }
                for p in participants
            ],
            "actions": [
                {
                    "action_id": a.id,
                    "user_id": a.user_id,
                    "action": a.action_type,
                    "amount": a.amount,
                    "stage": a.stage,
                    "order": a.action_order
                }
                for a in actions
            ]
        })
    
    finally:
        db.close()
```

---

## 🎨 前端实现

### 1. 回放播放器组件

```javascript
class ReplayPlayer {
    constructor(handId) {
        this.handId = handId;
        this.currentStep = 0;
        this.steps = [];
        this.speed = 1;
        this.isPlaying = false;
    }
    
    async load() {
        const response = await fetch(`/api/replay/hands/${this.handId}`);
        const data = await response.json();
        
        // 构建回放步骤
        this.steps = this.buildSteps(data);
        this.render();
    }
    
    buildSteps(data) {
        const steps = [];
        
        // 步骤1：发底牌
        steps.push({
            type: 'deal_hole_cards',
            participants: data.participants
        });
        
        // 步骤2-N：每个行动
        for (const action of data.actions) {
            steps.push({
                type: 'action',
                ...action
            });
            
            // 在阶段转换时插入发牌步骤
            if (this.isStageChange(action, data.actions)) {
                steps.push({
                    type: 'deal_community',
                    stage: action.stage
                });
            }
        }
        
        // 最后一步：比牌
        steps.push({
            type: 'showdown',
            participants: data.participants
        });
        
        return steps;
    }
    
    play() {
        this.isPlaying = true;
        this.playNextStep();
    }
    
    pause() {
        this.isPlaying = false;
    }
    
    playNextStep() {
        if (!this.isPlaying || this.currentStep >= this.steps.length) {
            this.isPlaying = false;
            return;
        }
        
        this.executeStep(this.steps[this.currentStep]);
        this.currentStep++;
        
        setTimeout(() => {
            this.playNextStep();
        }, 1000 / this.speed);
    }
    
    executeStep(step) {
        switch (step.type) {
            case 'deal_hole_cards':
                this.dealHoleCards(step.participants);
                break;
            case 'action':
                this.showAction(step);
                break;
            case 'deal_community':
                this.dealCommunity(step.stage);
                break;
            case 'showdown':
                this.showdown(step.participants);
                break;
        }
    }
    
    // ... 其他方法 ...
}
```

---

## ✅ 实现步骤

1. **数据库**（必须）
   - 创建 `hand_actions` 表
   - 在 `process_action` 中记录行动

2. **API**（必须）
   - 获取牌局列表
   - 获取牌局详情

3. **前端列表**（重要）
   - 回放列表页面
   - 筛选和分页

4. **前端播放器**（重要）
   - 回放播放器组件
   - 播放控制（播放/暂停/跳转）

5. **动画优化**（可选）
   - 平滑的发牌动画
   - 行动提示动画

---

## 📱 响应式设计

- PC：完整的播放器界面
- 移动：简化的控制按钮，竖屏优化

---

**预计开发时间：** 1-2 天

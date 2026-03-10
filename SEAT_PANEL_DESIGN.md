# 玩家座位控制面板设计规范

## 🎯 设计目标

每个玩家的座位不只是显示信息，而是一个**精致的控制面板**，要：
- 信息清晰易读
- 视觉精致有质感
- 状态一目了然
- 动画流畅自然

---

## 📐 座位面板结构

### 完整布局

```
┌─────────────────────────────┐
│  ┌─────┐                    │ ← 半透明背景卡片
│  │头像 │  玩家昵称           │
│  │     │  💰 10,000         │ ← 筹码余额
│  └─────┘                    │
│                             │
│  [Dealer] 或 [SB] 或 [BB]   │ ← 位置标记
│                             │
│  当前下注: 💰 200            │ ← 本轮下注
│                             │
│  ⏱️ 15s                     │ ← 倒计时（轮到时）
└─────────────────────────────┘
       ↓ 筹码堆 ↓              ← 下注筹码（在面板外）
```

---

## 🎨 视觉设计

### 1. 背景卡片

```css
.seat-panel {
  /* 半透明玻璃质感 */
  background: rgba(26, 44, 61, 0.85);
  backdrop-filter: blur(10px);
  
  /* 圆角和边框 */
  border-radius: 12px;
  border: 2px solid rgba(255, 191, 87, 0.3);
  
  /* 阴影 */
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  
  /* 内边距 */
  padding: 12px;
  
  /* 尺寸 */
  width: 140px;
  min-height: 100px;
}
```

### 2. 头像

```css
.seat-avatar {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  border: 3px solid #FFBF57; /* 金色边框 */
  box-shadow: 0 2px 10px rgba(255, 191, 87, 0.5);
  object-fit: cover;
}

/* 默认头像（空座位） */
.seat-avatar.empty {
  background: linear-gradient(135deg, #2C3E50, #34495E);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #7F8C8D;
  font-size: 24px;
}
```

### 3. 玩家信息

```css
.seat-info {
  margin-left: 70px; /* 头像右侧 */
  margin-top: -60px; /* 与头像对齐 */
}

.seat-username {
  font-size: 14px;
  font-weight: bold;
  color: #FFFFFF;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
  margin-bottom: 4px;
  
  /* 文字溢出处理 */
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.seat-chips {
  font-size: 13px;
  color: #FFBF57; /* 金色 */
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

.seat-chips::before {
  content: "💰";
  font-size: 14px;
}
```

### 4. 位置标记（Dealer/SB/BB）

```css
.seat-position {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: bold;
  margin-top: 8px;
  text-transform: uppercase;
}

/* Dealer 按钮 */
.seat-position.dealer {
  background: linear-gradient(135deg, #E74C3C, #C0392B);
  color: #FFFFFF;
  box-shadow: 0 2px 8px rgba(231, 76, 60, 0.5);
}

/* Small Blind */
.seat-position.sb {
  background: linear-gradient(135deg, #3498DB, #2980B9);
  color: #FFFFFF;
  box-shadow: 0 2px 8px rgba(52, 152, 219, 0.5);
}

/* Big Blind */
.seat-position.bb {
  background: linear-gradient(135deg, #F39C12, #E67E22);
  color: #FFFFFF;
  box-shadow: 0 2px 8px rgba(243, 156, 18, 0.5);
}
```

### 5. 当前下注

```css
.seat-current-bet {
  margin-top: 8px;
  font-size: 12px;
  color: #2ECC71; /* 绿色 */
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

.seat-current-bet::before {
  content: "💰";
  font-size: 13px;
}

/* 没有下注时隐藏 */
.seat-current-bet.zero {
  display: none;
}
```

### 6. 倒计时（轮到玩家时）

```css
.seat-timer {
  margin-top: 8px;
  font-size: 16px;
  font-weight: bold;
  color: #E74C3C; /* 红色 */
  display: flex;
  align-items: center;
  gap: 4px;
  animation: pulse 1s infinite;
}

.seat-timer::before {
  content: "⏱️";
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* 环形进度条 */
.seat-timer-ring {
  position: absolute;
  top: -5px;
  left: -5px;
  width: 70px;
  height: 70px;
  border-radius: 50%;
  border: 3px solid transparent;
  border-top-color: #E74C3C;
  animation: spin 15s linear;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

---

## 🎭 状态样式

### 1. 当前行动者（高亮）

```css
.seat-panel.active {
  border-color: #FFBF57;
  box-shadow: 
    0 0 20px rgba(255, 191, 87, 0.6),
    0 4px 20px rgba(0, 0, 0, 0.4);
  animation: glow 2s infinite;
}

@keyframes glow {
  0%, 100% { 
    box-shadow: 0 0 20px rgba(255, 191, 87, 0.6);
  }
  50% { 
    box-shadow: 0 0 30px rgba(255, 191, 87, 0.9);
  }
}
```

### 2. 已弃牌

```css
.seat-panel.folded {
  opacity: 0.4;
  filter: grayscale(100%);
}

.seat-panel.folded .seat-avatar {
  border-color: #7F8C8D;
}
```

### 3. All-in

```css
.seat-panel.all-in {
  border-color: #E74C3C;
}

.seat-panel.all-in::after {
  content: "ALL-IN";
  position: absolute;
  top: -10px;
  right: -10px;
  background: linear-gradient(135deg, #E74C3C, #C0392B);
  color: #FFFFFF;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: bold;
  box-shadow: 0 2px 8px rgba(231, 76, 60, 0.6);
}
```

### 4. 空座位

```css
.seat-panel.empty {
  background: rgba(26, 44, 61, 0.5);
  border-style: dashed;
  border-color: rgba(255, 255, 255, 0.2);
  cursor: pointer;
  transition: all 0.3s;
}

.seat-panel.empty:hover {
  background: rgba(26, 44, 61, 0.7);
  border-color: rgba(255, 191, 87, 0.5);
  transform: scale(1.05);
}

.seat-panel.empty .seat-info {
  text-align: center;
  color: #7F8C8D;
  font-size: 12px;
}
```

### 5. 赢家（比牌后）

```css
.seat-panel.winner {
  border-color: #2ECC71;
  animation: winner-glow 1s infinite;
}

@keyframes winner-glow {
  0%, 100% { 
    box-shadow: 0 0 30px rgba(46, 204, 113, 0.8);
  }
  50% { 
    box-shadow: 0 0 50px rgba(46, 204, 113, 1);
  }
}

/* 赢家标记 */
.seat-panel.winner::before {
  content: "🏆";
  position: absolute;
  top: -15px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 30px;
  animation: bounce 0.5s;
}

@keyframes bounce {
  0%, 100% { transform: translateX(-50%) translateY(0); }
  50% { transform: translateX(-50%) translateY(-10px); }
}
```

---

## 📱 响应式适配

### PC 端

```css
.seat-panel {
  width: 140px;
  min-height: 100px;
  padding: 12px;
}

.seat-avatar {
  width: 60px;
  height: 60px;
}

.seat-username {
  font-size: 14px;
}
```

### 手机端

```css
@media (max-width: 767px) {
  .seat-panel {
    width: 100px;
    min-height: 80px;
    padding: 8px;
  }
  
  .seat-avatar {
    width: 40px;
    height: 40px;
  }
  
  .seat-username {
    font-size: 11px;
  }
  
  .seat-chips {
    font-size: 10px;
  }
}
```

---

## 🎬 动画效果

### 1. 入座动画

```css
@keyframes seat-enter {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.seat-panel.entering {
  animation: seat-enter 0.3s ease-out;
}
```

### 2. 离座动画

```css
@keyframes seat-leave {
  from {
    opacity: 1;
    transform: scale(1);
  }
  to {
    opacity: 0;
    transform: scale(0.8);
  }
}

.seat-panel.leaving {
  animation: seat-leave 0.3s ease-in;
}
```

### 3. 下注动画

```css
@keyframes bet-update {
  0% { transform: scale(1); }
  50% { transform: scale(1.2); color: #2ECC71; }
  100% { transform: scale(1); }
}

.seat-current-bet.updating {
  animation: bet-update 0.3s;
}
```

---

## 🎯 实现优先级

1. **基础布局**（必须）
   - 头像 + 昵称 + 筹码
   - 半透明背景
   - 圆角边框

2. **位置标记**（必须）
   - Dealer/SB/BB 按钮
   - 不同颜色区分

3. **状态显示**（必须）
   - 当前下注
   - 倒计时（轮到时）
   - 高亮效果

4. **高级状态**（重要）
   - 已弃牌（灰色）
   - All-in 标记
   - 赢家特效

5. **动画效果**（优化）
   - 入座/离座
   - 下注更新
   - 脉冲高亮

---

## 📄 HTML 结构示例

```html
<div class="seat-panel active" data-seat="0">
  <!-- 头像 -->
  <img src="avatar.jpg" class="seat-avatar" alt="玩家头像">
  
  <!-- 倒计时环（轮到时显示） -->
  <div class="seat-timer-ring"></div>
  
  <!-- 玩家信息 -->
  <div class="seat-info">
    <div class="seat-username">玩家昵称</div>
    <div class="seat-chips">10,000</div>
  </div>
  
  <!-- 位置标记 -->
  <div class="seat-position dealer">Dealer</div>
  
  <!-- 当前下注 -->
  <div class="seat-current-bet">200</div>
  
  <!-- 倒计时 -->
  <div class="seat-timer">15s</div>
</div>
```

---

## 🎨 参考

搜索关键词：
- "poker player panel UI"
- "德州扑克 玩家信息面板"
- "PokerStars player card"
- "传奇扑克 座位设计"

关键是要**精致、清晰、有质感**！

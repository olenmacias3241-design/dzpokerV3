# 保险功能 UI 设计文档

## 🎯 功能说明

保险（Insurance）是德州扑克中的一个高级功能，允许玩家在特定情况下购买"保险"来降低风险。

### 触发条件
- 阶段：Turn（转牌）或 River（河牌）前
- 情况：玩家有听牌（如同花听牌、顺子听牌）
- 对手：已经 All-in 或下大注

---

## 📐 UI 设计

### 1. 保险触发提示

当满足保险条件时，在牌桌中央弹出提示：

```
┌─────────────────────────────────────┐
│  🎰 保险机会                         │
│                                     │
│  你有同花听牌！                      │
│  可以购买保险降低风险                │
│                                     │
│  [查看详情]  [跳过]                  │
└─────────────────────────────────────┘
```

**样式：**
```css
.insurance-prompt {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  
  background: rgba(26, 44, 61, 0.95);
  backdrop-filter: blur(10px);
  
  border: 2px solid #FFBF57;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6);
  
  padding: 24px;
  min-width: 400px;
  
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translate(-50%, -60%);
  }
  to {
    opacity: 1;
    transform: translate(-50%, -50%);
  }
}
```

---

### 2. 保险详情面板

点击"查看详情"后展开：

```
┌─────────────────────────────────────────────┐
│  🎰 保险详情                                 │
│                                             │
│  当前牌面：                                  │
│  [你的手牌] [公共牌]                         │
│                                             │
│  听牌类型：同花听牌                          │
│  可保险牌：♠️ A ♠️ K ♠️ Q ♠️ J ♠️ 10 ...    │
│  出牌数：9 张                                │
│  胜率：约 35%                                │
│                                             │
│  保险赔率：1:2.5                             │
│  最大保费：500 筹码                          │
│                                             │
│  ┌─────────────────────────────┐            │
│  │ 保费金额                     │            │
│  │ [滑块] 0 ────●──── 500      │            │
│  │                             │            │
│  │ 预设：[100] [200] [300] [500]│            │
│  └─────────────────────────────┘            │
│                                             │
│  预期收益：                                  │
│  - 中牌：赔付 1,250 筹码                     │
│  - 不中：损失 500 筹码                       │
│                                             │
│  [购买保险]  [不买，继续游戏]                │
└─────────────────────────────────────────────┘
```

**样式：**
```css
.insurance-panel {
  max-width: 500px;
  padding: 32px;
}

.insurance-cards {
  display: flex;
  gap: 8px;
  margin: 16px 0;
}

.insurance-outs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 8px 0;
}

.insurance-out-card {
  display: inline-block;
  padding: 4px 8px;
  background: rgba(255, 191, 87, 0.2);
  border: 1px solid #FFBF57;
  border-radius: 4px;
  font-size: 14px;
}

.insurance-slider {
  width: 100%;
  margin: 16px 0;
}

.insurance-presets {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.insurance-preset-btn {
  flex: 1;
  padding: 8px;
  background: rgba(255, 191, 87, 0.2);
  border: 1px solid #FFBF57;
  border-radius: 8px;
  color: #FFBF57;
  cursor: pointer;
  transition: all 0.2s;
}

.insurance-preset-btn:hover {
  background: rgba(255, 191, 87, 0.4);
  transform: scale(1.05);
}

.insurance-summary {
  background: rgba(46, 204, 113, 0.1);
  border: 1px solid #2ECC71;
  border-radius: 8px;
  padding: 12px;
  margin: 16px 0;
}
```

---

### 3. ALL-IN 按钮设计

ALL-IN 按钮需要特别醒目，因为这是一个重要的决策。

**正常状态：**
```css
.btn-all-in {
  background: linear-gradient(135deg, #E74C3C, #C0392B);
  color: #FFFFFF;
  font-size: 18px;
  font-weight: bold;
  padding: 16px 32px;
  border: 3px solid #FFFFFF;
  border-radius: 12px;
  box-shadow: 
    0 4px 20px rgba(231, 76, 60, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  
  text-transform: uppercase;
  letter-spacing: 2px;
  
  cursor: pointer;
  transition: all 0.3s;
  
  position: relative;
  overflow: hidden;
}

/* 发光动画 */
.btn-all-in::before {
  content: "";
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(
    45deg,
    transparent,
    rgba(255, 255, 255, 0.3),
    transparent
  );
  animation: shine 3s infinite;
}

@keyframes shine {
  0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
  100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
}

/* 悬停状态 */
.btn-all-in:hover {
  transform: scale(1.1);
  box-shadow: 
    0 6px 30px rgba(231, 76, 60, 0.8),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

/* 点击状态 */
.btn-all-in:active {
  transform: scale(1.05);
  box-shadow: 
    0 2px 10px rgba(231, 76, 60, 0.6),
    inset 0 2px 4px rgba(0, 0, 0, 0.3);
}

/* 禁用状态 */
.btn-all-in:disabled {
  background: linear-gradient(135deg, #7F8C8D, #95A5A6);
  border-color: #BDC3C7;
  cursor: not-allowed;
  opacity: 0.5;
}
```

**HTML 结构：**
```html
<button class="btn-all-in" id="all-in-btn">
  <span class="btn-icon">🔥</span>
  <span class="btn-text">ALL-IN</span>
  <span class="btn-amount">10,000</span>
</button>
```

---

### 4. 保险购买确认

点击"购买保险"后，显示确认对话框：

```
┌─────────────────────────────────┐
│  ⚠️ 确认购买保险                 │
│                                 │
│  保费：500 筹码                  │
│  赔率：1:2.5                     │
│  最大赔付：1,250 筹码            │
│                                 │
│  确定要购买吗？                  │
│                                 │
│  [确认购买]  [取消]              │
└─────────────────────────────────┘
```

---

### 5. 保险结果显示

#### 中牌（赢得保险）

```
┌─────────────────────────────────┐
│  🎉 保险生效！                   │
│                                 │
│  河牌：♠️ A                      │
│  你中了同花！                    │
│                                 │
│  保险赔付：1,250 筹码            │
│  净收益：+750 筹码               │
│                                 │
│  [继续游戏]                      │
└─────────────────────────────────┘
```

**动画效果：**
- 金币从天而降
- 绿色发光效果
- 庆祝音效

#### 不中牌（保险失效）

```
┌─────────────────────────────────┐
│  😔 保险未生效                   │
│                                 │
│  河牌：♦️ 7                      │
│  未中同花                        │
│                                 │
│  保险费：-500 筹码               │
│                                 │
│  [继续游戏]                      │
└─────────────────────────────────┘
```

---

## 📱 响应式设计

### PC 端
- 面板宽度：400-500px
- 字体大小：14-16px
- 按钮高度：48px

### 移动端
```css
@media (max-width: 767px) {
  .insurance-panel {
    max-width: 90vw;
    padding: 20px;
  }
  
  .insurance-cards {
    flex-wrap: wrap;
  }
  
  .insurance-presets {
    flex-direction: column;
  }
  
  .btn-all-in {
    width: 100%;
    padding: 20px;
    font-size: 20px;
  }
}
```

---

## 🎬 动画效果

### 1. 面板弹出
```css
@keyframes popIn {
  0% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.8);
  }
  100% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}
```

### 2. 保险生效（中牌）
```css
@keyframes celebrate {
  0%, 100% { transform: scale(1); }
  25% { transform: scale(1.1) rotate(-5deg); }
  75% { transform: scale(1.1) rotate(5deg); }
}
```

### 3. 保险失效（不中）
```css
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-10px); }
  75% { transform: translateX(10px); }
}
```

---

## 🎯 交互流程

1. **触发保险**
   - 检测听牌情况
   - 显示保险提示

2. **查看详情**
   - 展开保险面板
   - 显示可保险牌、赔率、保费

3. **选择保费**
   - 拖动滑块或点击预设
   - 实时显示预期收益

4. **购买确认**
   - 显示确认对话框
   - 确认后扣除保费

5. **发牌**
   - 发出河牌
   - 判断是否中牌

6. **结果显示**
   - 中牌：显示赔付金额
   - 不中：显示保费损失

---

## 📄 API 接口

### 购买保险
```
POST /api/tables/{table_id}/insurance

Request:
{
  "token": "player_token",
  "amount": 500
}

Response:
{
  "ok": true,
  "insurance": {
    "amount": 500,
    "odds": 2.5,
    "max_payout": 1250
  }
}
```

### 拒绝保险
```
POST /api/tables/{table_id}/insurance/decline

Request:
{
  "token": "player_token"
}

Response:
{
  "ok": true
}
```

---

## 🎨 视觉参考

- 保险面板：半透明深色背景，金色边框
- ALL-IN 按钮：红色渐变，白色边框，发光效果
- 中牌动画：金币、绿色光效、庆祝音效
- 不中动画：灰色、摇晃效果、失望音效

---

## ✅ 实现优先级

1. **基础功能**（必须）
   - 保险触发检测
   - 保险面板显示
   - 购买/拒绝接口

2. **ALL-IN 按钮**（必须）
   - 醒目的视觉设计
   - 发光动画
   - 点击反馈

3. **保险详情**（重要）
   - 可保险牌显示
   - 赔率计算
   - 保费滑块

4. **结果动画**（优化）
   - 中牌庆祝
   - 不中反馈
   - 音效

---

**备注：** 保险功能是高级功能，需要在核心游戏流程稳定后再实现。

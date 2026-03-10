# Figma 资源导出清单

**导出时间：** 2026-03-10 12:28  
**总文件数：** 50 个  
**总大小：** 1.1GB

---

## 📁 资源分类

### 1. 完整页面 (4个)

位置：`static/images/assets/pages/`

- `德州扑克大厅.png` (1.0MB) - 游戏大厅主界面
- `挑战中心.png` (1.3MB) - 挑战中心页面
- `新闻.png` (1.0MB) - 新闻页面
- `牌友.png` (878KB) - 牌友页面

### 2. 图标 (7个)

位置：`static/images/assets/icons/`

- `tuijian_42:1751.png` - 推荐图标
- `paiyou_42:1755.png` - 牌友图标
- `qingqiu_42:1759.png` - 请求图标
- `jinqi_42:1763.png` - 近期图标
- `serach_42:1775.png` - 搜索图标
- `xinwen_52:12.png` - 新闻图标
- `jiangli_52:8.png` - 奖励图标

### 3. 按钮 (7个)

位置：`static/images/assets/buttons/`

- `Target_52:104.png` - 目标按钮
- `Target_blue_52:114.png` - 蓝色目标按钮
- `Target_green_45:1214.png` - 绿色目标按钮
- `Target_left_45:276.png` - 左侧目标按钮
- `Target_bottom_45:1275.png` - 底部目标按钮
- `right_green_52:107.png` - 右侧绿色按钮
- `friends_none_42:1767.png` - 无好友按钮

### 4. 扑克牌 (1个)

位置：`static/images/assets/cards/`

- `poker_52:109.png` - 扑克牌

### 5. 筹码 (2个)

位置：`static/images/assets/chips/`

- `coin_52:46.png` - 金币
- `tiket_45:1218.png` - 票券

### 6. UI 元素 (29个)

位置：`static/images/assets/ui/`

包含各种 Frame、Layer、Lock 等 UI 组件。

---

## 🎯 下一步工作

### 需要继续导出的资源

1. **扑克牌完整套装** (52张)
   - 需要导出所有花色和点数的牌
   - 牌背面设计

2. **筹码完整套装** (7种面额)
   - 白色 (1)
   - 红色 (5)
   - 蓝色 (10)
   - 绿色 (25)
   - 黑色 (100)
   - 紫色 (500)
   - 橙色 (1000)

3. **游戏牌桌界面**
   - 德州扑克牌桌内-轮到自己操作 (239:197)
   - 德州扑克牌桌内-进入牌桌等待下一局开始 (239:2)
   - 德州扑克牌桌内-自己获胜 (243:2771)
   - 等等...

4. **行动按钮**
   - Fold, Check, Call, Bet, Raise, All-in
   - 不同状态（normal, hover, active）

5. **位置标记**
   - Dealer 按钮
   - SB/BB 标记

6. **背景和纹理**
   - 牌桌毛毡
   - 木质边框
   - 房间背景

---

## 📝 使用说明

### 在前端中引用

```html
<!-- 页面 -->
<img src="/static/images/assets/pages/德州扑克大厅.png" alt="游戏大厅">

<!-- 图标 -->
<img src="/static/images/assets/icons/tuijian_42:1751.png" alt="推荐">

<!-- 按钮 -->
<img src="/static/images/assets/buttons/Target_green_45:1214.png" alt="绿色按钮">

<!-- 扑克牌 -->
<img src="/static/images/assets/cards/poker_52:109.png" alt="扑克牌">

<!-- 筹码 -->
<img src="/static/images/assets/chips/coin_52:46.png" alt="金币">
```

### CSS 背景图

```css
.game-hall {
  background-image: url('/static/images/assets/pages/德州扑克大厅.png');
  background-size: cover;
}

.icon-recommend {
  background-image: url('/static/images/assets/icons/tuijian_42:1751.png');
  width: 24px;
  height: 24px;
}
```

---

## 🔧 继续导出

要导出更多资源，可以：

1. **修改 `figma_export.py`**
   - 增加 `max_export` 数量
   - 指定特定的节点 ID

2. **使用 Figma 手动导出**
   - 在 Figma 中选择元素
   - 右侧面板 → Export
   - 选择格式和尺寸

3. **使用 Figma 插件**
   - Figma to Code
   - Anima
   - Zeplin

---

**备注：** 当前导出的是第一批资源，主要是页面和基础 UI 元素。游戏核心资源（扑克牌、筹码、按钮等）需要进一步导出。

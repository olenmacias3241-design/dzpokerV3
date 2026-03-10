# UI 切图要求文档

## 📋 切图规范

### 1. 图片格式

**优先使用：**
- PNG（透明背景）
- SVG（矢量图，可缩放）

**备选：**
- JPG（背景图）
- WebP（优化版本）

### 2. 命名规范

```
类型_名称_状态.格式

示例：
- btn_fold_normal.png
- btn_fold_hover.png
- btn_fold_active.png
- chip_red_100.png
- card_back.png
- table_bg.jpg
```

### 3. 尺寸要求

#### 扑克牌
- 标准尺寸：140x200px (@2x: 280x400px)
- 移动端：100x140px (@2x: 200x280px)
- 需要：52张牌 + 1张背面

#### 筹码
- 标准尺寸：60x60px (@2x: 120x120px)
- 移动端：40x40px (@2x: 80x80px)
- 需要：5-7种面额（不同颜色）

#### 按钮
- 标准尺寸：120x40px (@2x: 240x80px)
- 移动端：150x50px (@2x: 300x100px)
- 需要：每个按钮 3 种状态（normal/hover/active）

#### 头像
- 标准尺寸：80x80px (@2x: 160x160px)
- 移动端：60x60px (@2x: 120x120px)
- 圆形或方形（CSS 可处理）

#### 位置标记（Dealer/SB/BB）
- 标准尺寸：40x40px (@2x: 80x80px)
- 移动端：30x30px (@2x: 60x60px)

#### 牌桌背景
- PC：1920x1080px
- 移动：750x1334px
- 可平铺的纹理：512x512px

### 4. 必需的图片资源

#### 扑克牌（54张）
```
cards/
  ├── spades/    (黑桃 A-K)
  ├── hearts/    (红心 A-K)
  ├── diamonds/  (方块 A-K)
  ├── clubs/     (梅花 A-K)
  └── back.png   (背面)
```

#### 筹码（7种）
```
chips/
  ├── chip_1.png      (白色, 1)
  ├── chip_5.png      (红色, 5)
  ├── chip_10.png     (蓝色, 10)
  ├── chip_25.png     (绿色, 25)
  ├── chip_100.png    (黑色, 100)
  ├── chip_500.png    (紫色, 500)
  └── chip_1000.png   (橙色, 1000)
```

#### 按钮（7个 x 3状态 = 21张）
```
buttons/
  ├── fold/
  │   ├── normal.png
  │   ├── hover.png
  │   └── active.png
  ├── check/
  ├── call/
  ├── bet/
  ├── raise/
  ├── all-in/
  └── insurance/
```

#### 位置标记（3个）
```
positions/
  ├── dealer.png
  ├── sb.png
  └── bb.png
```

#### 背景和纹理
```
backgrounds/
  ├── table_felt.jpg      (牌桌毛毡)
  ├── table_wood.jpg      (木质边框)
  ├── room_bg.jpg         (房间背景)
  └── felt_texture.png    (毛毡纹理，可平铺)
```

#### 图标和装饰
```
icons/
  ├── coin.png           (金币图标)
  ├── trophy.png         (奖杯)
  ├── timer.png          (计时器)
  ├── settings.png       (设置)
  └── close.png          (关闭)
```

### 5. 临时方案：从传奇扑克切图

#### 优先切图列表

1. **扑克牌**（最高优先级）
   - 52张牌 + 背面
   - 清晰可读

2. **筹码**（高优先级）
   - 至少 5 种面额
   - 不同颜色区分

3. **牌桌背景**（高优先级）
   - 绿色毛毡
   - 木质边框

4. **按钮**（中优先级）
   - Fold, Call, Raise, All-in
   - 至少 normal 状态

5. **位置标记**（中优先级）
   - Dealer, SB, BB

#### 切图工具

- Chrome DevTools（F12 → Elements → 右键 → Copy image）
- 截图工具（Snipaste, ShareX）
- 在线工具（remove.bg 去背景）

#### 注意事项

- ⚠️ 仅用于临时开发，不用于正式发布
- ⚠️ 后续会替换成正式设计
- ⚠️ 保持图片清晰度
- ⚠️ 统一风格

### 6. 图片优化

- 使用 TinyPNG 压缩
- 移除不必要的元数据
- 提供 @2x 高清版本
- 考虑使用 WebP 格式

### 7. 文件结构

```
static/
  └── images/
      ├── cards/
      ├── chips/
      ├── buttons/
      ├── positions/
      ├── backgrounds/
      └── icons/
```

### 8. CSS Sprites（可选）

对于小图标，可以合并成一张雪碧图：
- 减少 HTTP 请求
- 提高加载速度
- 使用工具：Sprite Cow, CSS Sprite Generator

---

## 📦 交付清单

- [ ] 扑克牌（54张）
- [ ] 筹码（7种）
- [ ] 按钮（7个 x 3状态）
- [ ] 位置标记（3个）
- [ ] 牌桌背景（2个尺寸）
- [ ] 图标和装饰（5个）
- [ ] @2x 高清版本
- [ ] 压缩优化后的版本

---

## 🎯 临时方案执行

1. 访问传奇扑克网站
2. 使用 DevTools 或截图工具
3. 按照上述规范切图
4. 保存到 `static/images/` 对应目录
5. 在代码中引用

**预计时间：** 2-3 小时

**后续：** 等正式设计稿到位后替换

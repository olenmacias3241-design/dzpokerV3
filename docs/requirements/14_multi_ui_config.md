# 14 - 多 UI 切换设计

**文档类型**：产品需求规格（多 UI 切换与配置）  
**关联**：`docs/requirements/04_game_table_ui_ux.md`、`docs/requirements/09_ui_ux_animations.md`

---

## 1. 目的与范围

### 1.1 目的

- 定义**多套 UI 的切换设计**：用户可在不同主题、不同界面版本之间切换，并可在不同入口完成切换操作；切换结果可持久化并在多端一致。
- 为产品、设计与开发提供统一的「切换维度、入口、方式、反馈与存储」规格。

### 1.2 范围

- **包含**：切换维度（主题 / UI 版本 / 字体等）、切换入口与方式、切换反馈与生效时机、配置项与默认值、存储与优先级、设置页与快捷入口、API 与数据、前端实现要点。
- **不包含**：各套 UI 的具体视觉与交互细节（见 04、09）；多语言/国际化单独另规格。

### 1.3 术语

| 中文 | 说明 |
|------|------|
| **多 UI 切换** | 用户在多套界面风格/主题之间进行选择并即时生效的能力 |
| **主题** | 色彩模式：浅色、深色、跟随系统 |
| **UI 版本** | 一套完整的界面风格+布局+动效组合，如「默认」「简约」「经典」等 |
| **配置项** | 用户可调的单项，如主题、UI 版本、字体、动画、音效等 |

---

## 2. 切换维度设计

### 2.1 维度一览

用户可切换的维度如下；各维度相互独立，可组合生效（如「深色 + 简约 + 大字体」）。

| 维度 | 可选值 | 默认值 | 说明 |
|------|--------|--------|------|
| **主题（theme）** | light / dark / system | system | 浅色、深色、跟随系统外观 |
| **UI 版本（uiVersion）** | default / compact / classic（可扩展） | default | 界面风格与布局密度 |
| **字体大小（fontSize）** | small / medium / large | medium | 全局或牌桌字体档位 |
| **动画（animationEnabled）** | 开 / 关 | 开 | 发牌、下注、比牌等动效 |
| **音效（soundEnabled）** | 开 / 关 | 开 | 下注、弃牌、胜利等音效 |
| **减弱动效（reducedMotion）** | 开 / 关 | 关 | 无障碍友好，缩短或简化动画 |

### 2.2 主题（theme）

| 取值 | 说明 |
|------|------|
| **light** | 浅色主题 |
| **dark** | 深色主题 |
| **system** | 跟随系统（prefers-color-scheme），由前端解析为实际 light 或 dark |

### 2.3 UI 版本（uiVersion）

| 取值 | 定位 | 适用场景 |
|------|------|----------|
| **default** | 主版本，完整动效与视觉层次（如 09「数字丝绒」） | 默认推荐，桌面与高性能设备 |
| **compact** | 简约版，信息更密、动效可减弱 | 低性能设备、偏好简洁、小屏 |
| **classic** | 经典版，偏传统扑克室风格（可后续扩展） | 怀旧或固定偏好用户 |

- 版本与主题可任意组合，如 default+dark、compact+light。

### 2.4 配置项完整定义

| 配置项 | 类型 | 可选值/范围 | 默认值 |
|--------|------|-------------|--------|
| theme | enum | light / dark / system | system |
| uiVersion | string | default / compact / classic | default |
| fontSize | enum | small / medium / large | medium |
| animationEnabled | boolean | true / false | true |
| soundEnabled | boolean | true / false | true |
| reducedMotion | boolean | true / false | false |

- 后续可扩展：牌桌背景、卡背、座位数偏好等。

---

## 3. 切换入口与方式

### 3.1 主入口：设置页 / 个人中心

- **位置**：个人中心或全局设置中的「外观」「显示」或「UI 设置」。
- **内容**：集中展示上述所有维度——主题单选、UI 版本单选、字体档位、动画/音效/减弱动效开关。
- **交互**：选择或开关后**即时生效**，无需确认或刷新；若已登录，变更同时写入服务端（见第 6 节）。

### 3.2 快捷入口（可选）

- **主题快捷切换**：大厅或牌桌页提供图标（如太阳/月亮），点击在 light / dark / system 间轮换或弹出小菜单选择；适用于仅改主题、不改版本的场景。
- **UI 版本快捷切换**：同一位置或相邻位置提供「简约/完整」等切换，点击在 default / compact 等间切换；可与主题快捷并列或收在「更多」中。
- **行为**：快捷操作与设置页修改同一套配置，生效规则一致；若从牌桌页切换，当前牌桌立即应用新主题/版本。

### 3.3 首次访问引导（可选）

- 首次进入可弹出轻量引导：「选择主题」或「选择界面风格」，选项为 2.1 中的主要维度；选择后写入本地并关闭引导，不再自动弹出。

### 3.4 URL 参数（仅当次生效）

- 支持通过 URL 覆盖配置，**仅当次访问生效，不写入本地与服务端**，便于分享、测试、运营链接。
- 建议参数：`theme`、`ui`（或 `uiVersion`）、`fontSize`、`animation`、`sound`。  
  示例：`/lobby?theme=dark&ui=compact`

---

## 4. 切换反馈与生效时机

### 4.1 即时生效

- 用户在任何入口修改任意维度后，**无需刷新页面**即生效：
  - **主题 / UI 版本 / 字体**：通过根节点或容器上的 `data-theme`、`data-ui-version`、`data-font-size` 或对应 class 切换样式与布局。
  - **动画 / 音效**：动画在「下一次触发的动效」时生效；音效在「下一次播放」时根据 soundEnabled 决定是否播放。

### 4.2 过渡与反馈

- **主题 / 版本切换**：建议增加短暂过渡（如 200–300ms 颜色/透明度过渡），避免生硬闪烁；可选在切换时给出轻提示（如 Toast「已切换为深色」）。
- **无障碍**：当 reducedMotion 为开时，过渡时长应缩短或取消，符合「减弱动效」预期。

### 4.3 失败与降级

- 若服务端保存失败（已登录场景），前端可提示「设置已在本机生效，但同步失败，请稍后重试」；本地已更新，下次成功时再同步。
- 若某 UI 版本服务端未开放（见 6.3），前端不展示该选项或置灰并提示「当前环境不可用」。

---

## 5. 配置的存储与优先级

### 5.1 存储位置

- **本地**：`localStorage`，键名如 `dzpoker_ui_config`，值为上述配置项的 JSON；未登录或仅本地偏好时使用。
- **服务端**：已登录用户的配置持久化在用户设置表或 users 表扩展字段；登录后拉取并覆盖本地，保存时回写服务端，实现多端同步。

### 5.2 生效优先级（从高到低）

1. **URL 参数**：仅当次生效，不写入任何存储。
2. **服务端用户配置**：已登录且存在保存过的配置时使用。
3. **本地存储**：未登录或服务端无配置时使用。
4. **默认值**：以上皆无时使用 2.4 中的默认值。

### 5.3 登录与同步

- **登录后**：若服务端有配置，用服务端覆盖本地并写入 localStorage；若服务端无、本地有，可提示「是否将当前设置同步到账号」并上传。
- **修改后**：已登录时除更新本地与界面外，提交到服务端；未登录仅更新本地。

---

## 6. API 定义（服务端存储时）

### 6.1 获取当前用户 UI 配置

- **Endpoint:** `GET /api/users/me/ui-config`
- **Headers:** `Authorization: Bearer <token>`
- **Response:**  
  `{ "theme": "dark", "uiVersion": "compact", "fontSize": "medium", "animationEnabled": true, "soundEnabled": false, "reducedMotion": false }`  
  若用户从未保存，可返回 200 + 默认值，或 204 表示使用默认/前端本地。

### 6.2 保存 UI 配置

- **Endpoint:** `PUT /api/users/me/ui-config`
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:** 同上 JSON，支持只传需更新字段（部分更新）。
- **Response:** 200 + 当前完整配置，或 204。
- **校验**：theme / uiVersion / fontSize 须在允许枚举内；布尔项须为 boolean。

### 6.3 可用选项配置（可选）

- 运营控制当前环境允许的主题与 UI 版本时使用。
- **Endpoint:** `GET /api/config/ui-options`（可匿名）
- **Response:** `{ "uiVersions": ["default", "compact"], "themes": ["light", "dark", "system"] }`
- 前端仅展示并允许选择返回的选项，避免无效配置。

---

## 7. 前端实现要点（供开发参照）

### 7.1 样式与 DOM 约定

- **主题**：在 `<html>` 或根容器设置 `data-theme="light"|"dark"` 或 class；CSS 用 `[data-theme=dark]` 或 `.theme-dark` 定义深色变量与样式；system 通过 prefers-color-scheme 或 JS 解析为 light/dark 后写入。
- **UI 版本**：根容器 `data-ui-version="default"|"compact"` 或 class `.ui-compact`；不同版本通过不同样式文件或同一文件内命名空间覆盖。
- **字体**：`data-font-size="medium"` 或 class 控制 `--font-size-base` 等 CSS 变量。

### 7.2 动画与音效

- **animationEnabled / reducedMotion**：根或牌桌容器增加 class（如 `.no-animation`、`.reduced-motion`），动画选择器内对该 class 禁用或缩短动画。
- **soundEnabled**：在播放音效前检查配置，为 false 则不播放。

### 7.3 URL 参数

- 页面加载时读取 query 中的 theme、ui、fontSize、animation、sound，应用后不写入 localStorage 与服务端。

---

## 8. 数据与兼容

### 8.1 数据库（可选）

- **方案 A**：users 表增加 `ui_config_json`（TEXT/JSON）。
- **方案 B**：独立 user_settings 表，如 user_id、key、value_json、updated_at，键为 `ui_config`。
- 详见 `docs/requirements/06_database_schema.md` 中相关说明。

### 8.2 默认值与兼容

- 未配置或旧版本缺失新配置项时，按 2.4 默认值补齐；读取后对缺失键补默认，保证向后兼容。

---

## 9. 需求检查清单（实现与验收）

- [ ] 主题 light / dark / system 可切换且即时生效
- [ ] UI 版本 default / compact（及可选 classic）可切换且即时生效
- [ ] 字体 small / medium / large 可切换且即时生效
- [ ] 动画、音效、减弱动效开关生效符合 4.1
- [ ] 设置页集中展示所有维度并可修改
- [ ] 可选：大厅/牌桌页主题或版本快捷切换
- [ ] 可选：首次访问主题/风格引导
- [ ] URL 参数可覆盖配置且仅当次生效、不写入存储
- [ ] 已登录用户配置可保存至服务端并多端同步
- [ ] 未登录用户配置存 localStorage，登录后可按 5.3 同步
- [ ] 可选：GET /api/config/ui-options 控制可用选项

---

**文档版本**：1.1  
**最后更新**：2026-03-12

# 13 - 约局模式（Scheduled Game）

**文档类型**：产品需求规格  
**参考**：WePoker / HHPoker 等平台的约局、私局、好友组局  
**关联**：`docs/requirements/02_game_lobby.md`、`docs/requirements/11_club_design.md`、`docs/requirements/06_database_schema.md`

---

## 1. 目的与范围

### 1.1 目的

- 支持用户**创建预约牌局（约局）**：设定开赛时间、盲注、人数、买入等，通过**邀请链接或好友/俱乐部**召集玩家，到点或满人后**自动开桌**，形成「定时私局」体验。
- 与「大厅即时桌」的区别：约局强调**预约、邀请、定时开始**；大厅为随时加入空位。

### 1.2 范围

- **包含**：约局创建/编辑/取消、开赛时间与规则（定时开赛/满人即开）、报名/占位、邀请与分享、与俱乐部结合（可选）、自动开桌与状态机。
- **不包含**：约局内的具体打牌规则（复用标准德州与现金桌逻辑）；结算与记账方式若涉及线下或独立货币可另开规格。

### 1.3 术语

| 中文 | 英文 | 说明 |
|------|------|------|
| 约局 | Scheduled Game | 一场预约好的牌局，有开赛时间与参与名单 |
| 局主/创建者 | Host / Creator | 创建该约局的用户，可编辑、取消、邀请 |
| 报名/占位 | Register / Reserve | 用户确认参与该约局，计入参与名单 |
| 定时开赛 | Start at scheduled time | 到设定时间自动开桌 |
| 满人即开 | Start when full | 报名人数达到上限即开桌（可忽略原定时间） |

---

## 2. 约局模型

### 2.1 约局属性

| 属性 | 类型 | 说明 |
|------|------|------|
| scheduledGameId | string | 唯一标识 |
| title | string | 局名称（如「周六晚 9 点局」「老友 6 人局」） |
| hostUserId | string | 局主 user_id |
| clubId | string, 可选 | 若属于某俱乐部，则仅该俱乐部成员可见/可报名；为空则视为「私局」 |
| startAt | datetime | 计划开赛时间 |
| startRule | enum | 定时开赛 / 满人即开（见 2.2） |
| minPlayers | int | 最少开赛人数（如 2）；不足则流局/取消 |
| maxPlayers | int | 最大人数（如 6 或 9），即满员人数 |
| blinds | string 或 object | 盲注，如 "10/20" 或 { smallBlind, bigBlind }；可为固定盲注或起始级别 |
| buyInMin / buyInMax | int, 可选 | 带入上下限（游戏币）；可选，不设则按平台默认 |
| initialChips | int, 可选 | 每人起始筹码；不设则按平台默认或由盲注推导 |
| password | string, 可选 | 加入密码；为空则无需密码 |
| inviteCode | string | 邀请码（唯一），用于生成邀请链接 |
| status | enum | 见 2.3 |
| tableId | string, 可选 | 开赛后创建的牌桌 ID；未开赛为空 |
| createdAt / updatedAt | datetime | 创建/更新时间 |

### 2.2 开赛规则（startRule）

- **scheduled**（定时开赛）：到 `startAt` 时，若已报名人数 ≥ minPlayers，则自动创建牌桌并拉所有已报名用户进入；若不足则流局（可配置为顺延或取消）。
- **full**（满人即开）：一旦报名人数 = maxPlayers，立即开桌（忽略 startAt）；若在 startAt 之前就满人，则提前开赛。
- **scheduled_or_full**（定时或满人即开）：满足「到达 startAt」或「报名人数 = maxPlayers」任一条件即开赛；推荐默认。

### 2.3 约局状态

| 状态 | 说明 |
|------|------|
| **Scheduled** | 预约中；可报名、可取消报名、局主可编辑/取消约局 |
| **ReadyToStart** | 人数已满或临近开赛（如 5 分钟内）；不可再报名，等待开赛 |
| **Starting** | 系统正在创建牌桌、分配座位、拉人进入（短暂状态） |
| **Running** | 牌局进行中；对应 tableId 已有，按现金桌逻辑打牌 |
| **Ended** | 牌局已结束（如所有人离桌或局主结束） |
| **Cancelled** | 约局已取消（局主取消或流局） |

### 2.4 参与名单

- 用户**报名**后进入参与名单；名单按报名顺序或可选「局主指定座位顺序」。
- **取消报名**：在状态为 Scheduled 且未满员时可取消；若已 ReadyToStart，是否允许取消可配置（通常不允许）。
- **踢出**：局主可从参与名单中移出某用户（在 Scheduled 状态下），被移出用户不可再报名本局（可配置为允许再次报名）。

---

## 3. 流程与规则

### 3.1 创建约局

- **谁可创建**：已登录用户；若绑定俱乐部则可在俱乐部内创建（仅俱乐部成员可见）。
- **必填**：title、startAt、minPlayers、maxPlayers、blinds；**startRule** 选填，默认 scheduled_or_full。
- **选填**：clubId（挂到某俱乐部）、buyInMin/Max、initialChips、password、备注说明。
- **邀请码**：系统自动生成唯一 inviteCode；用于生成邀请链接 `{baseUrl}/scheduled/join?code={inviteCode}` 或 `{baseUrl}/scheduled/{scheduledGameId}?invite={inviteCode}`。
- **局主**：自动加入参与名单，占第 1 席。

### 3.2 邀请与分享

- **分享链接**：局主（及可选：已报名用户）可分享邀请链接；任何人打开链接后，若未登录则先登录，再进入「约局详情页」并可见「报名」按钮（若未报名且未满员）。
- **邀请好友**：若产品支持好友关系，可「邀请好友」向指定用户发送站内通知或外链，好友点击后跳转约局详情并报名。
- **俱乐部内可见**：若约局带 clubId，则在「俱乐部大厅」或「俱乐部约局列表」中展示，仅俱乐部成员可见并可报名；局主可为俱乐部 Admin/Owner 或任意成员（可配置）。

### 3.3 报名与准入

- **报名**：用户点击报名后，校验：未满员、未在名单中、余额满足 buyIn（若设）、密码正确（若设）、若在俱乐部内则须为俱乐部成员；通过后加入参与名单。
- **满员**：报名人数达到 maxPlayers 时，若 startRule 含 full，则进入 ReadyToStart 并触发「即将开赛」；若为纯 scheduled 则仅标记满员，仍等到 startAt 再开赛。
- **密码**：若约局设了 password，报名时需传 password，服务端校验通过才加入名单。

### 3.4 开赛

- **触发**：由定时任务或事件驱动检查「当前时间 ≥ startAt」或「报名人数 = maxPlayers」（按 startRule）；满足则执行开赛逻辑。
- **开赛逻辑**：  
  1. 状态置为 Starting。  
  2. 按当前参与名单创建一张**现金桌**（或锦标赛桌，本规格默认现金桌）：盲注、人数上限、买入等取自约局配置。  
  3. 将名单内用户依次分配座位（顺序可随机或按报名顺序），并执行「加入牌桌」逻辑（扣买入、发筹码）。  
  4. 若某用户此时余额不足或掉线，可跳过该用户并通知局主；若剩余人数 < minPlayers，则流局并退款。  
  5. 状态置为 Running，写入 tableId；推送所有参与者「约局已开桌」，跳转牌桌页。
- **流局**：到 startAt 时报名人数 < minPlayers，或开赛时有效人数 < minPlayers：状态置为 Cancelled，可选退款（若已预扣则退），并通知已报名用户。

### 3.5 取消约局

- **局主取消**：在状态为 Scheduled 或 ReadyToStart 时可取消；状态置为 Cancelled，通知已报名用户，不扣费（若未预扣）。
- **系统取消/流局**：见 3.4。

### 3.6 进行中与结束

- 约局进入 Running 后，玩法与**普通现金桌**完全一致；牌桌结束后（所有人离桌或局主结束桌），约局状态置为 Ended，tableId 保留用于历史查看。
- **局主提前结束牌桌**：若产品允许，局主可在 Running 状态下请求「结束本局牌桌」，则牌桌按正常结束流程收尾，约局置为 Ended。

---

## 4. API 定义概要

### 4.1 约局 CRUD

- `POST /api/scheduled-games` — 创建约局（Body: title, startAt, startRule, minPlayers, maxPlayers, blinds, clubId?, buyInMin?, buyInMax?, initialChips?, password?, 等）
- `GET /api/scheduled-games/{scheduledGameId}` — 约局详情（含参与名单、状态、开赛倒计时）
- `PUT /api/scheduled-games/{scheduledGameId}` — 编辑约局（仅局主，且 status = Scheduled）
- `DELETE /api/scheduled-games/{scheduledGameId}` — 取消约局（仅局主）
- `GET /api/scheduled-games` — 列表；Query: `clubId=`（某俱乐部下的约局）、`status=`、`mine=true`（我创建的或我报名的）、分页

### 4.2 报名与参与

- `POST /api/scheduled-games/{scheduledGameId}/register` — 报名（Body 可选: password；若在俱乐部内则校验成员）
- `POST /api/scheduled-games/{scheduledGameId}/unregister` — 取消报名（仅 Scheduled 且未满员）
- `GET /api/scheduled-games/{scheduledGameId}/players` — 参与名单（含昵称、头像、报名顺序）
- `POST /api/scheduled-games/{scheduledGameId}/players/{userId}/kick` — 踢出（仅局主，仅 Scheduled）

### 4.3 邀请

- `GET /api/scheduled-games/{scheduledGameId}/invite-link` — 获取邀请链接（局主或已报名用户）；返回 URL + inviteCode
- 通过链接加入：前端解析 inviteCode 或 scheduledGameId，跳转约局详情页并预填邀请码；用户点击报名即调用 register。

### 4.4 WebSocket 事件

- **Server → Client**
  - `scheduled:updated` — 约局信息变更（参与名单、状态、开赛时间调整）
  - `scheduled:starting` — 即将开赛（倒计时 1 分钟或满人即开时）
  - `scheduled:table_created` — 已开桌，Payload: tableId, seatIndex, 跳转 URL 或 room 名
  - `scheduled:cancelled` — 约局已取消

- **Client → Server**
  - 无额外；报名/取消报名走 REST。

---

## 5. 与俱乐部的关系

- **约局可挂靠俱乐部**：创建时选填 clubId；则该约局仅在该俱乐部的「约局列表」中展示，且仅俱乐部成员可报名。
- **不挂靠**：clubId 为空，视为**私局**；仅能通过邀请链接或「我参与的约局」列表进入，适合好友小范围约局。
- 俱乐部内约局列表：`GET /api/clubs/{clubId}/scheduled-games`，返回该俱乐部下未结束的约局；创建入口在俱乐部页「创建约局」。

---

## 6. 数据库扩展（参考 06）

- **scheduled_games** 表：id, title, host_user_id, club_id(NULLable), start_at, start_rule, min_players, max_players, blinds_json, buy_in_min, buy_in_max, initial_chips, password_hash(NULLable), invite_code(unique), status, table_id(NULLable), created_at, updated_at。
- **scheduled_game_players** 表：scheduled_game_id, user_id, registered_at, seat_order(报名顺序), 唯一(scheduled_game_id, user_id)。
- 开赛后产生的牌桌在现有 **tables** 表，通过 table_id 关联；可选在 tables 表增加 scheduled_game_id 可空字段，便于查询「某约局对应的牌桌」。

具体建表见 `docs/requirements/06_database_schema.md` 中「约局」相关章节。

---

## 7. 产品要点小结（参考 WePoker / HHPoker）

- **创建即分享**：创建完成后展示邀请链接与邀请码，方便复制/分享到微信、群聊。
- **倒计时与提醒**：详情页展示「距开赛 X 分钟」；可选推送/站内信「您参与的约局即将开始」。
- **满人即开**：支持「人齐就开」，减少等待，适合熟人局。
- **俱乐部内约局**：俱乐部成员在俱乐部页可见「本周约局」或「发起约局」，增强俱乐部内活跃度。
- **流局与退款**：人数不足时明确流局并退款（若曾预扣），避免纠纷。

---

**文档版本**：1.0  
**最后更新**：2026-03-12

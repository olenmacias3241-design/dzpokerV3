# 11 - 俱乐部设计

**文档类型**：产品需求规格  
**关联**：`docs/requirements/02_game_lobby.md`（大厅与牌桌）、`docs/requirements/06_database_schema.md`（表结构）

---

## 1. 目的与范围

### 1.1 目的

- 支持用户创建**俱乐部（Club）**，邀请成员在俱乐部内开设**专属牌桌**或使用**俱乐部房间**，形成私密、可管理的扑克小圈子。
- 俱乐部具备**角色与权限**、**成员管理**、**俱乐部牌桌**与可选**俱乐部数据统计**。

### 1.2 范围

- **包含**：俱乐部创建/编辑/解散、成员邀请/加入/踢出/退出、角色（创建者/管理员/成员）、俱乐部牌桌创建与准入、俱乐部大厅视图。
- **不包含**：俱乐部独立货币或与链上资产直接结算（若需可另开规格）；锦标赛与俱乐部结合可后续扩展。

### 1.3 与大厅的关系

- **公共大厅**：所有用户可见的牌桌列表（现有 02 规格）。
- **俱乐部大厅**：用户加入的俱乐部列表；进入某俱乐部后，仅展示该俱乐部的牌桌（及成员）；俱乐部牌桌仅对**本俱乐部成员**可见/可加入（可配置为需管理员审批）。

---

## 2. 俱乐部模型

### 2.1 俱乐部属性

| 属性 | 类型 | 说明 |
|------|------|------|
| clubId | string | 唯一标识 |
| name | string | 俱乐部名称（长度限制，如 2–30 字） |
| description | string | 简介（可选，长度限制） |
| avatarUrl | string | 俱乐部头像 URL |
| creatorUserId | string | 创建者 user_id |
| visibility | enum | 公开可见 / 仅邀请可见（是否可被搜索） |
| joinPolicy | enum | 自由加入 / 需审批 / 仅邀请（邀请码/链接） |
| inviteCode | string | 邀请码（可选，唯一，用于链接或输入加入） |
| maxMembers | int | 最大成员数（可选，默认如 100） |
| createdAt / updatedAt | timestamp | 创建/更新时间 |

### 2.2 成员与角色

| 角色 | 英文 | 权限 |
|------|------|------|
| 创建者 | Owner | 同 Admin，且可转让俱乐部、解散俱乐部、删除管理员 |
| 管理员 | Admin | 审批加入、踢出成员（不含 Owner）、创建/关闭俱乐部牌桌、编辑俱乐部信息（名称/简介/头像/加入策略） |
| 成员 | Member | 查看俱乐部、加入俱乐部牌桌、邀请他人（若策略允许）、退出俱乐部 |

- **单人多角色**：同一用户在俱乐部内仅一个角色；创建者同时视为 Owner，可设多名 Admin，其余为 Member。
- **转让**：Owner 可将 Owner 转让给某 Admin，转让后原 Owner 变为 Admin 或 Member（可配置）。

### 2.3 俱乐部牌桌

- **俱乐部牌桌**：仅属于某俱乐部（clubId）；仅该俱乐部成员可见并可加入（或需管理员审批后加入，视配置）。
- **与公共牌桌区别**：公共牌桌在大厅对所有用户开放；俱乐部牌桌只在「俱乐部内大厅」展示，且准入受俱乐部成员身份控制。
- **创建**：仅俱乐部 Owner/Admin 可创建「俱乐部牌桌」；创建时指定盲注、人数上限、可选密码等，与现有牌桌参数兼容。
- **牌桌属性**：除现有 table 字段外，增加 `clubId`；若 `clubId` 非空则为俱乐部桌。

---

## 3. 流程与规则

### 3.1 创建俱乐部

- 用户（已登录）可创建俱乐部；创建者自动成为 Owner。
- 创建时必填：名称；可选：简介、头像、可见性、加入策略、最大成员数。
- 若选择「仅邀请」或「需审批」，系统生成唯一 **inviteCode**（及邀请链接）；可后续重新生成使旧链接失效。

### 3.2 加入俱乐部

- **自由加入**：用户通过搜索/列表找到俱乐部，点击加入即可成为 Member。
- **需审批**：用户提交加入申请，Owner/Admin 审批通过后成为 Member。
- **仅邀请**：用户通过邀请链接或输入 inviteCode，验证通过后成为 Member（或进入待审批列表，由管理员通过）。

### 3.3 邀请与邀请码

- Owner/Admin 可生成或**重新生成**邀请码；可选：设置有效期、使用次数上限。
- 邀请链接格式建议：`{baseUrl}/club/join?code={inviteCode}` 或 `{baseUrl}/club/{clubId}?invite={inviteCode}`。
- 成员（若策略允许）可分享邀请链接/邀请码，但不能修改俱乐部设置或踢人。

### 3.4 退出与踢出

- **退出**：成员可主动退出俱乐部；退出后不再能进入该俱乐部牌桌，不再计入成员数。
- **踢出**：Owner/Admin 可将 Member 踢出；被踢用户不可再通过原邀请码加入（可配置为一段时间内禁止同一用户再次加入）。

### 3.5 解散俱乐部

- 仅 Owner 可解散俱乐部。
- 解散前需处理：进行中的俱乐部牌桌（结束或迁移到公共大厅的策略需明确）；成员通知。
- 解散后：俱乐部数据可保留为「已解散」状态供审计，或软删除；俱乐部牌桌关闭。

---

## 4. API 定义概要

### 4.1 俱乐部 CRUD

- `POST /api/clubs` — 创建俱乐部（Body: name, description, avatarUrl, visibility, joinPolicy, maxMembers）
- `GET /api/clubs/{clubId}` — 俱乐部详情（含成员数、当前牌桌数；成员可见更多）
- `PUT /api/clubs/{clubId}` — 更新俱乐部信息（Owner/Admin）
- `DELETE /api/clubs/{clubId}` — 解散俱乐部（Owner）
- `GET /api/clubs` — 我加入的俱乐部列表；可选 `?search=` 搜索公开俱乐部
- `GET /api/clubs/search?q=` — 搜索俱乐部（仅 visibility=公开 的俱乐部）

### 4.2 成员与邀请

- `POST /api/clubs/{clubId}/join` — 加入俱乐部（Body 可选：inviteCode；若需审批则进入待审批列表）
- `POST /api/clubs/{clubId}/leave` — 退出俱乐部
- `POST /api/clubs/{clubId}/invite` — 生成/重新生成邀请码（Owner/Admin）；Body 可选：expiresIn, useLimit
- `GET /api/clubs/{clubId}/members` — 成员列表（分页、角色筛选）
- `POST /api/clubs/{clubId}/members/{userId}/kick` — 踢出成员（Owner/Admin）
- `POST /api/clubs/{clubId}/members/{userId}/role` — 设置角色（Owner 可设 Admin）；Body: role
- `GET /api/clubs/{clubId}/join-requests` — 待审批列表（Owner/Admin）
- `POST /api/clubs/{clubId}/join-requests/{requestId}/approve|reject` — 审批加入（Owner/Admin）

### 4.3 俱乐部牌桌

- `POST /api/clubs/{clubId}/tables` — 创建俱乐部牌桌（Owner/Admin）；Body 同大厅创建牌桌参数 + 可选 password
- `GET /api/clubs/{clubId}/tables` — 该俱乐部下的牌桌列表（仅成员可查）
- `DELETE /api/clubs/{clubId}/tables/{tableId}` — 关闭俱乐部牌桌（Owner/Admin）
- 加入俱乐部牌桌：复用大厅的加入牌桌逻辑，但服务端校验「用户须为该俱乐部成员」；若牌桌设了密码，需校验密码。

### 4.4 WebSocket 与大厅

- 进入「俱乐部大厅」时，可订阅 `club:{clubId}` 的 room，接收该俱乐部牌桌列表变更、成员变更（可选）。
- 俱乐部牌桌的 `game:state_update` 等与公共牌桌一致，仅推送对象限定为已加入该桌的玩家（及俱乐部内可见性由服务端控制）。

---

## 5. 数据统计（可选）

- **俱乐部维度**：总局数、总手数、活跃成员数、俱乐部牌桌数。
- **成员在俱乐部内**：该成员在本俱乐部牌桌上的局数、胜率、总盈亏（若平台有游戏币统计）。
- 展示位置：俱乐部主页、成员列表侧栏等；具体指标与埋点可后续细化。

---

## 6. 数据库扩展（参考 06）

- **clubs** 表：club_id, name, description, avatar_url, creator_user_id, visibility, join_policy, invite_code, max_members, created_at, updated_at。
- **club_members** 表：club_id, user_id, role (owner/admin/member), joined_at；唯一 (club_id, user_id)。
- **club_join_requests** 表：club_id, user_id, status (pending/approved/rejected), created_at, resolved_at, resolved_by。
- **tables** 表增加字段：club_id（可空）；club_id 非空即俱乐部牌桌，准入校验时查 club_members。

具体建表语句见 `docs/requirements/06_database_schema.md` 中「俱乐部」相关章节。

---

**文档版本**：1.0  
**最后更新**：2026-03-12

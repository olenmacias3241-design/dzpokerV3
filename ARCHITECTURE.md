# 架构说明：服务端与客户端分离

## 职责划分

### 服务端（监管所有牌桌）

- **单一数据源**：维护全部牌桌状态（`tables.TABLES`）、用户会话、对局逻辑。
- **能力**：
  - 牌桌列表、创建牌桌、加入/入座、开局、发牌、比牌、下注等全部由服务端处理。
  - HTTP API：登录、大厅、牌桌状态、动作、发下一街、表情等。
  - WebSocket：按桌号分 room，向**已加入该桌**的客户端推送状态（`game:state_update` / `table:state`）。
- **部署**：独立进程（如 `python app.py`），可单独部署到一台机器或容器，只暴露 API 与 WS 地址。

### 客户端（仅监控单局牌桌）

- **不持有全局状态**：不维护牌桌列表或其它桌的状态，只关心「当前这一桌」。
- **能力**：
  - 通过 URL 参数 `table` + `token` 确定当前桌与身份。
  - 仅与当前桌通信：拉取该桌状态（GET）、发送动作（POST 或 WS）、通过 WS 接收该桌的状态推送。
  - 同一时刻只加入一个 WebSocket room（`join_table` 时传入一个 `table_id`），只收当前桌的 `game:state_update`。
- **部署**：可同源（与后端同一域名），也可前后端分离：静态资源放在 CDN 或另一域名，通过配置指向服务端 API/WS 地址。

## 前后端分离部署

1. **服务端**：部署到 `https://api.example.com`（或 `http://IP:5001`），保证 CORS 允许客户端域名（当前为 `*`）。
2. **客户端**：在加载页面脚本**之前**设置服务端地址，例如在 `index.html` 中：
   ```html
   <script>
   window.DZPOKER_API_BASE = "https://api.example.com";
   window.DZPOKER_WS_URL   = "https://api.example.com";  // Socket.IO 连此地址
   </script>
   <script src="/static/config.js"></script>
   <!-- 其余 script -->
   ```
3. 所有 `fetch` 与 `io()` 会走上述地址；未设置时默认同源（空字符串）。

## 数据流简述

- **大厅**：客户端请求 `GET /api/lobby/tables` 得到牌桌列表（服务端汇总所有桌）；创建/加入时调用对应 API，再由服务端更新 TABLES。
- **牌桌页**：客户端只请求当前桌 `GET /api/tables/<id>` 与当前桌动作；WebSocket 只 `join_table` 当前桌，只收该桌的状态推送，实现「只监控单局牌桌」。

## 协作流程（步骤）

1. **登录**：客户端 POST `/api/login` 或 `/api/auth/login`，服务端返回 token；客户端存 token，后续请求都带 token。
2. **大厅**：客户端 GET `/api/lobby/tables` 得牌桌列表；创建桌：POST `/api/lobby/tables` 得 tableId → POST `/api/tables/<id>/sit` 入座 → 跳转牌桌页；加入桌：GET 该桌状态找空位 → POST sit → 跳转。
3. **牌桌页**：从 URL 取 table、token，GET `/api/tables/<id>?token=...` 拿当前桌状态；只渲染当前桌。
4. **WebSocket**：连接后 emit `join_table({ table_id, token })`（仅当前桌）；服务端 join_room(table_id)，只向该 room 推送 `game:state_update`；客户端只收当前桌推送并刷新 UI。
5. **对局**：开局/下注/发牌/表情由客户端发事件或 POST，服务端执行并广播该桌 state；客户端不维护权威状态，只根据推送更新界面。

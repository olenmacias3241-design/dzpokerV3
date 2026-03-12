# 02 - 游戏大厅规格

## 3.1 获取牌桌列表
- **Endpoint:** `GET /api/lobby/tables`
- **Query Params:**
  - `blinds` (e.g., "small", "medium", "high")
  - `players` (e.g., 6, 9)
- **Response:** Array of table objects.
- **Table Object Structure:**
  - `tableId`
  - `tableName`
  - `blinds` (e.g., "10/20")
  - `playerCount`
  - `maxPlayers`
  - `avgPotSize`
  - `status` ("waiting", "playing")

## 3.2 快速开始
- **Endpoint:** `POST /api/lobby/quick-start`
- **Functionality:** 服务器根据玩家的 `coinsBalance` 自动匹配一个符合带入要求且有空位的牌桌。
- **Success Response:**
  - `tableId`
  - `seatNumber`
- **Error Handling:**
  - 没有合适的牌桌
  - 玩家余额不足

## 3.3 加入特定牌桌
- **WebSocket Event (Client -> Server):** `lobby:join_table`
- **Payload:**
  - `tableId`
  - `seatNumber` (optional, if user clicks a specific seat)
  - `buyInAmount`
- **Server Response (WebSocket):**
  - Success: `game:joined_table` (sends full game state)
  - Error: `error:join_failed` (e.g., "Table is full", "Buy-in invalid")

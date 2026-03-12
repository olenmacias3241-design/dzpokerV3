# 05 - API 定义 (WebSocket)

前后端主要通过 WebSocket 进行实时通信。以下是核心事件定义。

## Server -> Client (服务器广播或私信)

- `game:state_update`
  - **触发**: 牌局状态变更时 (新一轮开始、玩家行动后)。
  - **Payload**: 完整的当前牌桌状态，包括：
    - `tableId`, `handId`
    - `gameState` (e.g., "Flop")
    - `pot`, `sidePots`
    - `communityCards`
    - `seats`: Array of player objects (seat, username, chips, status, currentBet)
    - `activePlayerSeat`: 当前行动者座位号
    - `dealerSeat`
  - **Note**: 玩家的底牌 (`holeCards`) 只会通过私信发给对应玩家。

- `game:player_action`
  - **触发**: 一位玩家完成行动后。
  - **Payload**:
    - `seat`: 行动玩家座位号
    - `action`: "fold", "check", "call", "bet", "raise", "all_in"
    - `amount`: 下注/加注的金额

- `game:showdown_result`
  - **触发**: 比牌阶段。
  - **Payload**:
    - `winners`: Array of winner objects (`seat`, `handDescription`, `amountWon`)
    - `potDistribution`: 详细的底池分配日志。

- `private:deal_hole_cards`
  - **触发**: 牌局开始发底牌时。
  - **Payload**:
    - `cards`: [`rank suit`, `rank suit`] (e.g., ["As", "Kd"])
  - **Note**: 此事件只发送给该玩家自己。

- `game:deal_phase`
  - **触发**: 每街发牌时（底牌、翻牌、转牌、河牌），供前端做发牌动画。
  - **Payload**:
    - `phase`: "hole_cards" | "flop" | "turn" | "river"
    - `cards`: 本街新发的牌数组，每项 `{ suit, rank }`（仅 flop/turn/river 有；hole_cards 时前端用 state 中各玩家 hand 做动画）
  - **Note**: 前端收到后可按 phase 播放对应动画（2 张手牌、3 张翻牌、1 张转牌、1 张河牌）。实现建议：先监听 `game:deal_phase` 播放发牌动画（如每张牌 0.2–0.4s 依次出现），再根据随后收到的 `game:state_update` 或当前 state 更新牌面 DOM。

## Client -> Server (玩家操作)

- `game:action`
  - **触发**: 玩家点击行动按钮。
  - **Payload**:
    - `action`: "fold", "check", "call", "bet", "raise", "all_in"
    - `amount`: (for bet/raise)

- `game:leave_table`
  - **触发**: 玩家选择离开桌子。

- `game:chat_message`
  - **触发**: 玩家发送聊天信息。
  - **Payload**:
    - `message`: (string)

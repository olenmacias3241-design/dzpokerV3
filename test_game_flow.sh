#!/bin/bash
# dzpokerV3 完整游戏流程测试（带日志）

set -e

API_BASE="http://127.0.0.1:5002"

echo "=========================================="
echo "dzpokerV3 游戏流程测试"
echo "=========================================="
echo ""

# 1. 创建牌桌
echo "1. 创建牌桌..."
TABLE_RESPONSE=$(curl -s -X POST "$API_BASE/api/lobby/tables" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试桌","blinds":"10/20","max_players":6}')

TABLE_ID=$(echo $TABLE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['tableId'])")
echo "   ✅ 牌桌创建成功，ID: $TABLE_ID"
echo ""

# 2. 玩家登录
echo "2. 玩家登录..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/api/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"测试玩家"}')

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")
USER_ID=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['userId'])")
echo "   ✅ 登录成功，Token: ${TOKEN:0:20}..."
echo "   用户ID: $USER_ID"
echo ""

# 3. 入座
echo "3. 玩家入座（座位0）..."
curl -s -X POST "$API_BASE/api/tables/$TABLE_ID/sit" \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"$TOKEN\",\"seat\":0}" > /dev/null
echo "   ✅ 入座成功"
echo "   ⏳ 等待机器人填充（2秒）..."
sleep 2
echo ""

# 4. 等待机器人行动
echo "4. 等待机器人自动行动（5秒）..."
sleep 5
echo ""

# 5. 查看当前状态
echo "5. 查看当前游戏状态..."
STATE=$(curl -s "$API_BASE/api/tables/$TABLE_ID?token=$TOKEN")
STAGE=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('stage', 'N/A'))" 2>/dev/null || echo "N/A")
POT=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('pot', 0))" 2>/dev/null || echo "0")
CURRENT=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('current_player_id', 'N/A'))" 2>/dev/null || echo "N/A")
ATC=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('amount_to_call', 0))" 2>/dev/null || echo "0")

echo "   阶段: $STAGE"
echo "   底池: $POT"
echo "   需跟注: $ATC"
echo "   当前行动者: $CURRENT"
echo ""

# 6. 玩家行动（跟注）
if [ "$CURRENT" = "$USER_ID" ]; then
    echo "6. 玩家跟注..."
    ACTION_RESPONSE=$(curl -s -X POST "$API_BASE/api/tables/$TABLE_ID/action" \
      -H "Content-Type: application/json" \
      -d "{\"token\":\"$TOKEN\",\"action\":\"call\"}")
    
    NEW_STAGE=$(echo $ACTION_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('stage', 'N/A'))" 2>/dev/null || echo "N/A")
    NEW_POT=$(echo $ACTION_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('pot', 0))" 2>/dev/null || echo "0")
    
    echo "   ✅ 跟注成功"
    echo "   新阶段: $NEW_STAGE"
    echo "   新底池: $NEW_POT"
    echo ""
else
    echo "6. 当前不是玩家回合，跳过"
    echo ""
fi

# 7. 等待机器人继续行动
echo "7. 等待机器人继续行动（5秒）..."
sleep 5
echo ""

# 8. 再次查看状态
echo "8. 查看最新游戏状态..."
STATE=$(curl -s "$API_BASE/api/tables/$TABLE_ID?token=$TOKEN")
STAGE=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('stage', 'N/A'))" 2>/dev/null || echo "N/A")
POT=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('pot', 0))" 2>/dev/null || echo "0")
CURRENT=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('current_player_id', 'N/A'))" 2>/dev/null || echo "N/A")

echo "   阶段: $STAGE"
echo "   底池: $POT"
echo "   当前行动者: $CURRENT"
echo ""

# 9. 继续玩几轮
echo "9. 继续游戏流程（自动跟注3次）..."
for i in {1..3}; do
    sleep 3
    STATE=$(curl -s "$API_BASE/api/tables/$TABLE_ID?token=$TOKEN")
    CURRENT=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('current_player_id', 'N/A'))" 2>/dev/null || echo "N/A")
    STAGE=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('stage', 'N/A'))" 2>/dev/null || echo "N/A")
    
    if [ "$CURRENT" = "$USER_ID" ] && [ "$STAGE" != "ENDED" ]; then
        echo "   第 $i 次行动: 跟注"
        curl -s -X POST "$API_BASE/api/tables/$TABLE_ID/action" \
          -H "Content-Type: application/json" \
          -d "{\"token\":\"$TOKEN\",\"action\":\"call\"}" > /dev/null
        echo "   ✅ 完成"
    else
        echo "   第 $i 次: 不是玩家回合或游戏已结束，跳过"
    fi
done
echo ""

# 10. 最终状态
echo "10. 查看最终状态..."
STATE=$(curl -s "$API_BASE/api/tables/$TABLE_ID?token=$TOKEN")
STAGE=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('stage', 'N/A'))" 2>/dev/null || echo "N/A")
POT=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('pot', 0))" 2>/dev/null || echo "0")

# 获取玩家筹码
PLAYER_STACK=$(echo $STATE | python3 -c "
import sys, json
d = json.load(sys.stdin)
players = d.get('game_state', {}).get('players', [])
for p in players:
    if p and p.get('player_id') == '$USER_ID':
        print(p.get('stack', 0))
        break
else:
    print('N/A')
" 2>/dev/null || echo "N/A")

echo "   阶段: $STAGE"
echo "   底池: $POT"
echo "   玩家筹码: $PLAYER_STACK"
echo ""

echo "=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo "💡 提示：查看服务端日志可以看到详细的行动记录"
echo "   执行: openclaw logs --follow"
echo "   或查看进程日志"

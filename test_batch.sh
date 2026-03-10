#!/bin/bash
# 批量游戏流程测试

set -e

API_BASE="http://127.0.0.1:5002"
NUM_TESTS=${1:-5}  # 默认运行5次测试

echo "============================================================"
echo "批量游戏流程测试 (共 $NUM_TESTS 次)"
echo "============================================================"
echo ""

TOTAL_GAMES=0
TOTAL_ROUNDS=0
TOTAL_POTS=0
START_TIME=$(date +%s)

for test_num in $(seq 1 $NUM_TESTS); do
    echo "========== 测试 $test_num/$NUM_TESTS =========="
    echo ""
    
    # 创建牌桌
    TABLE_RESPONSE=$(curl -s -X POST "$API_BASE/api/lobby/tables" \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"批量测试桌$test_num\",\"blinds\":\"10/20\",\"max_players\":6}")
    
    TABLE_ID=$(echo $TABLE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['tableId'])")
    echo "牌桌ID: $TABLE_ID"
    
    # 玩家登录
    LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/api/login" \
      -H "Content-Type: application/json" \
      -d "{\"username\":\"批量测试玩家$test_num\"}")
    
    TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")
    USER_ID=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['userId'])")
    
    # 入座
    curl -s -X POST "$API_BASE/api/tables/$TABLE_ID/sit" \
      -H "Content-Type: application/json" \
      -d "{\"token\":\"$TOKEN\",\"seat\":0}" > /dev/null
    
    echo "玩家入座，等待游戏开始..."
    sleep 3
    
    # 玩5轮
    ROUNDS=0
    MAX_POTS=0
    
    for round in {1..5}; do
        sleep 2
        
        STATE=$(curl -s "$API_BASE/api/tables/$TABLE_ID?token=$TOKEN")
        STAGE=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('stage', 'N/A'))" 2>/dev/null || echo "N/A")
        CURRENT=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('current_player_id', 'N/A'))" 2>/dev/null || echo "N/A")
        POT=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('pot', 0))" 2>/dev/null || echo "0")
        
        if [ "$POT" -gt "$MAX_POTS" ]; then
            MAX_POTS=$POT
        fi
        
        if [ "$STAGE" = "ENDED" ]; then
            ROUNDS=$((ROUNDS + 1))
            sleep 3
            continue
        fi
        
        if [ "$CURRENT" = "$USER_ID" ] && [ "$STAGE" != "N/A" ]; then
            # 随机选择行动
            RAND=$((RANDOM % 100))
            if [ $RAND -lt 60 ]; then
                # 60% 跟注
                curl -s -X POST "$API_BASE/api/tables/$TABLE_ID/action" \
                  -H "Content-Type: application/json" \
                  -d "{\"token\":\"$TOKEN\",\"action\":\"call\"}" > /dev/null
            elif [ $RAND -lt 80 ]; then
                # 20% 过牌
                curl -s -X POST "$API_BASE/api/tables/$TABLE_ID/action" \
                  -H "Content-Type: application/json" \
                  -d "{\"token\":\"$TOKEN\",\"action\":\"check\"}" > /dev/null
            else
                # 20% 弃牌
                curl -s -X POST "$API_BASE/api/tables/$TABLE_ID/action" \
                  -H "Content-Type: application/json" \
                  -d "{\"token\":\"$TOKEN\",\"action\":\"fold\"}" > /dev/null
            fi
        fi
    done
    
    # 获取最终筹码
    FINAL_STATE=$(curl -s "$API_BASE/api/tables/$TABLE_ID?token=$TOKEN")
    FINAL_STACK=$(echo $FINAL_STATE | python3 -c "
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
    
    TOTAL_GAMES=$((TOTAL_GAMES + 1))
    TOTAL_ROUNDS=$((TOTAL_ROUNDS + ROUNDS))
    TOTAL_POTS=$((TOTAL_POTS + MAX_POTS))
    
    echo "完成轮数: $ROUNDS, 最大底池: $MAX_POTS, 最终筹码: $FINAL_STACK"
    echo ""
done

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "============================================================"
echo "批量测试完成！"
echo "============================================================"
echo ""
echo "📊 统计数据："
echo "   总测试次数: $TOTAL_GAMES"
echo "   总完成轮数: $TOTAL_ROUNDS"
echo "   平均轮数: $((TOTAL_ROUNDS / TOTAL_GAMES))"
echo "   总底池累计: $TOTAL_POTS"
echo "   平均底池: $((TOTAL_POTS / TOTAL_GAMES))"
echo "   总耗时: ${DURATION}秒"
echo ""
echo "💡 查看详细日志："
echo "   process log sharp-summit --limit 200"

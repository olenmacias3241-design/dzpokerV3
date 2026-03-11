#!/bin/bash
# 保险功能测试脚本

set -e

API_BASE="http://127.0.0.1:8080"

echo "============================================================"
echo "保险功能测试"
echo "============================================================"
echo ""

# 1. 创建牌桌
echo "1. 创建牌桌..."
TABLE_RESPONSE=$(curl -s -X POST "$API_BASE/api/lobby/tables" \
  -H "Content-Type: application/json" \
  -d '{"name":"保险测试桌","blinds":"10/20","max_players":6}')

TABLE_ID=$(echo $TABLE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['tableId'])")
echo "   ✅ 牌桌ID: $TABLE_ID"
echo ""

# 2. 玩家登录
echo "2. 玩家登录..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/api/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"保险测试玩家"}')

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")
USER_ID=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['userId'])")
echo "   ✅ 玩家ID: $USER_ID"
echo ""

# 3. 入座
echo "3. 玩家入座..."
curl -s -X POST "$API_BASE/api/tables/$TABLE_ID/sit" \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"$TOKEN\",\"seat\":0}" > /dev/null
echo "   ✅ 已入座位0"
echo "   ⏳ 等待机器人填充（5秒）..."
sleep 5
echo ""

# 4. 查看初始状态
echo "4. 查看游戏状态..."
STATE=$(curl -s "$API_BASE/api/tables/$TABLE_ID?token=$TOKEN")
STAGE=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('stage', 'N/A'))" 2>/dev/null || echo "N/A")
POT=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('pot', 0))" 2>/dev/null || echo "0")
CARDS=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('community_cards', []))" 2>/dev/null || echo "[]")

echo "   阶段: $STAGE"
echo "   底池: $POT"
echo "   公共牌: $CARDS"
echo ""

# 5. 进行多轮游戏，尝试触发保险
echo "5. 进行游戏，尝试触发保险场景..."
echo "   （保险通常在 Turn 阶段，当玩家有听牌时触发）"
echo ""

for i in {1..10}; do
    echo "--- 第 $i 轮 ---"
    sleep 2
    
    STATE=$(curl -s "$API_BASE/api/tables/$TABLE_ID?token=$TOKEN")
    STAGE=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('stage', 'N/A'))" 2>/dev/null || echo "N/A")
    CURRENT=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('current_player_id', 'N/A'))" 2>/dev/null || echo "N/A")
    POT=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('pot', 0))" 2>/dev/null || echo "0")
    CARDS=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('community_cards', []))" 2>/dev/null || echo "[]")
    
    # 检查是否有保险待处理
    HAS_INSURANCE=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print('yes' if d.get('game_state', {}).get('pending_insurance') else 'no')" 2>/dev/null || echo "no")
    
    echo "阶段: $STAGE, 底池: $POT, 公共牌: $CARDS"
    
    if [ "$HAS_INSURANCE" = "yes" ]; then
        echo "🎰 保险机会出现！"
        
        INSURANCE_PLAYER=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('pending_insurance', {}).get('player_id', 'N/A'))" 2>/dev/null || echo "N/A")
        OUTS=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('pending_insurance', {}).get('outs', []))" 2>/dev/null || echo "[]")
        MAX_PREMIUM=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('pending_insurance', {}).get('max_premium', 0))" 2>/dev/null || echo "0")
        
        echo "   保险玩家: $INSURANCE_PLAYER"
        echo "   可保险牌: $OUTS"
        echo "   最大保费: $MAX_PREMIUM"
        
        if [ "$INSURANCE_PLAYER" = "$USER_ID" ]; then
            # 玩家的保险机会
            INSURANCE_AMOUNT=50
            if [ "$MAX_PREMIUM" -lt "$INSURANCE_AMOUNT" ]; then
                INSURANCE_AMOUNT=$MAX_PREMIUM
            fi
            
            echo "   玩家选择买保险: $INSURANCE_AMOUNT 筹码"
            INSURANCE_RESULT=$(curl -s -X POST "$API_BASE/api/tables/$TABLE_ID/insurance" \
              -H "Content-Type: application/json" \
              -d "{\"token\":\"$TOKEN\",\"amount\":$INSURANCE_AMOUNT}")
            
            echo "   结果: $INSURANCE_RESULT"
            echo ""
            echo "✅ 保险测试完成！"
            break
        else
            echo "   （机器人的保险机会，等待机器人决策）"
            sleep 2
        fi
        echo ""
        continue
    fi
    
    # 如果轮到玩家，自动跟注
    if [ "$CURRENT" = "$USER_ID" ] && [ "$STAGE" != "ENDED" ] && [ "$STAGE" != "N/A" ]; then
        ATC=$(echo $STATE | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('game_state', {}).get('amount_to_call', 0))" 2>/dev/null || echo "0")
        
        if [ "$ATC" -gt "0" ]; then
            echo "   玩家跟注 $ATC"
            curl -s -X POST "$API_BASE/api/tables/$TABLE_ID/action" \
              -H "Content-Type: application/json" \
              -d "{\"token\":\"$TOKEN\",\"action\":\"call\"}" > /dev/null
        else
            echo "   玩家过牌"
            curl -s -X POST "$API_BASE/api/tables/$TABLE_ID/action" \
              -H "Content-Type: application/json" \
              -d "{\"token\":\"$TOKEN\",\"action\":\"check\"}" > /dev/null
        fi
    else
        echo "   等待其他玩家..."
    fi
    
    # 如果游戏结束，等待新一局
    if [ "$STAGE" = "ENDED" ]; then
        echo "   手牌结束，等待新一局（4秒）..."
        sleep 4
    fi
    
    echo ""
done

echo "============================================================"
echo "测试完成！"
echo "============================================================"
echo ""
echo "💡 说明："
echo "   - 保险功能通常在 Turn 阶段触发"
echo "   - 需要玩家有听牌（如同花听牌、顺子听牌）"
echo "   - 如果没有触发保险，可能是因为牌面不符合条件"
echo "   - 可以多运行几次测试来增加触发概率"
echo ""
echo "📊 查看服务端日志："
echo "   process log sharp-summit"

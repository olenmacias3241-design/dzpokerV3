#!/usr/bin/env python3
"""
保险功能测试脚本

测试场景：
1. 创建牌桌并入座
2. 触发保险场景（需要特定牌面）
3. 测试买保险和不买保险的情况
"""

import requests
import time
import json

API_BASE = "http://127.0.0.1:5002"

def create_table():
    """创建牌桌"""
    resp = requests.post(f"{API_BASE}/api/lobby/tables", json={
        "name": "保险测试桌",
        "blinds": "10/20",
        "max_players": 6
    })
    data = resp.json()
    return data['tableId']

def login(username):
    """玩家登录"""
    resp = requests.post(f"{API_BASE}/api/login", json={
        "username": username
    })
    data = resp.json()
    return data['token'], data['userId']

def sit(table_id, token, seat):
    """入座"""
    resp = requests.post(f"{API_BASE}/api/tables/{table_id}/sit", json={
        "token": token,
        "seat": seat
    })
    return resp.json()

def get_table_state(table_id, token):
    """获取牌桌状态"""
    resp = requests.get(f"{API_BASE}/api/tables/{table_id}", params={"token": token})
    return resp.json()

def player_action(table_id, token, action, amount=0):
    """玩家行动"""
    resp = requests.post(f"{API_BASE}/api/tables/{table_id}/action", json={
        "token": token,
        "action": action,
        "amount": amount
    })
    return resp.json()

def buy_insurance(table_id, token, amount):
    """买保险"""
    resp = requests.post(f"{API_BASE}/api/tables/{table_id}/insurance", json={
        "token": token,
        "amount": amount
    })
    return resp.json()

def decline_insurance(table_id, token):
    """拒绝保险"""
    resp = requests.post(f"{API_BASE}/api/tables/{table_id}/insurance/decline", json={
        "token": token
    })
    return resp.json()

def print_game_state(state):
    """打印游戏状态"""
    gs = state.get('game_state', {})
    print(f"  阶段: {gs.get('stage', 'N/A')}")
    print(f"  底池: {gs.get('pot', 0)}")
    print(f"  公共牌: {gs.get('community_cards', [])}")
    
    pending_insurance = gs.get('pending_insurance')
    if pending_insurance:
        print(f"  ⚠️  保险待处理:")
        print(f"     玩家: {pending_insurance.get('player_id')}")
        print(f"     可保险牌: {pending_insurance.get('outs', [])}")
        print(f"     赔率: {pending_insurance.get('odds', 'N/A')}")
        print(f"     最大保费: {pending_insurance.get('max_premium', 0)}")
    
    players = gs.get('players', [])
    for p in players:
        if p:
            print(f"  玩家 {p.get('seat')}: {p.get('player_id')}, 筹码: {p.get('stack')}, 底牌: {p.get('hole_cards', [])}")

def main():
    print("=" * 60)
    print("保险功能测试")
    print("=" * 60)
    print()
    
    # 1. 创建牌桌
    print("1. 创建牌桌...")
    table_id = create_table()
    print(f"   ✅ 牌桌ID: {table_id}")
    print()
    
    # 2. 玩家登录并入座
    print("2. 玩家登录并入座...")
    token, user_id = login("保险测试玩家")
    print(f"   ✅ 玩家ID: {user_id}")
    
    sit(table_id, token, 0)
    print(f"   ✅ 已入座位0")
    print()
    
    # 3. 等待机器人填充和游戏开始
    print("3. 等待机器人填充和游戏开始（5秒）...")
    time.sleep(5)
    print()
    
    # 4. 查看初始状态
    print("4. 查看游戏状态...")
    state = get_table_state(table_id, token)
    print_game_state(state)
    print()
    
    # 5. 玩几轮，尝试触发保险场景
    print("5. 进行游戏，尝试触发保险场景...")
    print("   （保险通常在 Turn 阶段，当玩家有听牌时触发）")
    print()
    
    for round_num in range(1, 6):
        print(f"--- 第 {round_num} 轮 ---")
        time.sleep(2)
        
        state = get_table_state(table_id, token)
        gs = state.get('game_state', {})
        current_player = gs.get('current_player_id')
        stage = gs.get('stage')
        pending_insurance = gs.get('pending_insurance')
        
        print(f"阶段: {stage}, 当前玩家: {current_player}")
        
        # 检查是否有保险待处理
        if pending_insurance:
            print("🎰 保险机会出现！")
            print(f"   可保险牌: {pending_insurance.get('outs', [])}")
            print(f"   赔率: {pending_insurance.get('odds', 'N/A')}")
            print(f"   最大保费: {pending_insurance.get('max_premium', 0)}")
            
            if pending_insurance.get('player_id') == user_id:
                # 测试买保险
                max_premium = pending_insurance.get('max_premium', 0)
                insurance_amount = min(100, max_premium)
                
                print(f"   玩家选择买保险: {insurance_amount} 筹码")
                result = buy_insurance(table_id, token, insurance_amount)
                print(f"   结果: {result}")
            else:
                print("   （机器人的保险机会）")
            print()
            continue
        
        # 如果轮到玩家，自动跟注
        if current_player == user_id and stage not in ['ENDED', None]:
            atc = gs.get('amount_to_call', 0)
            if atc > 0:
                print(f"   玩家跟注 {atc}")
                result = player_action(table_id, token, "call")
            else:
                print(f"   玩家过牌")
                result = player_action(table_id, token, "check")
            
            # 检查返回结果中是否有保险
            if result.get('pending_insurance'):
                print("   🎰 行动后触发保险！")
                print_game_state({'game_state': result})
        else:
            print(f"   等待其他玩家...")
        
        print()
        
        # 如果游戏结束，等待新一局
        if stage == 'ENDED':
            print("   手牌结束，等待新一局（4秒）...")
            time.sleep(4)
    
    # 6. 最终状态
    print("6. 最终状态...")
    state = get_table_state(table_id, token)
    print_game_state(state)
    print()
    
    print("=" * 60)
    print("测试完成！")
    print("=" * 60)
    print()
    print("💡 说明：")
    print("   - 保险功能通常在 Turn 阶段触发")
    print("   - 需要玩家有听牌（如同花听牌、顺子听牌）")
    print("   - 如果没有触发保险，可能是因为牌面不符合条件")
    print("   - 可以多运行几次测试来增加触发概率")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n测试中断")
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()

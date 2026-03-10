#!/usr/bin/env python3
"""
主池/边池分配集成测试

直接测试 game_logic 中的边池计算功能
"""

import sys
sys.path.insert(0, '/Users/taoyin/.openclaw/workspace/dzpokerV3')

from core import pot_manager

def test_simple_pot():
    """测试场景1：简单主池，无 All-in"""
    print("\n=== 测试1：简单主池（无 All-in）===")
    
    players_state = {
        'player0': {'total_bet_this_hand': 100, 'is_folded': False},
        'player1': {'total_bet_this_hand': 100, 'is_folded': False}
    }
    
    pots = pot_manager.calculate_side_pots(players_state)
    
    print(f"底池数量: {len(pots)}")
    for i, pot in enumerate(pots):
        print(f"  底池{i}: 金额={pot['amount']}, 有资格={pot['eligible_players']}")
    
    assert len(pots) == 1
    assert pots[0]['amount'] == 200
    assert set(pots[0]['eligible_players']) == {'player0', 'player1'}
    print("✅ 测试通过")


def test_single_side_pot():
    """测试场景2：单边池（一人 All-in）"""
    print("\n=== 测试2：单边池（一人 All-in）===")
    
    players_state = {
        'player0': {'total_bet_this_hand': 50, 'is_folded': False},   # All-in 50
        'player1': {'total_bet_this_hand': 100, 'is_folded': False}   # 下注 100
    }
    
    pots = pot_manager.calculate_side_pots(players_state)
    
    print(f"底池数量: {len(pots)}")
    for i, pot in enumerate(pots):
        print(f"  底池{i}: 金额={pot['amount']}, 有资格={pot['eligible_players']}")
    
    # 主池：50*2=100，两人都有资格
    # 边池：50，只有 player1 有资格
    assert len(pots) == 2
    assert pots[0]['amount'] == 100
    assert set(pots[0]['eligible_players']) == {'player0', 'player1'}
    assert pots[1]['amount'] == 50
    assert set(pots[1]['eligible_players']) == {'player1'}
    print("✅ 测试通过")


def test_multiple_side_pots():
    """测试场景3：多边池（三人 All-in，金额不同）"""
    print("\n=== 测试3：多边池（三人 All-in，金额不同）===")
    
    players_state = {
        'player0': {'total_bet_this_hand': 30, 'is_folded': False},   # All-in 30
        'player1': {'total_bet_this_hand': 60, 'is_folded': False},   # All-in 60
        'player2': {'total_bet_this_hand': 100, 'is_folded': False}   # 下注 100
    }
    
    pots = pot_manager.calculate_side_pots(players_state)
    
    print(f"底池数量: {len(pots)}")
    for i, pot in enumerate(pots):
        print(f"  底池{i}: 金额={pot['amount']}, 有资格={pot['eligible_players']}")
    
    # 主池：30*3=90，所有人有资格
    # 边池1：(60-30)*2=60，player1 和 player2 有资格
    # 边池2：(100-60)*1=40，只有 player2 有资格
    assert len(pots) == 3
    assert pots[0]['amount'] == 90
    assert set(pots[0]['eligible_players']) == {'player0', 'player1', 'player2'}
    assert pots[1]['amount'] == 60
    assert set(pots[1]['eligible_players']) == {'player1', 'player2'}
    assert pots[2]['amount'] == 40
    assert set(pots[2]['eligible_players']) == {'player2'}
    print("✅ 测试通过")


def test_with_folded_players():
    """测试场景4：有玩家弃牌"""
    print("\n=== 测试4：有玩家弃牌===")
    
    players_state = {
        'player0': {'total_bet_this_hand': 50, 'is_folded': True},    # 弃牌，但已下注50
        'player1': {'total_bet_this_hand': 100, 'is_folded': False},
        'player2': {'total_bet_this_hand': 100, 'is_folded': False}
    }
    
    pots = pot_manager.calculate_side_pots(players_state)
    
    print(f"底池数量: {len(pots)}")
    for i, pot in enumerate(pots):
        print(f"  底池{i}: 金额={pot['amount']}, 有资格={pot['eligible_players']}")
    
    # 只有 player1 和 player2 有资格（player0 已弃牌）
    # player0 的 50 筹码不计入（因为已弃牌）
    assert len(pots) == 1
    assert pots[0]['amount'] == 200  # 100 + 100（player0 弃牌后筹码不计入）
    assert set(pots[0]['eligible_players']) == {'player1', 'player2'}
    print("✅ 测试通过")


def test_complex_scenario():
    """测试场景5：复杂场景（4人，多种下注）"""
    print("\n=== 测试5：复杂场景（4人，多边池）===")
    
    players_state = {
        'player0': {'total_bet_this_hand': 20, 'is_folded': False},   # All-in 20
        'player1': {'total_bet_this_hand': 50, 'is_folded': False},   # All-in 50
        'player2': {'total_bet_this_hand': 100, 'is_folded': False},  # 下注 100
        'player3': {'total_bet_this_hand': 100, 'is_folded': False}   # 下注 100
    }
    
    pots = pot_manager.calculate_side_pots(players_state)
    
    print(f"底池数量: {len(pots)}")
    for i, pot in enumerate(pots):
        print(f"  底池{i}: 金额={pot['amount']}, 有资格={pot['eligible_players']}")
    
    # 主池：20*4=80，所有人有资格
    # 边池1：(50-20)*3=90，player1,2,3 有资格
    # 边池2：(100-50)*2=100，player2,3 有资格
    assert len(pots) == 3
    assert pots[0]['amount'] == 80
    assert set(pots[0]['eligible_players']) == {'player0', 'player1', 'player2', 'player3'}
    assert pots[1]['amount'] == 90
    assert set(pots[1]['eligible_players']) == {'player1', 'player2', 'player3'}
    assert pots[2]['amount'] == 100
    assert set(pots[2]['eligible_players']) == {'player2', 'player3'}
    print("✅ 测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("主池/边池分配测试")
    print("=" * 60)
    
    try:
        test_simple_pot()
        test_single_side_pot()
        test_multiple_side_pots()
        test_with_folded_players()
        test_complex_scenario()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

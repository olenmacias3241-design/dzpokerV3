#!/usr/bin/env python3
"""
主池/边池分配测试脚本

测试场景：
1. 简单主池：两人对决，无 All-in
2. 单边池：一人 All-in，另一人筹码更多
3. 多边池：多人 All-in，金额不同
"""

import sys
from core.pot_manager import PotManager
from core.hand_evaluator import HandEvaluator

def test_simple_pot():
    """测试场景1：简单主池，无 All-in"""
    print("\n=== 测试1：简单主池（无 All-in）===")
    
    pm = PotManager()
    
    # 玩家0下注100，玩家1下注100
    pm.add_bet(0, 100)
    pm.add_bet(1, 100)
    
    pots = pm.get_pots()
    print(f"底池数量: {len(pots)}")
    print(f"主池金额: {pots[0]['amount']}")
    print(f"有资格玩家: {pots[0]['eligible_players']}")
    
    # 玩家0赢
    winners = {0: ("一对A", [("AS", "AH", "AD", "KC", "QD")])}
    pm.distribute(winners)
    
    print(f"玩家0赢得: {pm.get_player_winnings(0)}")
    print(f"玩家1赢得: {pm.get_player_winnings(1)}")
    
    assert pm.get_player_winnings(0) == 200
    assert pm.get_player_winnings(1) == 0
    print("✅ 测试通过")


def test_single_side_pot():
    """测试场景2：单边池（一人 All-in）"""
    print("\n=== 测试2：单边池（一人 All-in）===")
    
    pm = PotManager()
    
    # 玩家0 All-in 50，玩家1下注100
    pm.add_bet(0, 50, is_all_in=True)
    pm.add_bet(1, 100)
    
    pots = pm.get_pots()
    print(f"底池数量: {len(pots)}")
    
    for i, pot in enumerate(pots):
        print(f"底池{i}: 金额={pot['amount']}, 有资格={pot['eligible_players']}")
    
    # 主池：50*2=100，玩家0和1都有资格
    # 边池：50，只有玩家1有资格
    assert len(pots) == 2
    assert pots[0]['amount'] == 100
    assert set(pots[0]['eligible_players']) == {0, 1}
    assert pots[1]['amount'] == 50
    assert set(pots[1]['eligible_players']) == {1}
    
    # 玩家0赢（但只能赢主池）
    winners = {0: ("同花", [("AS", "KS", "QS", "JS", "9S")])}
    pm.distribute(winners)
    
    print(f"玩家0赢得: {pm.get_player_winnings(0)} (只能赢主池)")
    print(f"玩家1赢得: {pm.get_player_winnings(1)} (赢边池)")
    
    assert pm.get_player_winnings(0) == 100  # 只赢主池
    assert pm.get_player_winnings(1) == 50   # 赢边池
    print("✅ 测试通过")


def test_multiple_side_pots():
    """测试场景3：多边池（多人 All-in，金额不同）"""
    print("\n=== 测试3：多边池（三人 All-in，金额不同）===")
    
    pm = PotManager()
    
    # 玩家0 All-in 30
    # 玩家1 All-in 60
    # 玩家2 下注 100
    pm.add_bet(0, 30, is_all_in=True)
    pm.add_bet(1, 60, is_all_in=True)
    pm.add_bet(2, 100)
    
    pots = pm.get_pots()
    print(f"底池数量: {len(pots)}")
    
    for i, pot in enumerate(pots):
        print(f"底池{i}: 金额={pot['amount']}, 有资格={pot['eligible_players']}")
    
    # 主池：30*3=90，所有人有资格
    # 边池1：(60-30)*2=60，玩家1和2有资格
    # 边池2：(100-60)*1=40，只有玩家2有资格
    assert len(pots) == 3
    assert pots[0]['amount'] == 90
    assert set(pots[0]['eligible_players']) == {0, 1, 2}
    assert pots[1]['amount'] == 60
    assert set(pots[1]['eligible_players']) == {1, 2}
    assert pots[2]['amount'] == 40
    assert set(pots[2]['eligible_players']) == {2}
    
    # 玩家1赢（赢主池+边池1）
    winners = {1: ("三条", [("KH", "KC", "KD", "AS", "QD")])}
    pm.distribute(winners)
    
    print(f"玩家0赢得: {pm.get_player_winnings(0)}")
    print(f"玩家1赢得: {pm.get_player_winnings(1)} (赢主池+边池1)")
    print(f"玩家2赢得: {pm.get_player_winnings(2)} (赢边池2)")
    
    assert pm.get_player_winnings(0) == 0
    assert pm.get_player_winnings(1) == 150  # 主池90 + 边池1的60
    assert pm.get_player_winnings(2) == 40   # 边池2
    print("✅ 测试通过")


def test_split_pot():
    """测试场景4：平分底池"""
    print("\n=== 测试4：平分底池（两人牌型相同）===")
    
    pm = PotManager()
    
    # 玩家0和1各下注100
    pm.add_bet(0, 100)
    pm.add_bet(1, 100)
    
    # 两人都赢（平分）
    winners = {
        0: ("一对K", [("KH", "KC", "AS", "QD", "JC")]),
        1: ("一对K", [("KS", "KD", "AS", "QD", "JC")])
    }
    pm.distribute(winners)
    
    print(f"玩家0赢得: {pm.get_player_winnings(0)}")
    print(f"玩家1赢得: {pm.get_player_winnings(1)}")
    
    assert pm.get_player_winnings(0) == 100
    assert pm.get_player_winnings(1) == 100
    print("✅ 测试通过")


def test_complex_scenario():
    """测试场景5：复杂场景（4人，2人 All-in，1人平分）"""
    print("\n=== 测试5：复杂场景（4人，多边池，平分）===")
    
    pm = PotManager()
    
    # 玩家0 All-in 20
    # 玩家1 All-in 50
    # 玩家2 下注 100
    # 玩家3 下注 100
    pm.add_bet(0, 20, is_all_in=True)
    pm.add_bet(1, 50, is_all_in=True)
    pm.add_bet(2, 100)
    pm.add_bet(3, 100)
    
    pots = pm.get_pots()
    print(f"底池数量: {len(pots)}")
    
    for i, pot in enumerate(pots):
        print(f"底池{i}: 金额={pot['amount']}, 有资格={pot['eligible_players']}")
    
    # 主池：20*4=80，所有人有资格
    # 边池1：(50-20)*3=90，玩家1,2,3有资格
    # 边池2：(100-50)*2=100，玩家2,3有资格
    assert len(pots) == 3
    assert pots[0]['amount'] == 80
    assert pots[1]['amount'] == 90
    assert pots[2]['amount'] == 100
    
    # 玩家2和3平分边池2，玩家1赢其他
    winners = {
        1: ("三条", [("KH", "KC", "KD", "AS", "QD")]),
        2: ("一对A", [("AH", "AC", "KS", "QD", "JC")]),
        3: ("一对A", [("AS", "AD", "KS", "QD", "JC")])
    }
    pm.distribute(winners)
    
    print(f"玩家0赢得: {pm.get_player_winnings(0)}")
    print(f"玩家1赢得: {pm.get_player_winnings(1)} (赢主池+边池1)")
    print(f"玩家2赢得: {pm.get_player_winnings(2)} (平分边池2)")
    print(f"玩家3赢得: {pm.get_player_winnings(3)} (平分边池2)")
    
    assert pm.get_player_winnings(0) == 0
    assert pm.get_player_winnings(1) == 170  # 主池80 + 边池1的90
    assert pm.get_player_winnings(2) == 50   # 边池2的一半
    assert pm.get_player_winnings(3) == 50   # 边池2的一半
    print("✅ 测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("主池/边池分配测试")
    print("=" * 60)
    
    try:
        test_simple_pot()
        test_single_side_pot()
        test_multiple_side_pots()
        test_split_pot()
        test_complex_scenario()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

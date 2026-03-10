# dzpokerV3/core/pot_manager.py
# 边池（Side Pot）管理

def calculate_side_pots(players_state):
    """
    计算边池分配。
    
    Args:
        players_state: dict of {player_id: {'total_bet': int, 'is_folded': bool, ...}}
    
    Returns:
        list of {'amount': int, 'eligible_players': [player_ids]}
    """
    # 获取所有未弃牌玩家的总下注
    active_bets = []
    for pid, pstate in players_state.items():
        if not pstate.get('is_folded', False):
            total_bet = pstate.get('total_bet_this_hand', 0)
            if total_bet > 0:
                active_bets.append((pid, total_bet))
    
    if not active_bets:
        return []
    
    # 按下注金额排序
    active_bets.sort(key=lambda x: x[1])
    
    pots = []
    prev_level = 0
    
    for i, (pid, bet_amount) in enumerate(active_bets):
        if bet_amount <= prev_level:
            continue
        
        # 计算这一层的边池金额
        contribution = bet_amount - prev_level
        # 有资格参与这个池的玩家：下注 >= bet_amount 的所有未弃牌玩家
        eligible = [p for p, b in active_bets if b >= bet_amount]
        
        # 计算池的总金额：每个还在游戏中的玩家贡献 contribution
        pot_amount = 0
        for p_id, p_state in players_state.items():
            if not p_state.get('is_folded', False):
                p_total = p_state.get('total_bet_this_hand', 0)
                pot_amount += min(contribution, max(0, p_total - prev_level))
        
        if pot_amount > 0:
            pots.append({
                'amount': pot_amount,
                'eligible_players': eligible
            })
        
        prev_level = bet_amount
    
    return pots


def distribute_pots(pots, hand_ranks, players_state):
    """
    根据手牌强度分配边池。
    
    Args:
        pots: list of {'amount': int, 'eligible_players': [player_ids]}
        hand_ranks: dict of {player_id: hand_rank_tuple}
        players_state: dict of player states
    
    Returns:
        dict of {player_id: winnings}
    """
    winnings = {}
    
    for pot in pots:
        eligible = pot['eligible_players']
        amount = pot['amount']
        
        # 找出有资格且未弃牌的玩家中手牌最强的
        best_rank = None
        winners = []
        
        for pid in eligible:
            if players_state[pid].get('is_folded', False):
                continue
            
            rank = hand_ranks.get(pid)
            if rank is None:
                continue
            
            if best_rank is None or rank > best_rank:
                best_rank = rank
                winners = [pid]
            elif rank == best_rank:
                winners.append(pid)
        
        # 平分给获胜者
        if winners:
            share = amount // len(winners)
            remainder = amount % len(winners)
            
            for i, winner in enumerate(winners):
                winnings[winner] = winnings.get(winner, 0) + share
                if i == 0:  # 第一个获胜者拿余数
                    winnings[winner] += remainder
    
    return winnings

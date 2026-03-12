# dzpokerV3/core/pot_manager.py
# 边池（Side Pot）管理，知识库：docs/knowledge/TEXAS_HOLDEM_PLAY_AND_RULES.md §9

def calculate_side_pots(players_state):
    """
    按知识库计算边池：主池由最小 All-in 档位界定，每档位一个池；
    池金额 = 所有玩家「投入该档位上限」的合计（含弃牌玩家）；有资格赢取 = 未弃牌且 total_bet >= 该档位。

    Args:
        players_state: dict of {player_id: {'total_bet_this_hand': int, 'is_folded': bool}}

    Returns:
        list of {'amount': int, 'eligible_players': [player_ids]}
    """
    # 所有玩家的 total_bet_this_hand 作为档位（含弃牌）
    all_bets = [pstate.get('total_bet_this_hand', 0) for pstate in players_state.values()]
    levels = sorted(set(b for b in all_bets if b > 0))
    if not levels:
        return []

    pots = []
    prev_level = 0
    for level in levels:
        # 本档位池子金额 = 每个玩家 min(total_bet, level) 之和 - 已计入前面池子的部分
        pot_amount = 0
        for pid, pstate in players_state.items():
            total_bet = pstate.get('total_bet_this_hand', 0)
            contrib = min(total_bet, level) - min(total_bet, prev_level)
            pot_amount += max(0, contrib)
        # 有资格赢取：未弃牌且本局投入 >= level
        eligible = [
            pid for pid, pstate in players_state.items()
            if not pstate.get('is_folded', False) and pstate.get('total_bet_this_hand', 0) >= level
        ]
        if pot_amount > 0:
            pots.append({'amount': pot_amount, 'eligible_players': eligible})
        prev_level = level
    return pots


def _winner_closest_to_dealer(winners, player_order, dealer_pid):
    """在 winners 中返回离 dealer 最近的那位（player_order 顺时针，dealer 下一位最先）。"""
    if not winners or not player_order or dealer_pid not in player_order:
        return winners[0] if winners else None
    n = len(player_order)
    dealer_idx = player_order.index(dealer_pid)
    # 从 dealer 下一位起顺时针，第一个在 winners 里的
    for i in range(1, n + 1):
        idx = (dealer_idx + i) % n
        pid = player_order[idx]
        if pid in winners:
            return pid
    return winners[0]


def distribute_pots(pots, hand_ranks, players_state, player_order=None, dealer_pid=None):
    """
    按牌型分配边池；平分时奇数筹码给「位置最靠前（离 Dealer 最近）」的玩家。

    Args:
        pots: list of {'amount': int, 'eligible_players': [player_ids]}
        hand_ranks: dict of {player_id: comparable_rank_tuple}
        players_state: dict of player states (is_folded, total_bet_this_hand)
        player_order: 可选，座位顺序列表（用于奇数筹码）
        dealer_pid: 可选，庄家 player_id（用于奇数筹码）

    Returns:
        dict of {player_id: winnings}
    """
    winnings = {}
    for pot in pots:
        eligible = pot['eligible_players']
        amount = pot['amount']
        best_rank = None
        winners = []
        for pid in eligible:
            if players_state.get(pid, {}).get('is_folded', False):
                continue
            rank = hand_ranks.get(pid)
            if rank is None:
                continue
            if best_rank is None or rank > best_rank:
                best_rank = rank
                winners = [pid]
            elif rank == best_rank:
                winners.append(pid)
        if not winners:
            continue
        share = amount // len(winners)
        remainder = amount % len(winners)
        for w in winners:
            winnings[w] = winnings.get(w, 0) + share
        if remainder > 0 and player_order and dealer_pid:
            closest = _winner_closest_to_dealer(winners, player_order, dealer_pid)
            if closest is not None:
                winnings[closest] = winnings.get(closest, 0) + remainder
        elif remainder > 0:
            winnings[winners[0]] = winnings.get(winners[0], 0) + remainder
    return winnings

# dzpokerV3/core/hand_evaluator.py
# 知识库依据：docs/knowledge/TEXAS_HOLDEM_PLAY_AND_RULES.md
# 牌型 10 档、顺子/同花/同花顺、A-2-3-4-5(Wheel)、踢脚比较、可比元组

from .cards import Card

# 牌型名称（与 hand_type_index 对应），用于前端显示
# 顺序：高牌=0, 一对=1, 两对=2, 三条=3, 顺子=4, 同花=5, 葫芦=6, 四条=7, 同花顺=8, 皇家同花顺=9
HAND_TYPE_NAMES = [
    "高牌", "一对", "两对", "三条", "顺子", "同花", "葫芦", "四条", "同花顺", "皇家同花顺"
]

# 点数到可比整数的映射：2=0, 3=1, ..., K=11, A=12（比大小时 A 最大）
RANK_ORDER = {r: i for i, r in enumerate('23456789TJQKA')}
# 顺子中 A 当 1 时（Wheel）：A=0
RANK_ORDER_LOW = {r: i for i, r in enumerate('A23456789TJQK')}


def _rank_val(card, low_ace=False):
    """单张牌点数用于比较；low_ace=True 时 A 当 1（仅用于 Wheel）。"""
    r = card.rank if hasattr(card, 'rank') else str(card)[0]
    return RANK_ORDER_LOW.get(r, RANK_ORDER.get(r, 0)) if low_ace else RANK_ORDER.get(r, 0)


def _is_flush(cards):
    """5 张牌是否同花。"""
    if len(cards) < 5:
        return False
    s = cards[0].suit if hasattr(cards[0], 'suit') else str(cards[0])[1]
    return all((c.suit if hasattr(c, 'suit') else str(c)[1]) == s for c in cards)


def _straight_high(ranks_sorted_desc):
    """
    从已排序的 5 个点数（从大到小）判断是否顺子；若是则返回顺子最高张的 rank_val，否则 None。
    支持 Wheel：A,5,4,3,2 -> 5 为最高张（A 当 1）。
    """
    # ranks_sorted_desc: 5 个 rank_val 从大到小
    if len(ranks_sorted_desc) != 5:
        return None
    uniq = list(dict.fromkeys(ranks_sorted_desc))
    if len(uniq) != 5:
        return None
    # 普通顺子：连续 5 个数
    if uniq[0] - uniq[4] == 4:
        return uniq[0]
    # Wheel: A-2-3-4-5 -> 在 RANK_ORDER 中 A=12, 2=0,3=1,4=2,5=3 -> 12,0,1,2,3 需特殊处理
    # 用 RANK_ORDER_LOW: A=0,2=1,3=2,4=3,5=4 -> 0,1,2,3,4 连续，最高张是 5 -> rank_val=4
    return None


def _straight_high_from_cards(cards, low_ace=False):
    """从 5 张牌得到顺子最高张的 rank_val（RANK_ORDER 下），非顺子返回 None。Wheel 返回 3 表示 5 高（最小顺子）。"""
    rank_map = RANK_ORDER_LOW if low_ace else RANK_ORDER
    vals = sorted([rank_map.get(c.rank if hasattr(c, 'rank') else str(c)[0], 0) for c in cards], reverse=True)
    if len(vals) != 5:
        return None
    uniq = list(dict.fromkeys(vals))
    if len(uniq) != 5:
        return None
    if uniq[0] - uniq[4] == 4:
        # 普通顺子：返回在 RANK_ORDER 下的最高张（用于比较）
        if low_ace:
            # 用的是 RANK_ORDER_LOW，最高张 uniq[0] 是 4 表示 5，对应 RANK_ORDER 里 5=3
            return 3  # Wheel
        return uniq[0]
    # Wheel (A-2-3-4-5): 仅在 low_ace 下 [4,3,2,1,0]
    if low_ace and uniq == [4, 3, 2, 1, 0]:
        return 3
    return None


def _eval_five(cards):
    """
    评估 5 张牌，返回 (hand_level, tie_break_tuple, hand_type_index)。
    hand_level: 0=高牌, 1=一对, ..., 8=同花顺, 9=皇家同花顺（同花顺 A 高）
    tie_break_tuple: 用于同牌型比较的元组，从大到小。
    """
    if len(cards) != 5:
        return (0, (0, 0, 0, 0, 0), 0)
    # 统一为 Card
    conv = []
    for c in cards:
        if isinstance(c, Card):
            conv.append(c)
        elif isinstance(c, str) and len(c) >= 2:
            conv.append(Card(c[0], c[1]))
        else:
            continue
    if len(conv) != 5:
        return (0, (0, 0, 0, 0, 0), 0)
    cards = conv

    rank_vals = [_rank_val(c) for c in cards]
    rank_vals_hi = sorted(rank_vals, reverse=True)
    counts = {}
    for r in rank_vals:
        counts[r] = counts.get(r, 0) + 1
    # 按出现次数降序、再按点数降序
    by_count = sorted(counts.items(), key=lambda x: (-x[1], -x[0]))
    is_flush = _is_flush(cards)
    straight_hi = _straight_high_from_cards(cards, low_ace=False)
    # Wheel: A,2,3,4,5 在 RANK_ORDER_LOW 中为 0,1,2,3,4，连续
    rv_low = sorted([_rank_val(c, low_ace=True) for c in cards], reverse=True)
    wheel_ok = len(set(rv_low)) == 5 and rv_low == [4, 3, 2, 1, 0]

    # 同花顺 / 皇家同花顺
    if is_flush:
        straight_hi_flush = _straight_high_from_cards(cards, low_ace=False)
        if wheel_ok:
            straight_hi_flush = 3  # Wheel 同花顺，最小
        elif straight_hi_flush is None:
            straight_hi_flush = _straight_high_from_cards(cards, low_ace=True)  # 仅 Wheel 可能
            if straight_hi_flush is not None:
                straight_hi_flush = 3
        if straight_hi_flush is not None:
            if straight_hi_flush == 12:  # A high
                return (9, (12,), 9)   # 皇家同花顺
            return (8, (straight_hi_flush,), 8)  # 同花顺

    # 四条
    if len(by_count) >= 1 and by_count[0][1] == 4:
        quad = by_count[0][0]
        kicker = by_count[1][0] if len(by_count) > 1 else 0
        return (7, (quad, kicker), 7)

    # 葫芦
    if len(by_count) >= 2 and by_count[0][1] == 3 and by_count[1][1] >= 2:
        trip = by_count[0][0]
        pair = by_count[1][0]
        return (6, (trip, pair), 6)

    # 同花（非顺子）
    if is_flush:
        return (5, tuple(rank_vals_hi), 5)

    # 顺子（非同花）
    if straight_hi is not None:
        return (4, (straight_hi,), 4)
    if wheel_ok:
        return (4, (3,), 4)  # Wheel 最高张 5，最小顺子

    # 三条
    if len(by_count) >= 1 and by_count[0][1] == 3:
        trip = by_count[0][0]
        kickers = sorted([r for r in rank_vals if r != trip], reverse=True)[:2]
        return (3, (trip, kickers[0], kickers[1]) if len(kickers) >= 2 else (trip, kickers[0], 0), 3)

    # 两对
    if len(by_count) >= 2 and by_count[0][1] == 2 and by_count[1][1] == 2:
        p1, p2 = by_count[0][0], by_count[1][0]
        if p1 < p2:
            p1, p2 = p2, p1
        kicker = next((r for r in rank_vals if r != p1 and r != p2), 0)
        return (2, (p1, p2, kicker), 2)

    # 一对
    if len(by_count) >= 1 and by_count[0][1] == 2:
        pair = by_count[0][0]
        kickers = sorted([r for r in rank_vals if r != pair], reverse=True)[:3]
        while len(kickers) < 3:
            kickers.append(0)
        return (1, (pair, kickers[0], kickers[1], kickers[2]), 1)

    # 高牌
    while len(rank_vals_hi) < 5:
        rank_vals_hi.append(0)
    return (0, tuple(rank_vals_hi[:5]), 0)


def evaluate_hand(hole_cards, community_cards):
    """
    从 2 张底牌 + 最多 5 张公共牌中选出最佳 5 张组合，返回可比元组与牌型。

    Args:
        hole_cards: list[Card] 或可转成 rank/suit 的对象
        community_cards: list[Card]，取前 5 张

    Returns:
        (rank_tuple, best_5_cards, hand_type_index)
        - rank_tuple: 元组 (hand_level, v1, v2, ...)，可直接用 > 比较大小
        - best_5_cards: 组成最佳牌型的 5 张牌
        - hand_type_index: 0~9 对应 HAND_TYPE_NAMES
    """
    all_cards = list(hole_cards)[:2] + list(community_cards)[:5]
    # 转为 Card
    conv = []
    for c in all_cards:
        if isinstance(c, Card):
            conv.append(c)
        elif isinstance(c, str) and len(c) >= 2:
            conv.append(Card(c[0], c[1]))
        elif hasattr(c, 'rank') and hasattr(c, 'suit'):
            conv.append(Card(c.rank, c.suit))
        else:
            continue
    all_cards = conv
    if len(all_cards) < 5:
        return ((0, 0, 0, 0, 0, 0), [], 0)

    import itertools
    best_rank = (0, 0, 0, 0, 0, 0)
    best_hand = []
    best_type = 0
    for combo in itertools.combinations(all_cards, 5):
        level, tie_break, type_idx = _eval_five(combo)
        # 拼成统一长度以便比较（level + 最多 5 个 tie-break）
        tb = list(tie_break)[:5]
        while len(tb) < 5:
            tb.append(0)
        rank_tuple = (level,) + tuple(tb)
        if rank_tuple > best_rank:
            best_rank = rank_tuple
            best_hand = list(combo)
            best_type = type_idx
    return (best_rank, best_hand, best_type)


def get_hand_type_name(hole_cards, community_cards):
    """返回当前牌型中文名；牌不足 5 张时返回 None。"""
    if not hole_cards or len(hole_cards) < 2:
        return None
    community = list(community_cards)[:5] if community_cards else []
    if len(hole_cards) + len(community) < 5:
        return None
    _, _, idx = evaluate_hand(hole_cards, community)
    return HAND_TYPE_NAMES[idx] if 0 <= idx < len(HAND_TYPE_NAMES) else "高牌"


def find_winners(game_state):
    """
    从摊牌玩家中找出赢家（牌型最大者）。
    未弃牌且 is_active 的玩家参与比牌；仅一人则直接为该玩家。
    """
    showdown_players = [
        pid for pid, p in game_state.get('players', {}).items()
        if p.get('is_in_hand') and p.get('is_active', True)  # 未弃牌；缺 is_active 视为仍在局
    ]
    if not showdown_players:
        return []
    if len(showdown_players) == 1:
        return showdown_players

    best_rank = None
    winners = []
    for pid in showdown_players:
        p = game_state['players'][pid]
        hole = p.get('hole_cards', [])
        community = game_state.get('community_cards', [])
        if len(hole) < 2 or len(community) < 5:
            rank_tuple = (0, 0, 0, 0, 0, 0)
        else:
            rank_tuple, _, _ = evaluate_hand(hole, community[:5])
        if best_rank is None or rank_tuple > best_rank:
            best_rank = rank_tuple
            winners = [pid]
        elif rank_tuple == best_rank:
            winners.append(pid)
    return winners

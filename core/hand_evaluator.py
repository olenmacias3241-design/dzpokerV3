# dzpokerV3/core/hand_evaluator.py

from .cards import Card

# 牌型名称（与 hand_type_index 对应），用于前端显示
HAND_TYPE_NAMES = [
    "高牌", "一对", "两对", "三条", "顺子", "同花", "葫芦", "四条", "同花顺"
]


def _hand_type_index_for_combo(hand_combo):
    """根据 5 张牌判断牌型索引。"""
    ranks_in_combo = [c.rank for c in hand_combo]
    unique_ranks = set(ranks_in_combo)
    n_unique = len(unique_ranks)
    if n_unique == 5:
        return 0
    if n_unique == 4:
        return 1
    if n_unique == 3:
        for r in unique_ranks:
            if ranks_in_combo.count(r) == 3:
                return 3
        return 2
    if n_unique == 2:
        for r in unique_ranks:
            if ranks_in_combo.count(r) == 4:
                return 7   # 四条
        return 6   # 葫芦
    return 0


def evaluate_hand(hole_cards, community_cards):
    """
    Evaluates the best possible 5-card hand from a combination of 2 hole cards and 5 community cards.
    
    Args:
        hole_cards (list[Card]): A list of 2 Card objects.
        community_cards (list[Card]): A list of 5 Card objects.

    Returns:
        tuple(hand_rank, best_hand_cards, hand_type_index): 
            - hand_rank (int): A number representing the hand strength (higher is better).
            - best_hand_cards (list[Card]): The 5 cards that form the best hand.
            - hand_type_index (int): Index into HAND_TYPE_NAMES for display.
    """
    all_cards = hole_cards + community_cards
    if len(all_cards) < 5:
        return 0, [], 0

    rank_map = {r: i for i, r in enumerate('23456789TJQKA', 2)}
    import itertools

    best_score = -1
    best_hand_for_player = []
    best_type_index = 0
    
    for hand_combo in itertools.combinations(all_cards, 5):
        score = sum(rank_map[c.rank] for c in hand_combo)
        ranks_in_combo = [c.rank for c in hand_combo]
        unique_ranks = set(ranks_in_combo)
        if len(unique_ranks) == 4:
            score += 1000
        elif len(unique_ranks) == 3:
            is_three_of_a_kind = False
            for r in unique_ranks:
                if ranks_in_combo.count(r) == 3:
                    score += 3000
                    is_three_of_a_kind = True
                    break
            if not is_three_of_a_kind:
                score += 2000
        elif len(unique_ranks) == 2:
             is_four_of_a_kind = False
             for r in unique_ranks:
                 if ranks_in_combo.count(r) == 4:
                     score += 7000
                     is_four_of_a_kind = True
                     break
             if not is_four_of_a_kind:
                 score += 6000

        if score > best_score:
            best_score = score
            best_hand_for_player = list(hand_combo)
            best_type_index = _hand_type_index_for_combo(hand_combo)

    return best_score, best_hand_for_player, best_type_index


def get_hand_type_name(hole_cards, community_cards):
    """返回当前牌型中文名；牌不足 5 张时返回 None。仅给当前玩家用。"""
    if not hole_cards or len(hole_cards) < 2:
        return None
    community = list(community_cards) if community_cards else []
    if len(hole_cards) + len(community) < 5:
        return None
    _, _, idx = evaluate_hand(hole_cards, community[:5])
    return HAND_TYPE_NAMES[idx] if 0 <= idx < len(HAND_TYPE_NAMES) else "高牌"

def find_winners(game_state):
    """
    Finds the winner(s) of the hand from the players who went to showdown.

    Args:
        game_state (dict): The final game state.

    Returns:
        list[player_id]: A list of player IDs who won the pot.
    """
    showdown_players = {
        pid: p for pid, p in game_state['players'].items() 
        if p.get('is_in_hand') and not p.get('last_action') == 'FOLD'
    }

    if not showdown_players:
        # This case handles when all but one player folds
        active_players = [pid for pid, p in game_state['players'].items() if p.get('is_in_hand')]
        if len(active_players) == 1:
            return active_players
        return []

    if len(showdown_players) == 1:
        return list(showdown_players.keys())

    best_score = -1
    winners = []

    for player_id, player_state in showdown_players.items():
        hole_cards = player_state.get('hole_cards', [])
        community_cards = game_state.get('community_cards', [])
        
        score, hand, _ = evaluate_hand(hole_cards, community_cards)
        player_state['best_hand_score'] = score
        player_state['best_hand'] = hand

        if score > best_score:
            best_score = score
            winners = [player_id]
        elif score == best_score:
            # Tie-breaker logic (kickers) would be needed here.
            # For now, we just split the pot.
            winners.append(player_id)
            
    return winners

if __name__ == '__main__':
    # --- Test ---
    # Card needs to be imported if run directly
    # from cards import Card 
    
    # Mock game state for testing
    p1_cards = [Card('A', 'H'), Card('K', 'D')]
    p2_cards = [Card('Q', 'S'), Card('Q', 'C')]
    community = [Card('Q', 'H'), Card('J', 'H'), Card('2', 'S'), Card('7', 'D'), Card('3', 'C')]

    score1, hand1, _ = evaluate_hand(p1_cards, community)
    score2, hand2, _ = evaluate_hand(p2_cards, community)

    print(f"Player 1: {p1_cards} -> Score {score1}, Hand {hand1}")
    print(f"Player 2: {p2_cards} -> Score {score2}, Hand {hand2}")

    winner = "Player 1" if score1 > score2 else "Player 2"
    print(f"Winner is: {winner}")

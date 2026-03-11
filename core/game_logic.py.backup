# dzpokerV3/core/game_logic.py
#
# 德州扑克 (Texas Hold'em) 下注轮次规则（本模块严格遵循）：
#
# 【一局流程】
#   1) 先发 2 张手牌（底牌）→ 玩家下注一轮（底牌圈 Preflop）。
#   2) 发 3 张公共牌（翻牌 Flop）→ 大家再下一轮注（翻牌圈）。
#   3) 发 1 张转牌（Turn）→ 再下一轮注（转牌圈）。
#   4) 发 1 张河牌（River）→ 再下一轮注（河牌圈）。
#   5) 比牌（Showdown）→ 分池，牌局结束。
#
# 1) 座位与顺序
#    - 所有行动顺序按「座位顺时针」(player_order / seat 0,1,2,...)。
#    - 位置：Dealer(庄/BT) → Small Blind(SB) → Big Blind(BB) → UTG → ... 顺时针。
#
# 2) 底牌圈 (Preflop)
#    - 先下盲注：SB、BB 自动扣注。
#    - 第一个行动的人 = BB 下一位（UTG），即 (bb_pos + 1) % n。
#    - 最后行动的人 = BB（若无人加注，BB 可过牌）。
#
# 3) 翻牌/转牌/河牌圈 (Flop/Turn/River)
#    - 第一个行动的人 = 庄位(BT) 下一位，即 (dealer_pos + 1) % n 起第一个未弃牌且未 All-in 的玩家。
#
# 4) 下注轮结束条件
#    - 从「当前行动者」顺时针找下一个「未弃牌且未 All-in 且本街投入 < 当前跟注额」的玩家；若找到则轮到他行动。
#    - 若绕一圈回到「最后加注者」且所有人都已跟注到同一金额，则本街结束，发下一张牌或比牌。
#
# 5) current_player_id
#    - 始终表示「当前必须行动的一名玩家」；为 None 表示本街无人需行动（即将发牌或比牌）。
#
# 6) 示例（2 人）
#    - dealer_pos=0 → SB=座位1, BB=座位0 → 先行动=SB(座位1)，后行动=BB(座位0)。
# 示例（3 人）
#    - dealer_pos=0 → SB=1, BB=2 → 先行动=座位0(UTG)，然后座位1(SB)，最后座位2(BB)。

from enum import Enum, auto
from .cards import Deck, Card
from . import hand_evaluator

class GameStage(Enum):
    """ Defines the stages of a poker game. """
    PREFLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()
    SHOWDOWN = auto()
    ENDED = auto()

class PlayerAction(Enum):
    """ Defines the possible actions a player can take. """
    BET = auto()
    CALL = auto()
    RAISE = auto()
    CHECK = auto()
    FOLD = auto()
    ALL_IN = auto()

def handle_player_action(game_state, player_id, action, amount=0):
    """
    Handles a player's action and advances the game state.
    This is the core function for managing betting rounds.

    Args:
        game_state (dict): The current state of the game table.
        player_id (str): The ID of the player taking the action.
        action (PlayerAction): The action the player is taking.
        amount (int): The amount for bet/raise actions.

    Returns:
        tuple(dict, error_string): The updated game_state and an error message, if any.
    """
    current_player_id = game_state.get('current_player_id')
    if current_player_id != player_id:
        return game_state, f"现在不是玩家 {player_id} 的行动时间，轮到 {current_player_id}"

    player_state = game_state['players'].get(player_id)
    if not player_state:
        return game_state, f"玩家 {player_id} 不在牌局中"

    # --- Action Validation ---
    amount_to_call = game_state.get('amount_to_call', 0)
    can_check = amount_to_call == 0

    if action == PlayerAction.CHECK and not can_check:
        return game_state, "不能 Check，必须 Call, Raise 或 Fold"
    
    if action == PlayerAction.CALL and can_check:
        # If amount_to_call is 0, Call is effectively a Check.
        action = PlayerAction.CHECK

    # ALL_IN: 下注全部筹码（等同于 call 到全下或 bet 全下）
    if action == PlayerAction.ALL_IN:
        all_in_amt = player_state['stack']
        if all_in_amt <= 0:
            return game_state, "没有筹码可 All-in"
        to_put = min(amount_to_call - player_state.get('bet_this_round', 0), all_in_amt)
        if to_put < 0:
            to_put = 0
        if to_put > 0:
            player_state['stack'] -= to_put
            player_state['bet_this_round'] = player_state.get('bet_this_round', 0) + to_put
            player_state['total_bet_this_hand'] = player_state.get('total_bet_this_hand', 0) + to_put
            game_state['pot'] += to_put
            if player_state['bet_this_round'] > game_state.get('amount_to_call', 0):
                game_state['amount_to_call'] = player_state['bet_this_round']
                game_state['last_raiser_id'] = player_id
        player_state['last_action'] = 'ALL_IN'
        player_state['is_all_in'] = True
        next_player_id, round_over = find_next_player(game_state, player_id)
        if round_over:
            return advance_to_next_stage(game_state), None
        game_state['current_player_id'] = next_player_id
        return game_state, None

    # TODO: Add more validation for BET, RAISE, FOLD

    # --- State Update ---
    if action == PlayerAction.FOLD:
        player_state['is_active'] = False
        player_state['last_action'] = 'FOLD'
    
    elif action == PlayerAction.CHECK:
        player_state['last_action'] = 'CHECK'

    elif action == PlayerAction.CALL:
        call_amount = min(amount_to_call - player_state.get('bet_this_round', 0), player_state['stack'])
        player_state['stack'] -= call_amount
        player_state['bet_this_round'] = player_state.get('bet_this_round', 0) + call_amount
        player_state['total_bet_this_hand'] = player_state.get('total_bet_this_hand', 0) + call_amount
        game_state['pot'] += call_amount
        player_state['last_action'] = 'CALL'
        if player_state['stack'] == 0:
            player_state['is_all_in'] = True

    elif action == PlayerAction.BET:
        if amount <= 0 or amount > player_state['stack']:
            return game_state, "下注金额无效"
        player_state['stack'] -= amount
        player_state['bet_this_round'] = amount
        player_state['total_bet_this_hand'] = player_state.get('total_bet_this_hand', 0) + amount
        game_state['pot'] += amount
        game_state['amount_to_call'] = amount
        player_state['last_action'] = 'BET'
        game_state['last_raiser_id'] = player_id
        if player_state['stack'] == 0:
            player_state['is_all_in'] = True

    elif action == PlayerAction.RAISE:
        # Basic raise validation
        min_raise = game_state.get('last_raise_amount', game_state.get('bb', 0))
        if amount < min_raise:
            return game_state, f"加注金额不能小于 {min_raise}"
        
        total_bet = amount_to_call + amount
        if total_bet > player_state['stack']:
             return game_state, "加注金额超过你的筹码"

        player_state['stack'] -= total_bet
        player_state['bet_this_round'] = player_state.get('bet_this_round', 0) + total_bet
        player_state['total_bet_this_hand'] = player_state.get('total_bet_this_hand', 0) + total_bet
        game_state['pot'] += total_bet
        game_state['amount_to_call'] = player_state['bet_this_round']
        game_state['last_raise_amount'] = amount
        player_state['last_action'] = 'RAISE'
        game_state['last_raiser_id'] = player_id
        if player_state['stack'] == 0:
            player_state['is_all_in'] = True

    # --- Determine Next Player and End of Round ---
    next_player_id, round_over = find_next_player(game_state, player_id)

    if round_over:
        print(f"Betting round is over. Last actor was {player_id}.")
        return advance_to_next_stage(game_state), None
    else:
        game_state['current_player_id'] = next_player_id
        print(f"Action moves to player {next_player_id}")

    return game_state, None


def find_next_player(game_state, last_actor_id):
    """
    从 last_actor 起顺时针找「下一个需要行动」的玩家（未弃牌、未 All-in 且本街投入 < amount_to_call）。
    若下一个轮到的是 last_raiser 且所有人都已跟注，则本街结束，返回 (None, True)。
    顺序严格按 game_state['player_order']（座位顺序）。
    """
    # 轮次顺序 = 座位顺序（player_order 在 start_game 时按 seated 写入）
    player_order = game_state.get('player_order')
    if player_order:
        player_ids = [p for p in player_order if p in game_state['players']]
    else:
        player_ids = list(game_state['players'].keys())
    num_players = len(player_ids)

    # 还能行动的人：未弃牌且未 All-in
    active_players_in_hand = [
        pid for pid, p in game_state['players'].items() if p.get('is_in_hand') and not p.get('is_all_in')
    ]

    if len(active_players_in_hand) <= 1:
        return None, True

    last_raiser = game_state.get('last_raiser_id')
    max_bet = game_state.get('amount_to_call', 0)

    # 从 last_actor 的下一位开始，顺时针遍历（按 player_ids 顺序）
    last_actor_index = player_ids.index(last_actor_id)
    for i in range(1, num_players + 1):
        next_player_id = player_ids[(last_actor_index + i) % num_players]
        player_state = game_state['players'][next_player_id]

        if not player_state.get('is_in_hand') or player_state.get('is_all_in'):
            continue

        # 本街投入不足跟注额 → 必须行动，轮到他
        if player_state.get('bet_this_round', 0) < max_bet:
            return next_player_id, False

        # 已跟齐，且已经回到 last_raiser → 本街结束
        if last_raiser and next_player_id == last_raiser:
            return None, True

    return None, True


def advance_to_next_stage(game_state):
    """
    Advances the game to the next stage (e.g., from Pre-flop to Flop).
    Deals community cards and resets betting for the new round.
    """
    current_stage = game_state.get('stage')
    
    stage_progression = {
        GameStage.PREFLOP: GameStage.FLOP,
        GameStage.FLOP: GameStage.TURN,
        GameStage.TURN: GameStage.RIVER,
        GameStage.RIVER: GameStage.SHOWDOWN,
    }

    next_stage = stage_progression.get(current_stage)

    if not next_stage:
        print(f"Game is already in or past the final betting round: {current_stage.name}")
        game_state['stage'] = GameStage.ENDED
        # TODO: Implement showdown logic here
        return game_state

    game_state['stage'] = next_stage
    print(f"Advancing from {current_stage.name} to {next_stage.name}")

    # --- Deal Community Cards ---
    if next_stage == GameStage.FLOP:
        flop_cards = game_state['deck'].draw(3)
        game_state['community_cards'].extend(flop_cards)
        print(f"Dealt flop: {flop_cards}")
    elif next_stage == GameStage.TURN:
        turn_card = game_state['deck'].draw(1)
        game_state['community_cards'].append(turn_card)
        print(f"Dealt turn: {turn_card}")
    elif next_stage == GameStage.RIVER:
        river_card = game_state['deck'].draw(1)
        game_state['community_cards'].append(river_card)
        print(f"Dealt river: {river_card}")
    elif next_stage == GameStage.SHOWDOWN:
        print("All betting rounds are over. Proceeding to showdown.")
        
        # 使用 pot_manager 计算边池和分配
        from . import pot_manager
        
        # 准备玩家状态（包含 total_bet_this_hand）
        players_for_pot = {}
        for pid, pstate in game_state['players'].items():
            players_for_pot[pid] = {
                'total_bet_this_hand': pstate.get('total_bet_this_hand', 0),
                'is_folded': not pstate.get('is_in_hand', False) or not pstate.get('is_active', False)
            }
        
        # 计算边池
        pots = pot_manager.calculate_side_pots(players_for_pot)
        
        # 评估所有玩家的手牌
        hand_ranks = {}
        for pid, pstate in game_state['players'].items():
            if pstate.get('is_in_hand') and pstate.get('is_active'):
                hole_cards = pstate.get('hole_cards', [])
                community = game_state.get('community_cards', [])
                if len(hole_cards) == 2 and len(community) >= 3:
                    rank, _, _ = hand_evaluator.evaluate_hand(hole_cards, community)
                    hand_ranks[pid] = rank
        
        # 分配奖金
        winnings = pot_manager.distribute_pots(pots, hand_ranks, players_for_pot)
        
        for pid, amount in winnings.items():
            game_state['players'][pid]['stack'] += amount
            print(f"Player {pid} wins {amount}")
        
        game_state['pot'] = 0
        game_state['stage'] = GameStage.ENDED
        game_state['winners'] = list(winnings.keys())
        game_state['pots'] = pots
        game_state['last_hand_winnings'] = dict(winnings)
        return game_state


    # Reset betting variables for the new round
    game_state['amount_to_call'] = 0
    game_state['last_raise_amount'] = 0
    game_state['last_raiser_id'] = None
    for player_id in game_state['players']:
        player_state = game_state['players'][player_id]
        if player_state.get('is_in_hand'):
            player_state['bet_this_round'] = 0
            # We can also reset their last action
            # player_state['last_action'] = None

    game_state['last_raiser_id'] = None
    for player_id, player_state in game_state['players'].items():
        if player_state.get('is_active'):
            player_state['bet_this_round'] = 0
            player_state['last_action'] = None

    # Reset 'current_player_id' to the first active player after the button — 翻牌/转/河从庄位下家开始
    dealer_pos = game_state.get('dealer_button_position', -1)
    player_order = game_state.get('player_order')
    if player_order:
        player_ids = [p for p in player_order if p in game_state['players']]
    else:
        player_ids = list(game_state['players'].keys())
    num_players = len(player_ids)
    
    first_active_player = None
    for i in range(1, num_players + 1):
        player_id = player_ids[(dealer_pos + i) % num_players]
        player_state = game_state['players'][player_id]
        if player_state.get('is_in_hand') and not player_state.get('is_all_in'):
            first_active_player = player_id
            break

    game_state['current_player_id'] = first_active_player

    print(f"New round starts with player: {first_active_player}")
    return game_state


def run_ai_turns(game_state):
    """
    Simple AI loop for the new engine. While current_player_id refers to a bot
    and the round is not over, choose a basic action and apply it via
    handle_player_action.

    Returns:
        (game_state, actions): Updated game state and list of (player_id, action_name, amount_or_None, stage_name)
    """
    import random
    def _stage_name():
        s = game_state.get('stage')
        return s.name if s else 'PREFLOP'

    actions = []
    while True:
        cur = game_state.get('current_player_id')
        if cur is None:
            break
        ps = game_state['players'].get(cur)
        if not ps:
            break
        if not ps.get('is_bot'):
            break
        # Decide action
        # If already all-in or not in hand, skip
        if not ps.get('is_in_hand', True) or ps.get('is_all_in', False):
            next_pid, over = find_next_player(game_state, cur)
            if over:
                game_state = advance_to_next_stage(game_state)
                break
            game_state['current_player_id'] = next_pid
            continue
        call_amt = game_state.get('amount_to_call', 0)
        stack = ps.get('stack', 0)
        # If large call (>50% stack) sometimes fold
        if call_amt > 0 and call_amt > stack * 0.5 and random.random() < 0.25:
            stage_before = _stage_name()
            game_state, err = handle_player_action(game_state, cur, PlayerAction.FOLD)
            if err:
                break
            actions.append((cur, 'FOLD', None, stage_before))
            continue
        # If nothing to call, sometimes bet small, else check/call
        if call_amt == 0:
            if random.random() < 0.6:
                stage_before = _stage_name()
                game_state, err = handle_player_action(game_state, cur, PlayerAction.CHECK)
                if err:
                    break
                actions.append((cur, 'CHECK', None, stage_before))
            else:
                bet_amt = min(game_state.get('bb', 0) * 2, stack)
                if bet_amt <= 0:
                    stage_before = _stage_name()
                    game_state, err = handle_player_action(game_state, cur, PlayerAction.CHECK)
                    if err:
                        break
                    actions.append((cur, 'CHECK', None, stage_before))
                else:
                    stage_before = _stage_name()
                    game_state, err = handle_player_action(game_state, cur, PlayerAction.BET, bet_amt)
                    if err:
                        break
                    actions.append((cur, 'BET', int(bet_amt), stage_before))
            continue
        else:
            # There is an amount to call
            if stack <= call_amt:
                stage_before = _stage_name()
                game_state, err = handle_player_action(game_state, cur, PlayerAction.CALL)
                if err:
                    break
                actions.append((cur, 'CALL', int(call_amt), stage_before))
            elif random.random() < 0.5:
                stage_before = _stage_name()
                game_state, err = handle_player_action(game_state, cur, PlayerAction.CALL)
                if err:
                    break
                actions.append((cur, 'CALL', int(call_amt), stage_before))
            else:
                raise_amt = min(int(game_state.get('bb', 0) * 2), stack - call_amt)
                if raise_amt <= 0:
                    stage_before = _stage_name()
                    game_state, err = handle_player_action(game_state, cur, PlayerAction.CALL)
                    if err:
                        break
                    actions.append((cur, 'CALL', int(call_amt), stage_before))
                else:
                    stage_before = _stage_name()
                    game_state, err = handle_player_action(game_state, cur, PlayerAction.RAISE, raise_amt)
                    if err:
                        break
                    actions.append((cur, 'RAISE', int(raise_amt), stage_before))
            continue
    return (game_state, actions)


def start_new_hand(game_state):
    """
    新一局开始：洗牌、发底牌、下盲注、设定第一个行动者。
    - active_player_ids：按座位顺序的在局玩家列表（与 player_order 一致）。
    - dealer_pos：庄位在该列表中的下标；SB/BB/UTG 均由 dealer_pos 推导。
    """
    print("--- Starting a new hand ---")
    game_state['deck'] = Deck()
    game_state['community_cards'] = []

    # 在局玩家列表（顺序 = 座位顺序，与 player_order 一致）
    active_player_ids = [pid for pid, p in game_state['players'].items() if p.get('is_in_hand')]
    num_players = len(active_player_ids)

    for player_id in active_player_ids:
        hole_cards = game_state['deck'].draw(2)
        game_state['players'][player_id]['hole_cards'] = hole_cards
        game_state['players'][player_id]['total_bet_this_hand'] = 0
        game_state['players'][player_id]['is_all_in'] = False
        print(f"Dealt {hole_cards} to player {player_id}")

    game_state['stage'] = GameStage.PREFLOP

    bb_amount = game_state.get('bb', 0)
    sb_amount = game_state.get('sb', 0)
    dealer_pos = game_state.get('dealer_button_position', 0)
    dealer_pos = min(dealer_pos, num_players - 1) if num_players else 0

    sb_pos = (dealer_pos + 1) % num_players
    bb_pos = (dealer_pos + 2) % num_players
    
    sb_player_id = active_player_ids[sb_pos]
    bb_player_id = active_player_ids[bb_pos]
    
    game_state['sb_player_id'] = sb_player_id
    game_state['bb_player_id'] = bb_player_id
    
    # Post Small Blind
    sb_player_state = game_state['players'][sb_player_id]
    actual_sb = min(sb_amount, sb_player_state['stack'])
    sb_player_state['stack'] -= actual_sb
    sb_player_state['bet_this_round'] = actual_sb
    sb_player_state['total_bet_this_hand'] = actual_sb
    game_state['pot'] += actual_sb
    if sb_player_state['stack'] == 0:
        sb_player_state['is_all_in'] = True
    print(f"Player {sb_player_id} posts small blind of {actual_sb}")

    # Post Big Blind
    bb_player_state = game_state['players'][bb_player_id]
    actual_bb = min(bb_amount, bb_player_state['stack'])
    bb_player_state['stack'] -= actual_bb
    bb_player_state['bet_this_round'] = actual_bb
    bb_player_state['total_bet_this_hand'] = actual_bb
    game_state['pot'] += actual_bb
    if bb_player_state['stack'] == 0:
        bb_player_state['is_all_in'] = True
    print(f"Player {bb_player_id} posts big blind of {actual_bb}")

    game_state['amount_to_call'] = actual_bb
    
    # First player to act is after the big blind (UTG) — 底牌圈从 BB 下家开始
    utg_pos = (bb_pos + 1) % num_players
    first_to_act_id = active_player_ids[utg_pos]
    game_state['current_player_id'] = first_to_act_id
    game_state['last_raiser_id'] = bb_player_id # The BB is the initial "raise"
    
    return game_state


if __name__ == '__main__':
    # Example usage for testing purposes
    mock_game_state = {
        'stage': GameStage.PREFLOP,
        'pot': 50,
        'players': {
            'player1': {'stack': 1000, 'is_active': True},
            'player2': {'stack': 950, 'is_active': True},
        },
        'current_player_id': 'player1',
    }

    # Simulate a player action
    updated_state = handle_player_action(mock_game_state, 'player1', PlayerAction.BET, 100)
    
    # Simulate advancing the stage
    updated_state = advance_to_next_stage(updated_state)

    print("\\nFinal game state (mock):", updated_state)

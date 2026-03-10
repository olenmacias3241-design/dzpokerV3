# dzpokerV3/core/replay.py
# 牌局回放：从 hand_actions 重建游戏状态

from . import game_logic

def replay_hand(hand_actions, initial_state):
    """
    从动作记录回放一手牌。
    
    Args:
        hand_actions: list of {'user_id': str, 'action_type': str, 'amount': int}
        initial_state: 初始游戏状态（包含玩家、盲注等）
    
    Returns:
        final_state: 回放后的游戏状态
    """
    state = initial_state.copy()
    
    for action_record in hand_actions:
        user_id = action_record['user_id']
        action_type = action_record['action_type']
        amount = action_record.get('amount', 0)
        
        # 跳过特殊标记（如 AI_TICK）
        if action_type in ('AI_TICK', 'SYSTEM'):
            continue
        
        try:
            action_enum = game_logic.PlayerAction[action_type.upper()]
            state, error = game_logic.handle_player_action(state, user_id, action_enum, amount)
            if error:
                print(f"Replay error at action {action_type} by {user_id}: {error}")
                break
        except KeyError:
            print(f"Unknown action type: {action_type}")
            continue
    
    return state


def load_hand_from_db(db, hand_id):
    """
    从数据库加载一手牌的完整信息并回放。
    
    Args:
        db: 数据库会话
        hand_id: hand 表的 ID
    
    Returns:
        game_state: 回放后的游戏状态，如果失败返回 None
    """
    from database import Hand, HandAction, GameTable
    
    hand = db.query(Hand).filter(Hand.id == hand_id).first()
    if not hand:
        return None
    
    table = db.query(GameTable).filter(GameTable.id == hand.table_id).first()
    if not table:
        return None
    
    # 获取该手牌的所有动作（按时间排序）
    actions = db.query(HandAction).filter(
        HandAction.hand_id == hand_id
    ).order_by(HandAction.timestamp).all()
    
    # 构建初始状态（需要从 table_seats 获取玩家信息）
    # 这里简化处理，实际应该从 table_seats 重建
    initial_state = {
        'sb': table.small_blind,
        'bb': table.big_blind,
        'pot': 0,
        'players': {},  # 需要从 table_seats 填充
        'stage': game_logic.GameStage.PREFLOP,
        'community_cards': [],
        'amount_to_call': 0,
    }
    
    # 转换动作记录格式
    action_list = [
        {'user_id': a.user_id, 'action_type': a.action_type, 'amount': a.amount}
        for a in actions
    ]
    
    # 回放
    final_state = replay_hand(action_list, initial_state)
    return final_state

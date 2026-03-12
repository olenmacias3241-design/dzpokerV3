# dzpokerV3/core/bot_ai.py - 智能机器人决策系统

import random
from .hand_evaluator import evaluate_hand

class BotPersonality:
    """机器人性格类型"""
    TIGHT_PASSIVE = "tight_passive"      # 紧凶：只玩好牌，很少诈唬
    LOOSE_AGGRESSIVE = "loose_aggressive" # 松凶：玩很多牌，经常加注
    TIGHT_AGGRESSIVE = "tight_aggressive" # 紧凶：只玩好牌，经常加注
    LOOSE_PASSIVE = "loose_passive"       # 松弱：玩很多牌，很少加注


class SmartBotAI:
    """
    智能机器人 AI
    
    特点：
    1. 根据手牌强度做决策
    2. 考虑位置优势
    3. 根据底池大小调整下注
    4. 有一定的诈唬概率
    5. 模拟人类的思考时间
    """
    
    def __init__(self, personality=BotPersonality.TIGHT_AGGRESSIVE):
        self.personality = personality
        self.aggression = self._get_aggression()
        self.tightness = self._get_tightness()
        self.bluff_frequency = self._get_bluff_frequency()
    
    def _get_aggression(self):
        """获取激进程度 (0-1)"""
        if "aggressive" in self.personality:
            return random.uniform(0.6, 0.9)
        else:
            return random.uniform(0.2, 0.4)
    
    def _get_tightness(self):
        """获取紧度 (0-1，越高越紧)"""
        if "tight" in self.personality:
            return random.uniform(0.6, 0.8)
        else:
            return random.uniform(0.3, 0.5)
    
    def _get_bluff_frequency(self):
        """获取诈唬频率 (0-1)"""
        if "aggressive" in self.personality:
            return random.uniform(0.15, 0.25)
        else:
            return random.uniform(0.05, 0.10)
    
    def evaluate_hand_strength(self, hole_cards, community_cards):
        """
        评估手牌强度 (0-1)
        
        0.0-0.2: 垃圾牌
        0.2-0.4: 弱牌
        0.4-0.6: 中等牌
        0.6-0.8: 强牌
        0.8-1.0: 超强牌
        """
        if not hole_cards or len(hole_cards) < 2:
            return 0.0
        
        # Preflop: 只看底牌
        if not community_cards:
            return self._evaluate_preflop(hole_cards)
        
        # Postflop: 评估当前牌型
        all_cards = hole_cards + community_cards
        if len(all_cards) < 5:
            # 不足5张，简单评估
            return self._evaluate_preflop(hole_cards) * 0.8
        
        # 使用 hand_evaluator 评估（传入底牌 + 公共牌，返回 rank 元组）
        try:
            rank_tuple, _ = evaluate_hand(hole_cards, community_cards[:5])
            # rank_tuple[0] = hand level 0-9（高牌到皇家同花顺）
            level = rank_tuple[0] if isinstance(rank_tuple, tuple) else 0
            return (level + 1) / 10.0
        except Exception:
            return 0.5
    
    def _evaluate_preflop(self, hole_cards):
        """评估翻牌前手牌强度"""
        if len(hole_cards) != 2:
            return 0.0
        
        c1, c2 = hole_cards[0], hole_cards[1]
        
        # 提取点数和花色
        rank1 = self._rank_value(c1[0])
        rank2 = self._rank_value(c2[0])
        suited = c1[1] == c2[1]
        
        # 对子
        if rank1 == rank2:
            # AA, KK, QQ = 超强
            if rank1 >= 12:
                return 0.95
            # JJ, TT = 强
            elif rank1 >= 9:
                return 0.75
            # 99-22 = 中等
            else:
                return 0.5 + (rank1 / 20.0)
        
        # 高牌
        high = max(rank1, rank2)
        low = min(rank1, rank2)
        gap = high - low
        
        # AK, AQ = 超强
        if high == 12 and low >= 11:
            return 0.85 if suited else 0.75
        
        # AJ, AT, KQ = 强
        if (high == 12 and low >= 9) or (high == 11 and low >= 10):
            return 0.70 if suited else 0.60
        
        # 同花连牌
        if suited and gap <= 1:
            return 0.65
        
        # 同花有间隔
        if suited and gap <= 3:
            return 0.55
        
        # 高牌连牌
        if gap <= 1 and high >= 9:
            return 0.50
        
        # 一张高牌
        if high >= 10:
            return 0.35 + (high / 30.0)
        
        # 垃圾牌
        return 0.15 + (high / 40.0)
    
    def _rank_value(self, rank_char):
        """将牌面转换为数值 (2-14)"""
        rank_map = {
            '2': 0, '3': 1, '4': 2, '5': 3, '6': 4,
            '7': 5, '8': 6, '9': 7, 'T': 8, 'J': 9,
            'Q': 10, 'K': 11, 'A': 12
        }
        return rank_map.get(rank_char, 0)
    
    def decide_action(self, game_state, player_id):
        """
        决策行动
        
        返回: (action, amount)
        action: "fold", "check", "call", "bet", "raise", "all_in"
        amount: 下注金额
        """
        player_state = game_state['players'].get(player_id, {})
        hole_cards = player_state.get('hole_cards', [])
        community_cards = game_state.get('community_cards', [])
        
        # 评估手牌强度
        hand_strength = self.evaluate_hand_strength(hole_cards, community_cards)
        
        # 获取游戏信息
        amount_to_call = game_state.get('amount_to_call', 0)
        pot = game_state.get('pot', 0)
        bb = game_state.get('bb', 10)
        player_stack = player_state.get('stack', 0)
        bet_this_round = player_state.get('bet_this_round', 0)
        
        # 计算底池赔率
        if amount_to_call > 0:
            pot_odds = amount_to_call / (pot + amount_to_call)
        else:
            pot_odds = 0
        
        # 是否可以过牌
        can_check = amount_to_call == 0
        
        # 决策逻辑
        if can_check:
            return self._decide_when_can_check(hand_strength, pot, bb, player_stack)
        else:
            return self._decide_when_must_call(
                hand_strength, amount_to_call, pot, bb, 
                player_stack, bet_this_round, pot_odds
            )
    
    def _decide_when_can_check(self, hand_strength, pot, bb, stack):
        """可以过牌时的决策"""
        
        # 超强牌 (0.8+): 大概率下注/加注
        if hand_strength >= 0.8:
            if random.random() < 0.85:
                # 下注 0.5-1.0 倍底池
                bet_size = int(pot * random.uniform(0.5, 1.0))
                bet_size = max(bb, min(bet_size, stack))
                return "bet", bet_size
            else:
                # 慢打（slow play）
                return "check", 0
        
        # 强牌 (0.6-0.8): 经常下注
        elif hand_strength >= 0.6:
            if random.random() < 0.70:
                bet_size = int(pot * random.uniform(0.4, 0.7))
                bet_size = max(bb, min(bet_size, stack))
                return "bet", bet_size
            else:
                return "check", 0
        
        # 中等牌 (0.4-0.6): 有时下注（诈唬）
        elif hand_strength >= 0.4:
            if random.random() < self.bluff_frequency * 2:
                bet_size = int(pot * random.uniform(0.3, 0.5))
                bet_size = max(bb, min(bet_size, stack))
                return "bet", bet_size
            else:
                return "check", 0
        
        # 弱牌/垃圾牌: 大部分过牌，偶尔诈唬
        else:
            if random.random() < self.bluff_frequency:
                bet_size = int(pot * random.uniform(0.5, 0.8))
                bet_size = max(bb, min(bet_size, stack))
                return "bet", bet_size
            else:
                return "check", 0
    
    def _decide_when_must_call(self, hand_strength, to_call, pot, bb, stack, bet_this_round, pot_odds):
        """需要跟注时的决策"""
        
        # 超强牌 (0.8+): 几乎总是加注或 All-in
        if hand_strength >= 0.8:
            if random.random() < 0.15:
                # 偶尔慢打
                return "call", 0
            elif stack <= to_call * 3:
                # 筹码不多，直接 All-in
                return "all_in", 0
            else:
                # 加注 2-3 倍
                raise_to = to_call + int(pot * random.uniform(0.5, 1.0))
                raise_to = min(raise_to, stack)
                return "raise", raise_to
        
        # 强牌 (0.6-0.8): 经常加注
        elif hand_strength >= 0.6:
            if random.random() < 0.60:
                if stack <= to_call * 2:
                    return "all_in", 0
                else:
                    raise_to = to_call + int(pot * random.uniform(0.4, 0.7))
                    raise_to = min(raise_to, stack)
                    return "raise", raise_to
            else:
                return "call", 0
        
        # 中等牌 (0.4-0.6): 根据底池赔率决定
        elif hand_strength >= 0.4:
            # 如果底池赔率好，跟注
            if pot_odds < 0.3:
                return "call", 0
            # 偶尔加注（诈唬）
            elif random.random() < self.bluff_frequency:
                raise_to = to_call + int(pot * random.uniform(0.3, 0.5))
                raise_to = min(raise_to, stack)
                return "raise", raise_to
            # 否则弃牌
            else:
                return "fold", 0
        
        # 弱牌 (0.2-0.4): 大部分弃牌，底池赔率极好时跟注
        elif hand_strength >= 0.2:
            if pot_odds < 0.15:
                return "call", 0
            else:
                return "fold", 0
        
        # 垃圾牌: 几乎总是弃牌，极少诈唬
        else:
            if random.random() < self.bluff_frequency * 0.5:
                # 极少数情况下诈唬 All-in
                return "all_in", 0
            else:
                return "fold", 0
    
    def get_think_time(self, action, hand_strength):
        """
        获取思考时间（秒）
        
        模拟人类：
        - 简单决策（check, fold）: 0.5-1.5秒
        - 中等决策（call）: 1.0-2.5秒
        - 复杂决策（bet, raise, all-in）: 1.5-3.5秒
        - 困难决策（弱牌但要跟注/加注）: 2.0-4.0秒
        """
        base_time = {
            "check": (0.5, 1.5),
            "fold": (0.5, 1.5),
            "call": (1.0, 2.5),
            "bet": (1.5, 3.0),
            "raise": (1.5, 3.5),
            "all_in": (2.0, 4.0),
        }.get(action, (1.0, 2.0))
        
        # 如果是弱牌但要下注/加注（诈唬），增加思考时间
        if action in ["bet", "raise", "all_in"] and hand_strength < 0.4:
            base_time = (base_time[0] + 0.5, base_time[1] + 1.0)
        
        return random.uniform(*base_time)


# 创建不同性格的机器人
def create_bot_ai(personality=None):
    """创建一个机器人 AI"""
    if personality is None:
        # 随机选择性格
        personalities = [
            BotPersonality.TIGHT_PASSIVE,
            BotPersonality.LOOSE_AGGRESSIVE,
            BotPersonality.TIGHT_AGGRESSIVE,
            BotPersonality.LOOSE_PASSIVE,
        ]
        personality = random.choice(personalities)
    
    return SmartBotAI(personality)

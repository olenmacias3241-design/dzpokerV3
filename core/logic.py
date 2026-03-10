# dzpokerV3/core/logic.py
# Version 6 - Full betting (blinds, fold/check/call/bet/raise), side pots, wheel straight
import random
from collections import Counter
from itertools import combinations

# --- Hand Evaluation (with wheel straight A-2-3-4-5) ---

def _rank_to_int(rank):
    """Converts card rank string to an integer for comparison (A=14 high, A=1 for wheel)."""
    if rank.isdigit():
        return int(rank)
    return {'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}[rank]

def evaluate_hand(seven_cards):
    """
    Evaluates the best 5-card hand from 7 cards.
    Returns a tuple: (hand_type, primary_rank, ...kickers).
    Hand types: 8=Straight Flush, 7=Four of a Kind, 6=Full House, 5=Flush,
                4=Straight, 3=Three of a Kind, 2=Two Pair, 1=One Pair, 0=High Card
    """
    all_5 = list(combinations(seven_cards, 5))
    best = (0,)
    for hand in all_5:
        r = _get_hand_rank(hand)
        if r > best:
            best = r
    return best

def _get_hand_rank(hand):
    """Rank of a 5-card hand. Handles wheel (A-2-3-4-5)."""
    ranks = sorted([_rank_to_int(c.rank) for c in hand], reverse=True)
    suits = [c.suit for c in hand]
    is_flush = len(set(suits)) == 1

    # Straight: normal and wheel (A-2-3-4-5)
    ranks_asc = sorted(ranks)
    is_straight_norm = all(ranks_asc[i] == ranks_asc[i + 1] - 1 for i in range(4))
    is_wheel = ranks_asc == [2, 3, 4, 5, 14]  # A plays as 1
    is_straight = is_straight_norm or is_wheel
    straight_high = ranks_asc[4] if is_straight_norm else (5 if is_wheel else 0)

    if is_straight and is_flush:
        return (8, straight_high)

    counts = Counter(ranks)
    counts_sorted = sorted(counts.items(), key=lambda x: (-x[1], -x[0]))

    if counts_sorted[0][1] == 4:
        return (7, counts_sorted[0][0], counts_sorted[1][0])
    if counts_sorted[0][1] == 3 and counts_sorted[1][1] == 2:
        return (6, counts_sorted[0][0], counts_sorted[1][0])
    if is_flush:
        return (5,) + tuple(ranks)
    if is_straight:
        return (4, straight_high)
    if counts_sorted[0][1] == 3:
        kickers = tuple(r for r in ranks if r != counts_sorted[0][0])
        return (3, counts_sorted[0][0]) + kickers
    if counts_sorted[0][1] == 2 and counts_sorted[1][1] == 2:
        return (2, counts_sorted[0][0], counts_sorted[1][0], counts_sorted[2][0])
    if counts_sorted[0][1] == 2:
        kickers = tuple(r for r in ranks if r != counts_sorted[0][0])
        return (1, counts_sorted[0][0]) + kickers
    return (0,) + tuple(ranks)

# --- Card, Deck, Player ---
class Card:
    def __init__(self, suit, rank):
        self.suit, self.rank = suit, rank
    def __str__(self):
        return f"{self.suit}{self.rank}"
    def to_dict(self):
        return {'suit': self.suit, 'rank': self.rank}

class Deck:
    def __init__(self):
        self.cards = self._generate_deck()
    def _generate_deck(self):
        s = ["♥", "♦", "♣", "♠"]
        r = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
        return [Card(suit, rank) for suit in s for rank in r]
    def shuffle(self):
        random.shuffle(self.cards)
    def deal(self, n):
        return [self.cards.pop() for _ in range(n)] if len(self.cards) >= n else []
    def burn(self):
        if self.cards:
            self.cards.pop()

class Player:
    def __init__(self, name, chips, is_human=False):
        self.name = name
        self.chips = chips
        self.is_human = is_human
        self.hand = []
        self.current_bet = 0      # amount put in current street
        self.total_bet_this_hand = 0  # total put in pot this hand
        self.has_acted = False
        self.has_folded = False
        self.is_all_in = False
        self.sid = None  # WebSocket session id (optional)

    def receive_cards(self, cards):
        self.hand.extend(cards)

    def reset_for_new_round(self):
        self.hand = []
        self.current_bet = 0
        self.total_bet_this_hand = 0
        self.has_acted = False
        self.has_folded = False
        self.is_all_in = False

    def to_dict(self, hide_cards=False):
        d = {
            'name': self.name,
            'chips': self.chips,
            'current_bet': self.current_bet,
            'total_bet_this_hand': self.total_bet_this_hand,
            'has_folded': self.has_folded,
            'is_all_in': self.is_all_in,
        }
        if hide_cards:
            d['hand'] = []
        else:
            d['hand'] = [c.to_dict() for c in self.hand]
        return d

# --- Game ---
class Game:
    def __init__(self, small_blind=5, big_blind=10, insurance_enabled=False):
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.insurance_enabled = bool(insurance_enabled)
        self.players = []
        self.deck = None
        self.pot = 0
        self.side_pots = []  # list of {'amount': n, 'eligible': [player indices]}
        self.community_cards = []
        self.stage = None  # preflop, flop, turn, river, showdown
        self.is_running = False
        self.current_player_idx = 0
        self.dealer_idx = 0
        self.sb_idx = 0
        self.bb_idx = 0
        self.last_raise_amount = 0  # min raise size for current street
        self.last_action_description = "等待新游戏开始"
        self.winner_info = None
        self.winner_idx = None
        self.hand_id = 0
        import time
        self._emotes = {}  # player_idx -> {'emote': str, 'at': timestamp}
        self._emote_ttl = 5  # seconds
        self.pending_street = None  # 'flop'|'turn'|'river'|'showdown'
        self._showdown_reveal = False  # 仅多人比牌时为 True，弃牌导致一人赢时不亮对方牌
        self.pending_insurance = None  # {'leading_idx', 'equity', 'all_in_indices'} 领先玩家可买保险
        self.insurance_purchase = None  # {'player_idx', 'premium', 'payout_if_lose'}

    def add_player(self, player):
        self.players.append(player)

    def _post_blinds(self):
        n = len(self.players)
        self.sb_idx = self.dealer_idx
        self.bb_idx = (self.dealer_idx + 1) % n
        sb_amt = min(self.small_blind, self.players[self.sb_idx].chips)
        bb_amt = min(self.big_blind, self.players[self.bb_idx].chips)
        self.players[self.sb_idx].chips -= sb_amt
        self.players[self.sb_idx].current_bet = sb_amt
        self.players[self.sb_idx].total_bet_this_hand = sb_amt
        self.players[self.sb_idx].is_all_in = self.players[self.sb_idx].chips == 0
        self.players[self.bb_idx].chips -= bb_amt
        self.players[self.bb_idx].current_bet = bb_amt
        self.players[self.bb_idx].total_bet_this_hand = bb_amt
        self.players[self.bb_idx].is_all_in = self.players[self.bb_idx].chips == 0
        self.pot = sb_amt + bb_amt
        self.last_raise_amount = self.big_blind
        # Preflop: first to act is left of BB = (bb_idx + 1) % n
        self.current_player_idx = (self.bb_idx + 1) % n
        # If only 2 players, SB acts first preflop
        if n == 2:
            self.current_player_idx = self.sb_idx

    def _max_bet_this_street(self):
        return max(p.current_bet for i, p in enumerate(self.players) if not p.has_folded)

    def _call_amount(self, player_idx):
        p = self.players[player_idx]
        return self._max_bet_this_street() - p.current_bet

    def _min_raise_to(self):
        return self._max_bet_this_street() + max(self.last_raise_amount, self.big_blind)

    def _betting_round_complete(self):
        active = [i for i, p in enumerate(self.players) if not p.has_folded and not p.is_all_in]
        if not active:
            return True
        max_bet = self._max_bet_this_street()
        for i in active:
            if self.players[i].current_bet < max_bet:
                return False
        return all(self.players[i].has_acted for i in active)

    def _compute_equity(self, all_in_indices):
        """Monte Carlo 计算 All-in 玩家的胜率。返回 (leading_idx, equities_dict)。"""
        n_community = len(self.community_cards)
        need = 5 - n_community
        if need <= 0:
            # 已有 5 张公共牌，直接比牌算赢家
            best_rank = [(-1,)] * len(self.players)
            for i in all_in_indices:
                best_rank[i] = evaluate_hand(self.players[i].hand + self.community_cards)
            best = max(best_rank[i] for i in all_in_indices)
            winners = [i for i in all_in_indices if best_rank[i] == best]
            eq = {}
            for i in all_in_indices:
                eq[i] = 1.0 / len(winners) if i in winners else 0.0
            leading = winners[0]
            return leading, eq
        remaining = list(self.deck.cards)
        if len(remaining) < need:
            return None, {}
        N = 600
        wins = [0.0] * len(self.players)
        for _ in range(N):
            runout = random.sample(remaining, need)
            board = self.community_cards + runout
            best_rank = (-1,)
            winners = []
            for i in all_in_indices:
                r = evaluate_hand(self.players[i].hand + board)
                if r > best_rank:
                    best_rank = r
                    winners = [i]
                elif r == best_rank:
                    winners.append(i)
            for i in winners:
                wins[i] += 1.0 / len(winners)
        equities = {i: wins[i] / N for i in all_in_indices}
        leading_idx = max(all_in_indices, key=lambda i: equities[i])
        return leading_idx, equities

    def _deal_allin_runout_and_showdown(self):
        """全员 All-in 时发完剩余公共牌并比牌。"""
        while self.stage in ('preflop', 'flop', 'turn', 'river'):
            if self.stage == 'preflop':
                self.deck.burn()
                self.community_cards.extend(self.deck.deal(3))
                self.stage = 'flop'
            elif self.stage == 'flop':
                self.deck.burn()
                self.community_cards.extend(self.deck.deal(1))
                self.stage = 'turn'
            elif self.stage == 'turn':
                self.deck.burn()
                self.community_cards.extend(self.deck.deal(1))
                self.stage = 'river'
            elif self.stage == 'river':
                self.stage = 'showdown'
                self.is_running = False
                self.last_action_description = "比牌（全员 All-in）。"
                self._do_showdown()
                return
        return

    def _advance_to_next_street(self):
        for p in self.players:
            p.current_bet = 0
            p.has_acted = False
        self.last_raise_amount = 0
        n = len(self.players)
        # If all remaining players are all-in, deal out the rest and showdown (or offer insurance)
        active_can_act = [i for i in range(n) if not self.players[i].has_folded and not self.players[i].is_all_in]
        if not active_can_act:
            all_in_indices = [i for i in range(n) if not self.players[i].has_folded and self.players[i].is_all_in]
            if self.insurance_enabled and len(all_in_indices) >= 2:
                leading_idx, equities = self._compute_equity(all_in_indices)
                if leading_idx is not None:
                    equity = equities.get(leading_idx, 0)
                    leader = self.players[leading_idx]
                    # 只有领先玩家且有人且胜率在 (0,1) 且领先玩家有筹码可付保费时才提供保险
                    if 0 < equity < 1 and leader.is_human and leader.chips > 0:
                        self.pending_insurance = {
                            "leading_idx": leading_idx,
                            "equity": round(equity, 4),
                            "all_in_indices": all_in_indices,
                        }
                        self.stage = "insurance_offer"
                        self.is_running = False
                        self.last_action_description = f"{leader.name} 领先（胜率 {equity*100:.1f}%），可购买保险。"
                        return
            self._deal_allin_runout_and_showdown()
            return
        if self.stage == 'preflop':
            self.stage = 'preflop_done'
            self.pending_street = 'flop'
            self.last_action_description = "底牌圈下注结束，请点击「发翻牌」。"
            return
        if self.stage == 'flop':
            self.stage = 'flop_done'
            self.pending_street = 'turn'
            self.last_action_description = "翻牌圈下注结束，请点击「发转牌」。"
            return
        if self.stage == 'turn':
            self.stage = 'turn_done'
            self.pending_street = 'river'
            self.last_action_description = "转牌圈下注结束，请点击「发河牌」。"
            return
        if self.stage == 'river':
            self.stage = 'river_done'
            self.pending_street = 'showdown'
            self.last_action_description = "河牌圈下注结束，请点击「比牌」。"
            return
        self.run_ai_turns()

    def deal_next_street(self):
        """用户点击发牌后调用：发下一街牌并进入该街下注轮。"""
        n = len(self.players)
        if self.pending_street == 'flop':
            self.deck.burn()
            self.community_cards.extend(self.deck.deal(3))
            self.stage = 'flop'
            self.pending_street = None
            self.last_action_description = "翻牌已发，请下注。"
            self.current_player_idx = (self.dealer_idx + 1) % n
            while self.players[self.current_player_idx].has_folded or self.players[self.current_player_idx].is_all_in:
                self.current_player_idx = (self.current_player_idx + 1) % n
            self.run_ai_turns()
        elif self.pending_street == 'turn':
            self.deck.burn()
            self.community_cards.extend(self.deck.deal(1))
            self.stage = 'turn'
            self.pending_street = None
            self.last_action_description = "转牌已发，请下注。"
            self.current_player_idx = (self.dealer_idx + 1) % n
            while self.players[self.current_player_idx].has_folded or self.players[self.current_player_idx].is_all_in:
                self.current_player_idx = (self.current_player_idx + 1) % n
            self.run_ai_turns()
        elif self.pending_street == 'river':
            self.deck.burn()
            self.community_cards.extend(self.deck.deal(1))
            self.stage = 'river'
            self.pending_street = None
            self.last_action_description = "河牌已发，请下注。"
            self.current_player_idx = (self.dealer_idx + 1) % n
            while self.players[self.current_player_idx].has_folded or self.players[self.current_player_idx].is_all_in:
                self.current_player_idx = (self.current_player_idx + 1) % n
            self.run_ai_turns()
        elif self.pending_street == 'showdown':
            self.stage = 'showdown'
            self.is_running = False
            self.pending_street = None
            self.last_action_description = "比牌。"
            self._do_showdown()

    def resolve_insurance(self, premium_amount):
        """处理保险：不买则 premium_amount=0，买则传入保费。随后发完 All-in  runout 并比牌。"""
        if not self.pending_insurance:
            return False
        leading_idx = self.pending_insurance["leading_idx"]
        equity = self.pending_insurance["equity"]
        self.pending_insurance = None
        premium_amount = int(premium_amount or 0)
        if premium_amount > 0:
            leader = self.players[leading_idx]
            premium_amount = min(premium_amount, leader.chips)
            if premium_amount > 0:
                leader.chips -= premium_amount
                # 输时拿回 payout = premium / equity（公平赔率 1/E）
                payout = premium_amount / max(equity, 0.01)
                self.insurance_purchase = {
                    "player_idx": leading_idx,
                    "premium": premium_amount,
                    "payout_if_lose": int(payout),
                }
        self._deal_allin_runout_and_showdown()
        return True

    def _advance_turn(self):
        n = len(self.players)
        not_folded = [i for i in range(n) if not self.players[i].has_folded]
        if len(not_folded) <= 1:
            self.stage = 'showdown'
            self.is_running = False
            self.last_action_description = "比牌（仅剩一人）。"
            self._do_showdown()
            return
        # Find next player who can act (not folded, not all-in)
        start = self.current_player_idx
        self.current_player_idx = (self.current_player_idx + 1) % n
        while self.players[self.current_player_idx].has_folded or self.players[self.current_player_idx].is_all_in:
            if self.current_player_idx == start:
                break
            self.current_player_idx = (self.current_player_idx + 1) % n
        if self._betting_round_complete():
            self._advance_to_next_street()
        else:
            self.run_ai_turns()

    def _put_in_pot(self, player_idx, amount):
        self.players[player_idx].chips -= amount
        self.players[player_idx].current_bet += amount
        self.players[player_idx].total_bet_this_hand += amount
        self.pot += amount
        if self.players[player_idx].chips == 0:
            self.players[player_idx].is_all_in = True

    def process_player_action(self, action, amount=0):
        if not self.is_running:
            return
        idx = self.current_player_idx
        player = self.players[idx]
        if not player.is_human or player.has_folded or player.is_all_in:
            return
        call_amt = self._call_amount(idx)
        min_raise_to = self._min_raise_to()
        max_bet = self._max_bet_this_street()

        if action == 'fold':
            player.has_folded = True
            player.has_acted = True
            self.last_action_description = f"{player.name} 弃牌。"
            self._advance_turn()
            return

        if action == 'check':
            if call_amt != 0:
                return  # invalid
            player.has_acted = True
            self.last_action_description = f"{player.name} 过牌。"
            self._advance_turn()
            return

        if action == 'call':
            to_put = min(call_amt, player.chips)
            if to_put == 0 and call_amt == 0:
                player.has_acted = True
                self.last_action_description = f"{player.name} 过牌。"
            else:
                self._put_in_pot(idx, to_put)
                player.has_acted = True
                self.last_action_description = f"{player.name} 跟注 {to_put}。"
            self._advance_turn()
            return

        if action in ('bet', 'raise', 'all_in'):
            if action == 'all_in':
                to_put = player.chips
            else:
                amount = int(amount)
                if amount < 0:
                    return
                # amount = total bet this street (bet/raise "to")
                to_put = min(max(amount, 0) - player.current_bet, player.chips)
            if to_put <= 0 and action != 'all_in':
                return
            if to_put > 0 and action != 'all_in':
                total_after = player.current_bet + to_put
                if total_after < min_raise_to and total_after < player.current_bet + player.chips:
                    return  # bet/raise too small (unless all-in)
            max_bet = self._max_bet_this_street()
            self._put_in_pot(idx, to_put)
            raise_size = (player.current_bet - max_bet) if player.current_bet > max_bet else 0
            if raise_size > 0:
                self.last_raise_amount = raise_size
            player.has_acted = True
            if action == 'all_in':
                self.last_action_description = f"{player.name} All-in {to_put}。"
            elif player.current_bet > max_bet:
                self.last_action_description = f"{player.name} 下注/加注 {to_put}。"
            else:
                self.last_action_description = f"{player.name} 下注 {to_put}。"
            self._advance_turn()
            return

    def run_ai_turns(self):
        while self.is_running:
            idx = self.current_player_idx
            player = self.players[idx]
            if player.is_human or player.has_folded or player.is_all_in:
                return
            call_amt = self._call_amount(idx)
            # Simple AI: random fold 10%, else check/call or small bet
            import random
            if call_amt > player.chips * 0.5 and random.random() < 0.3:
                player.has_folded = True
                player.has_acted = True
                self.last_action_description = f"{player.name} 弃牌。"
            elif call_amt == 0:
                if random.random() < 0.6:
                    player.has_acted = True
                    self.last_action_description = f"{player.name} 过牌。"
                else:
                    bet_amt = min(self.big_blind * 2, player.chips)
                    if bet_amt > 0:
                        self._put_in_pot(idx, bet_amt)
                        self.last_raise_amount = bet_amt
                    player.has_acted = True
                    self.last_action_description = f"{player.name} 下注 {bet_amt}。"
            else:
                if random.random() < 0.4 and player.chips >= call_amt:
                    to_put = min(call_amt, player.chips)
                    self._put_in_pot(idx, to_put)
                    player.has_acted = True
                    self.last_action_description = f"{player.name} 跟注 {to_put}。"
                else:
                    player.has_folded = True
                    player.has_acted = True
                    self.last_action_description = f"{player.name} 弃牌。"
            self._advance_turn()

    def _do_showdown(self):
        """Evaluate hands, build side pots, assign winnings."""
        active = [(i, p) for i, p in enumerate(self.players) if not p.has_folded]
        if not active:
            return
        insurance_buyer_chips_before = None
        if getattr(self, "insurance_purchase", None):
            insurance_buyer_chips_before = self.players[self.insurance_purchase["player_idx"]].chips

        if len(active) == 1:
            idx, p = active[0]
            p.chips += self.pot
            self.winner_idx = idx
            self.winner_info = f"{p.name} 获胜（对手弃牌），赢得 {self.pot}。"
            self._showdown_reveal = False  # 一人赢，不亮对方牌
            if getattr(self, "insurance_purchase", None):
                self.insurance_purchase = None
            import random
            for i in range(len(self.players)):
                if not self.players[i].is_human:
                    if i == idx:
                        self.set_emote(i, random.choice(['🎉', '😎', '👍']))
                    else:
                        self.set_emote(i, random.choice(['😤', '😢', '👎']))
            return
        self._showdown_reveal = True  # 多人比牌，亮出所有参与比牌者的手牌
        # Build side pots by all-in levels (all players who put money in)
        levels = sorted(set(p.total_bet_this_hand for p in self.players if p.total_bet_this_hand > 0))
        pots = []
        for k, level in enumerate(levels):
            prev_level = levels[k - 1] if k > 0 else 0
            amount = 0
            for p in self.players:
                contrib = min(p.total_bet_this_hand, level) - prev_level
                if contrib > 0:
                    amount += contrib
            eligible = [i for i, p in enumerate(self.players) if not p.has_folded and p.total_bet_this_hand >= level]
            if amount > 0 and eligible:
                pots.append({'amount': amount, 'eligible': eligible})
        # Evaluate best hand for each active player
        best_rank = [(-1,)] * len(self.players)
        for i, p in enumerate(self.players):
            if p.has_folded:
                continue
            r = evaluate_hand(p.hand + self.community_cards)
            best_rank[i] = r
        # Distribute from last pot to first
        hand_names = ["高牌", "一对", "两对", "三条", "顺子", "同花", "葫芦", "四条", "同花顺"]
        for pot_info in reversed(pots):
            eligible = pot_info['eligible']
            best = (-1,)
            winners = []
            for i in eligible:
                if best_rank[i] > best:
                    best = best_rank[i]
                    winners = [i]
                elif best_rank[i] == best:
                    winners.append(i)
            amt = pot_info['amount']
            per = amt // len(winners)
            extra = amt % len(winners)
            for w in winners:
                self.players[w].chips += per + (extra if w == winners[0] else 0)
                extra = 0
        # Build winner message from main pot (first pot)
        if pots:
            main_eligible = pots[0]['eligible']
            best = (-1,)
            winner_idx = None
            for i in main_eligible:
                if best_rank[i] > best:
                    best = best_rank[i]
                    winner_idx = i
            if winner_idx is not None:
                self.winner_idx = winner_idx
                hand_type = best[0]
                self.winner_info = f"{self.players[winner_idx].name} 获胜！牌型: {hand_names[hand_type]}，赢得 {self.pot}。"
                # AI reacts with emote when it wins or loses
                import random
                for i in range(len(self.players)):
                    if not self.players[i].is_human:
                        if i == winner_idx:
                            self.set_emote(i, random.choice(['🎉', '😎', '👍', '🤑']))
                        else:
                            self.set_emote(i, random.choice(['😤', '😢', '👎', '😅']))
        else:
            self.winner_info = "比牌结束。"

        # 保险结算：若购买者未赢任何池，则赔付
        if getattr(self, "insurance_purchase", None):
            buy = self.insurance_purchase
            idx = buy["player_idx"]
            chips_after = self.players[idx].chips
            if insurance_buyer_chips_before is not None and chips_after == insurance_buyer_chips_before:
                self.players[idx].chips += buy["payout_if_lose"]
            self.insurance_purchase = None

    def start_new_round(self):
        for p in self.players:
            p.reset_for_new_round()
        self.deck = Deck()
        self.deck.shuffle()
        self.pot = 0
        self.side_pots = []
        self.community_cards = []
        self.hand_id += 1
        self.dealer_idx = (self.dealer_idx + 1) % len(self.players)
        for p in self.players:
            p.receive_cards(self.deck.deal(2))
        self.stage = 'preflop'
        self.is_running = True
        self.last_action_description = "新一局，底牌已发。"
        self.winner_info = None
        self.winner_idx = None
        self._showdown_reveal = False
        self.pending_insurance = None
        self.insurance_purchase = None
        self._post_blinds()
        self.run_ai_turns()

    def get_state(self, private_for_player_sid=None):
        def hide_cards_for(i):
            # 自己的牌（REST 下视为玩家 0）始终可见
            if private_for_player_sid is None:
                if i == 0:
                    return False
                # 对方牌：仅当「多人比牌」时可见；弃牌导致一人赢时不可见
                if self.stage == 'showdown' and getattr(self, '_showdown_reveal', False):
                    return False
                return True
            if self.stage == 'showdown' and getattr(self, '_showdown_reveal', False):
                return False
            return getattr(self.players[i], 'sid', None) != private_for_player_sid and not (
                self.stage == 'showdown' and getattr(self, '_showdown_reveal', False)
            )

        state = {
            'hand_id': self.hand_id,
            'players': [self.players[i].to_dict(hide_cards=hide_cards_for(i)) for i in range(len(self.players))],
            'pot': self.pot,
            'side_pots': [{'amount': sp['amount']} for sp in self.side_pots],
            'community_cards': [c.to_dict() for c in self.community_cards],
            'stage': self.stage,
            'is_running': self.is_running,
            'current_player_idx': self.current_player_idx,
            'dealer_idx': self.dealer_idx,
            'sb_idx': self.sb_idx,
            'bb_idx': self.bb_idx,
            'last_action': self.last_action_description,
            'call_amount': self._call_amount(self.current_player_idx) if (self.is_running and not self.pending_street) else 0,
            'min_raise_to': self._min_raise_to() if (self.is_running and not self.pending_street) else 0,
        }
        if self.pending_street:
            state['pending_street'] = self.pending_street
        if getattr(self, 'pending_insurance', None):
            state['insurance_offer'] = {
                'leading_idx': self.pending_insurance['leading_idx'],
                'equity': self.pending_insurance['equity'],
                'leading_name': self.players[self.pending_insurance['leading_idx']].name,
            }
        if self.winner_info:
            state['winner_info'] = self.winner_info
            state['winner_idx'] = self.winner_idx
        import time
        now = time.time()
        state['emotes'] = {str(i): {'emote': info['emote'], 'at': info['at']}
                           for i, info in self._emotes.items()
                           if now - info['at'] < self._emote_ttl}
        return state

    def set_emote(self, player_idx, emote):
        """Record an emote from a player (shown above seat for a few seconds)."""
        import time
        if 0 <= player_idx < len(self.players) and emote:
            self._emotes[player_idx] = {'emote': str(emote)[:8], 'at': time.time()}

# dzpokerV3/tables.py - 服务端内存牌桌状态管理

import uuid
from core import game_logic
from core.cards import Deck
from core.hand_evaluator import get_hand_type_name

try:
    from database import HandAction
except Exception:
    HandAction = None  # 无数据库时降级

# ──────────────────────────────────────────────────────────
# 全局内存状态
# ──────────────────────────────────────────────────────────

TABLES = {}       # table_id(int) -> table dict
_tokens = {}      # token(str)    -> user dict
_sid_map = {}     # sid(str)      -> (table_id, seat_index)
_next_tid = [1]   # 自增 table id


# ──────────────────────────────────────────────────────────
# 认证工具
# ──────────────────────────────────────────────────────────

def login(username):
    """游客登录（仅用户名），返回 token。"""
    if not username:
        return {"ok": False, "message": "用户名不能为空"}
    for tok, u in _tokens.items():
        if u["username"] == username:
            return {"ok": True, "token": tok, "userId": u["user_id"], "username": username}
    token = str(uuid.uuid4())
    user_id = "guest_" + token[:8]
    _tokens[token] = {"user_id": user_id, "username": username, "stack": 10000}
    return {"ok": True, "token": token, "userId": user_id, "username": username}


def token_for_db_user(user_id, username):
    """为数据库用户创建（或复用）内存 token。"""
    uid = str(user_id)
    for tok, u in _tokens.items():
        if u["user_id"] == uid:
            return tok
    token = str(uuid.uuid4())
    _tokens[token] = {"user_id": uid, "username": username or f"user_{user_id}", "stack": 10000}
    return token


def get_user(token):
    """通过 token 查找用户，不存在返回 None。"""
    if not token:
        return None
    return _tokens.get(token)


# ──────────────────────────────────────────────────────────
# GameWrapper：给 app.py 提供对象接口
# ──────────────────────────────────────────────────────────

class _PlayerProxy:
    """每个座位的轻量代理，供 app.py 设置 .sid。"""
    def __init__(self, player_id, player_state):
        self.player_id = player_id
        self._state = player_state
        self.sid = None


class GameWrapper:
    """
    封装 core.game_logic 的字典式游戏状态，
    对外提供 app.py 所需的对象接口：
      .players[seat].sid
      .get_state(private_for_player_sid=...)
      .start_new_round()
      .pending_insurance
    """

    def __init__(self, game_state, seat_to_pid):
        """
        game_state   : core.game_logic 使用的 dict
        seat_to_pid  : list[str|None]，按座位索引存放 player_id
        """
        self.state = game_state
        self._seat_to_pid = seat_to_pid
        self.players = [
            _PlayerProxy(pid, game_state["players"].get(pid, {})) if pid else None
            for pid in seat_to_pid
        ]
        self.pending_insurance = None

    def _private_pid_for_sid(self, sid):
        if not sid:
            return None
        for p in self.players:
            if p and p.sid == sid:
                return p.player_id
        return None

    @staticmethod
    def _card_to_display(c):
        """Card or 'AH'/'2S' string -> {suit: unicode, rank: str} for frontend."""
        if hasattr(c, "rank") and hasattr(c, "suit"):
            rank, suit = c.rank, c.suit
        elif isinstance(c, str) and len(c) >= 2:
            rank, suit = c[0], c[1]
        else:
            return {"suit": "?", "rank": "?"}
        suit_unicode = {"H": "♥", "D": "♦", "C": "♣", "S": "♠"}.get(str(suit).upper(), "?")
        return {"suit": suit_unicode, "rank": str(rank)}

    def get_state(self, private_for_player_sid=None, emotes=None):
        """返回可 JSON 序列化的游戏状态，含私牌（仅限指定 sid）。前端期望 name/chips/current_bet/hand、牌面为 {suit, rank}。emotes 为牌桌表情列表（按座位），传入后会在状态中包含供前端展示。"""
        private_pid = self._private_pid_for_sid(private_for_player_sid)
        s = self.state
        seat_to_pid = self._seat_to_pid
        active_pids = [pid for pid in seat_to_pid if pid]

        dealer_idx = sb_idx = bb_idx = current_player_idx = 0
        if active_pids:
            dealer_pos = s.get("dealer_button_position", 0)
            dealer_pos = min(dealer_pos, len(active_pids) - 1)
            dealer_pid = active_pids[dealer_pos]
            dealer_idx = seat_to_pid.index(dealer_pid) if dealer_pid in seat_to_pid else 0
            sb_pid = s.get("sb_player_id")
            bb_pid = s.get("bb_player_id")
            sb_idx = seat_to_pid.index(sb_pid) if sb_pid and sb_pid in seat_to_pid else -1
            bb_idx = seat_to_pid.index(bb_pid) if bb_pid and bb_pid in seat_to_pid else -1
            cur_pid = s.get("current_player_id")
            current_player_idx = seat_to_pid.index(cur_pid) if cur_pid and cur_pid in seat_to_pid else -1
        cur_pid = s.get("current_player_id")

        players_out = []
        for seat_idx, pid in enumerate(seat_to_pid):
            if pid is None:
                players_out.append(None)
                continue
            ps = s["players"].get(pid, {})
            hole = ps.get("hole_cards", [])
            name = str(pid)[:12]
            for _tok, u in _tokens.items():
                if str(u.get("user_id")) == str(pid):
                    name = (u.get("username") or "玩家")[:20]
                    break
            # 摊牌/结束：未弃牌玩家的手牌对所有人可见；否则仅自己可见
            stage = s.get("stage")
            stage_name = (stage.name if stage else "PREFLOP") if stage else "PREFLOP"
            in_showdown = stage_name in ("SHOWDOWN", "ENDED")
            not_folded = ps.get("is_in_hand", False) and ps.get("is_active", False)
            if pid == private_pid and hole:
                hand = [self._card_to_display(c) for c in hole]
            elif in_showdown and not_folded and hole:
                hand = [self._card_to_display(c) for c in hole]
            else:
                hand = [self._card_to_display("??") for _ in hole] if hole else []
            players_out.append({
                "seat": seat_idx,
                "player_id": pid,
                "name": name,
                "chips": ps.get("stack", 0),
                "current_bet": ps.get("bet_this_round", 0),
                "hand": hand,
                "hole_cards": hand,
                "stack": ps.get("stack", 0),
                "bet_this_round": ps.get("bet_this_round", 0),
                "last_action": ps.get("last_action"),
                "is_in_hand": ps.get("is_in_hand", False),
                "is_active": ps.get("is_active", False),
                "has_folded": not ps.get("is_in_hand", True) or not ps.get("is_active", True),
                "is_all_in": ps.get("is_all_in", False),
            })
        stage = s.get("stage")
        stage_name = stage.name if stage else "PREFLOP"
        community = s.get("community_cards", [])
        street_label_map = {
            "PREFLOP": "底牌圈",
            "FLOP": "翻牌圈",
            "TURN": "转牌圈",
            "RIVER": "河牌圈",
            "SHOWDOWN": "比牌",
            "ENDED": "比牌结束",
        }
        street_label = street_label_map.get(stage_name, stage_name or "等待")
        current_player_name = ""
        if 0 <= current_player_idx < len(players_out) and players_out[current_player_idx]:
            current_player_name = (players_out[current_player_idx].get("name") or "")[:20]
        out = {
            "stage": stage_name.lower() if stage_name else "preflop",
            "street_label": street_label,
            "current_player_name": current_player_name,
            "pot": s.get("pot", 0),
            "community_cards": [self._card_to_display(c) for c in community],
            "current_player_id": cur_pid,
            "current_player_idx": current_player_idx,
            "dealer_idx": dealer_idx,
            "sb_idx": sb_idx,
            "bb_idx": bb_idx,
            "sb_player_id": s.get("sb_player_id"),
            "bb_player_id": s.get("bb_player_id"),
            "amount_to_call": s.get("amount_to_call", 0),
            "call_amount": s.get("amount_to_call", 0),
            "min_raise_to": s.get("amount_to_call", 0) + max(s.get("last_raise_amount", s.get("bb", 0)), s.get("bb", 0)),
            "last_action": next((p.get("last_action") for p in s["players"].values() if p.get("last_action")), "") or "",
            "players": players_out,
            "max_players": len(seat_to_pid),
            "pending_insurance": self.pending_insurance,
            "is_running": s.get("current_player_id") is not None and stage_name not in ("SHOWDOWN", "ENDED"),
            "side_pots": [{"amount": p.get("amount", p)} for p in s.get("pots", [])] if s.get("pots") else [],
        }
        # 仅当前请求玩家可见：翻牌/转牌/河牌后显示己方牌型
        if private_pid:
            ps = s["players"].get(private_pid, {})
            hole = ps.get("hole_cards", [])
            community = s.get("community_cards", [])
            if hole and len(community) >= 3:
                out["my_hand_type"] = get_hand_type_name(hole, community)
        if emotes is not None and isinstance(emotes, (list, tuple)):
            import time
            now = time.time()
            out_emotes = {}
            for i in range(len(emotes)):
                if i < len(emotes) and emotes[i]:
                    out_emotes[str(i)] = {"emote": str(emotes[i])[:8], "at": now}
            out["emotes"] = out_emotes
        else:
            out["emotes"] = {}
        if stage_name == "ENDED":
            winners = s.get("winners", [])
            last_winnings = s.get("last_hand_winnings", {})
            out["winnings_by_seat"] = {
                seat_idx: last_winnings.get(pid, 0)
                for seat_idx, pid in enumerate(seat_to_pid) if pid
            }
            if winners:
                winner_pid = winners[0]
                winner_idx = seat_to_pid.index(winner_pid) if winner_pid in seat_to_pid else -1
                winner_name = str(winner_pid)[:12]
                for _tok, u in _tokens.items():
                    if str(u.get("user_id")) == str(winner_pid):
                        winner_name = (u.get("username") or "玩家")[:20]
                        break
                amount_won = sum(last_winnings.get(pid, 0) for pid in winners)
                out["winner_idx"] = winner_idx
                out["winner_info"] = "{} 获胜！赢得 {} 筹码".format(winner_name, amount_won)
                out["winner_amount"] = amount_won
        return out

    def start_new_round(self):
        """开启新一局手牌。"""
        s = self.state
        active_pids = [pid for pid in self._seat_to_pid if pid]
        for pid in active_pids:
            ps = s["players"].get(pid, {})
            ps.update({
                "is_in_hand": ps.get("stack", 0) > 0,
                "bet_this_round": 0,
                "last_action": None,
                "hole_cards": [],
            })
            ps["is_active"] = ps["is_in_hand"]
        s.update({
            "pot": 0,
            "community_cards": [],
            "amount_to_call": 0,
            "last_raiser_id": None,
            "dealer_button_position": (s.get("dealer_button_position", -1) + 1) % max(len(active_pids), 1),
        })
        game_logic.start_new_hand(s)


# ──────────────────────────────────────────────────────────
# 牌桌管理
# ──────────────────────────────────────────────────────────

def _alloc_table_id():
    tid = _next_tid[0]
    _next_tid[0] += 1
    return tid


def create_table(db=None, table_name=None, sb=5, bb=10, max_players=6):
    """创建内存牌桌，返回 table dict。"""
    tid = _alloc_table_id()
    t = {
        "table_id": tid,
        "table_name": table_name or f"牌桌 {tid}",
        "status": "waiting",
        "seats": [None] * max_players,
        "stacks": [0] * max_players,
        "max_players": max_players,
        "blinds": {"sb": sb, "bb": bb},
        "game": None,
        "emotes": [None] * max_players,
        "current_hand_id": None,
    }
    TABLES[tid] = t
    return t


def list_tables(db=None):
    """返回所有牌桌摘要列表。"""
    result = []
    for tid, t in TABLES.items():
        seated = sum(1 for s in t["seats"] if s is not None)
        result.append({
            "tableId": t["table_id"],
            "tableName": t["table_name"],
            "status": t["status"],
            "blinds": t["blinds"],
            "maxPlayers": t["max_players"],
            "seatedPlayers": seated,
        })
    return result


def sit(db_or_table_id, table_id_or_token=None, token_or_seat=None, seat_idx=None, auto_start=True):
    """
    兼容两种调用方式：
      sit(db, table_id, token, seat)   -- 新式（带 db）
      sit(table_id, token, seat)       -- 旧式（无 db）
    auto_start: 当座位人数>=2时是否自动开局；批量加机器人时应传 False，由调用方统一开局。
    """
    if seat_idx is None:
        # 旧式：sit(table_id, token, seat)
        t_id, tok, s = db_or_table_id, table_id_or_token, token_or_seat
    else:
        # 新式：sit(db, table_id, token, seat)
        t_id, tok, s = table_id_or_token, token_or_seat, seat_idx

    s = int(s)
    t = TABLES.get(t_id)
    if not t:
        return False, "牌桌不存在"
    
    user = get_user(tok)
    if not user:
        return False, "请先登录"
    uid = user["user_id"]
    
    # 检查玩家是否已经在牌桌上
    if uid in t["seats"]:
        # 如果玩家已经在牌桌上，允许重新连接（返回成功）
        current_seat = t["seats"].index(uid)
        return True, None
    
    # 游戏进行中不允许新玩家入座（但如果游戏刚开始且还在等待阶段，允许入座）
    if t["status"] == "playing":
        # 检查游戏是否刚开始（还没有发牌）
        game_state = t.get("game_state")
        if game_state:
            stage = game_state.get("stage")
            # 如果还在 PREFLOP 且没有人行动过，允许入座
            if stage and hasattr(stage, 'name') and stage.name == "PREFLOP":
                # 检查是否有人已经行动
                has_action = any(
                    p.get("last_action") for p in game_state.get("players", {}).values()
                )
                if not has_action:
                    # 游戏刚开始，还没人行动，允许入座
                    pass
                else:
                    return False, "游戏进行中，无法入座"
            else:
                return False, "游戏进行中，无法入座"
        else:
            return False, "游戏进行中，无法入座"
    
    if s < 0 or s >= t["max_players"]:
        return False, "座位号无效"
    if t["seats"][s] is not None:
        return False, "该座位已有人"
    
    t["seats"][s] = uid
    t["stacks"][s] = user.get("stack", 1000)

    # 检查是否满足开局条件（仅当 auto_start 时自动开局，避免批量加机器人时加一个就开一局）
    seated_players = sum(1 for seat in t["seats"] if seat is not None)
    if auto_start and t["status"] == "waiting" and seated_players >= 2:
        print(f"[Auto-Start] 牌桌 {t_id} 满足开局条件，自动开始游戏...")
        db_session = db_or_table_id if seat_idx is not None else None
        start_game(db_session, t_id, tok)
        
    return True, None


def leave(table_id, token):
    """玩家离座（仅等待中允许）。"""
    t = TABLES.get(table_id)
    if not t:
        return False, "牌桌不存在"
    
    # 游戏进行中不允许离座
    if t["status"] == "playing":
        return False, "游戏进行中无法离座，请等待本局结束"
    
    user = get_user(token)
    if not user:
        return False, "请先登录"
    uid = user["user_id"]
    try:
        idx = t["seats"].index(uid)
    except ValueError:
        return False, "您不在此桌"
    t["seats"][idx] = None
    t["stacks"][idx] = 0
    return True, None


def get_table_state(table_id, token):
    """从指定用户视角返回牌桌状态，含 my_seat、can_start、player_count。"""
    t = TABLES.get(table_id)
    if not t:
        return None, "牌桌不存在"
    user = get_user(token)
    uid = user["user_id"] if user else None
    seats_str = [str(s) if s else None for s in t["seats"]]
    my_seat = seats_str.index(str(uid)) if uid and str(uid) in seats_str else -1
    seated = sum(1 for s in t["seats"] if s is not None)
    return {
        "tableId": t["table_id"],
        "tableName": t["table_name"],
        "status": t["status"],
        "blinds": t["blinds"],
        "maxPlayers": t["max_players"],
        "seats": [
            {"userId": t["seats"][i], "stack": t["stacks"][i]} if t["seats"][i] else None
            for i in range(t["max_players"])
        ],
        "my_seat": my_seat,
        "player_count": seated,
        "can_start": t["status"] == "waiting" and seated >= 2,
        "seat_names": [
            next((u.get("username") for _tok, u in _tokens.items() if str(u.get("user_id")) == str(t["seats"][i])), None)
            if t["seats"][i] else None
            for i in range(t["max_players"])
        ],
    }, None


def get_table_state_public(table_id):
    """返回不含私密信息的牌桌状态。"""
    t = TABLES.get(table_id)
    if not t:
        return None
    return {
        "tableId": t["table_id"],
        "tableName": t["table_name"],
        "status": t["status"],
        "blinds": t["blinds"],
        "maxPlayers": t["max_players"],
        "seats": [
            {"userId": t["seats"][i], "stack": t["stacks"][i]} if t["seats"][i] else None
            for i in range(t["max_players"])
        ],
    }


def get_seat_index(table_id, user_id):
    """返回用户在牌桌中的座位索引，未找到返回 -1。"""
    t = TABLES.get(table_id)
    if not t:
        return -1
    uid = str(user_id)
    for i, s in enumerate(t["seats"]):
        if s is not None and str(s) == uid:
            return i
    return -1


def start_game(db, table_id, token):
    """开始游戏（需要至少 2 名玩家入座）。"""
    t = TABLES.get(table_id)
    if not t:
        return False, "牌桌不存在"
    if t["status"] == "playing":
        return False, "游戏已在进行中"
    seated = [(i, uid) for i, uid in enumerate(t["seats"]) if uid is not None]
    if len(seated) < 2:
        return False, "至少需要 2 名玩家才能开始"

    sb = t["blinds"]["sb"]
    bb = t["blinds"]["bb"]
    seat_to_pid = list(t["seats"])

    players_dict = {}
    for seat_idx, uid in seated:
        # detect bot flag from tokens (if the seat was occupied by a bot token earlier)
        is_bot = False
        try:
            # tokens map token->user; reverse lookup for uid
            for tok, u in _tokens.items():
                if u.get("user_id") == uid and u.get("is_bot"):
                    is_bot = True
                    break
        except Exception:
            is_bot = False
        players_dict[uid] = {
            "stack": t["stacks"][seat_idx],
            "is_in_hand": True,
            "is_active": True,
            "bet_this_round": 0,
            "last_action": None,
            "hole_cards": [],
            "is_bot": is_bot,
            "is_all_in": False,
        }

    game_state = {
        "players": players_dict,
        "pot": 0,
        "community_cards": [],
        "stage": game_logic.GameStage.PREFLOP,
        "amount_to_call": 0,
        "last_raise_amount": 0,
        "last_raiser_id": None,
        "dealer_button_position": 0,
        "sb": sb,
        "bb": bb,
        "deck": Deck(),
        "player_order": [uid for _, uid in seated],
    }
    game_logic.start_new_hand(game_state)

    t["game"] = GameWrapper(game_state, seat_to_pid)
    t["status"] = "playing"

    # 若第一个行动者是机器人，立即执行所有连续机器人回合（不略过、不等待后台循环）
    wrapper = t["game"]
    cur_pid = wrapper.state.get("current_player_id")
    if cur_pid and wrapper.state["players"].get(cur_pid, {}).get("is_bot"):
        try:
            final_state, _ = game_logic.run_ai_turns(wrapper.state)
            wrapper.state = final_state
        except Exception as e:
            print(f"[start_game] run_ai_turns: {e}")

    return True, None


# ──────────────────────────────────────────────────────────
# 游戏动作
# ──────────────────────────────────────────────────────────

def process_action(db, table_id, seat_index, action_str, amount=0):
    table = TABLES.get(table_id)
    if not table or not table.get("game"):
        return False, "对局不存在"

    wrapper = table["game"]
    s = wrapper._seat_to_pid
    if seat_index < 0 or seat_index >= len(s) or not s[seat_index]:
        return False, "无效座位"
    user_id = s[seat_index]

    if wrapper.state.get("current_player_id") != user_id:
        return False, "未轮到你行动"

    try:
        action = game_logic.PlayerAction[action_str.upper()]
    except KeyError:
        return False, f"无效的动作: {action_str}"

    # 记录行动前的状态
    stage_before = wrapper.state.get("stage", "UNKNOWN")
    pot_before = wrapper.state.get("pot", 0)
    player_stack_before = wrapper.state.get("players", {}).get(user_id, {}).get("stack", 0)
    
    print(f"[Action] 牌桌 {table_id}, 座位 {seat_index}, 玩家 {user_id}")
    print(f"  阶段: {stage_before}, 底池: {pot_before}, 玩家筹码: {player_stack_before}")
    print(f"  行动: {action_str.upper()}, 金额: {amount}")

    updated_state, error = game_logic.handle_player_action(wrapper.state, user_id, action, amount)
    if error:
        print(f"  ❌ 行动失败: {error}")
        return False, error
    
    wrapper.state = updated_state
    
    # 记录行动后的状态
    stage_after = wrapper.state.get("stage", "UNKNOWN")
    pot_after = wrapper.state.get("pot", 0)
    player_stack_after = wrapper.state.get("players", {}).get(user_id, {}).get("stack", 0)
    current_player_after = wrapper.state.get("current_player_id", "NONE")
    
    print(f"  ✅ 行动成功")
    print(f"  阶段: {stage_before} → {stage_after}")
    print(f"  底池: {pot_before} → {pot_after} (变化: {pot_after - pot_before})")
    print(f"  玩家筹码: {player_stack_before} → {player_stack_after} (变化: {player_stack_after - player_stack_before})")
    print(f"  下一个行动者: {current_player_after}")

    hand_id = table.get("current_hand_id")
    if db and HandAction and hand_id:
        # 获取当前行动顺序
        action_order = db.query(HandAction).filter_by(hand_id=hand_id).count() + 1
        
        db.add(HandAction(
            hand_id=hand_id,
            user_id=user_id,
            action_type=action.name,
            amount=int(amount) if amount else None,
            stage=stage_after,
            action_order=action_order
        ))

    # --- If next player(s) are bots, run AI loop to let them act automatically ---
    try:
        # Loop while current_player_id corresponds to a bot in this table
        while True:
            cur_pid = wrapper.state.get('current_player_id')
            if not cur_pid:
                break
            # map pid -> seat index
            if cur_pid in wrapper._seat_to_pid:
                cur_seat = wrapper._seat_to_pid.index(cur_pid)
                # check if seat is occupied and if it's a bot
                pid_state = wrapper.state['players'].get(cur_pid, {})
                if pid_state.get('is_bot'):
                    # run AI loop and get updated state + actions（必须写回 wrapper.state，否则机器人行动不生效）
                    final_state, actions = game_logic.run_ai_turns(wrapper.state)
                    wrapper.state = final_state
                    # persist each AI action to hand_actions (with stage and action_order)
                    if actions and db and HandAction and hand_id:
                        next_order = db.query(HandAction).filter_by(hand_id=hand_id).count() + 1
                        for item in actions:
                            if len(item) >= 4:
                                aid, aname, aamount, stage_name = item[0], item[1], item[2], item[3]
                            else:
                                aid, aname, aamount = item[0], item[1], item[2]
                                stage_name = (wrapper.state.get('stage') or game_logic.GameStage.PREFLOP).name
                            db.add(HandAction(
                                hand_id=hand_id,
                                user_id=aid,
                                action_type=aname,
                                amount=int(aamount) if aamount is not None else None,
                                stage=stage_name,
                                action_order=next_order,
                            ))
                            next_order += 1
                    # continue loop in case multiple bots act in sequence
                    continue
            break
    except Exception as e:
        # don't block on AI errors; surface to caller if necessary
        print('AI run error:', e)

    return True, None


def add_bot(table_id, seat_idx, bot_name=None, stack=1000):
    """Add a simple bot to a specific seat on a waiting table.
    Returns (True, None) or (False, error_message).
    """
    t = TABLES.get(table_id)
    if not t:
        return False, "牌桌不存在"
    if t['status'] != 'waiting':
        return False, '牌桌已在进行中'
    if seat_idx < 0 or seat_idx >= t['max_players']:
        return False, '座位号无效'
    if t['seats'][seat_idx] is not None:
        return False, '该座位已有人'
    # create a bot player id
    pid = 'bot_' + str(uuid.uuid4())[:8]
    t['seats'][seat_idx] = pid
    t['stacks'][seat_idx] = stack
    # if game already exists, also register in game state players
    if t.get('game'):
        gw = t['game']
        gw.state['players'][pid] = {
            'stack': stack,
            'is_in_hand': False,
            'is_active': False,
            'bet_this_round': 0,
            'last_action': None,
            'is_bot': True,
        }
        gw._seat_to_pid[seat_idx] = pid
    return True, None


def deal_next_street(table_id):
    """进入下一条街（翻牌/转牌/河牌）。"""
    t = TABLES.get(table_id)
    if not t or not t.get("game"):
        return False, "对局不存在"
    game_logic.advance_to_next_stage(t["game"].state)
    return True, None


def resolve_insurance(table_id, token, amount):
    """处理保险决定（当前为存根，直接放弃）。"""
    t = TABLES.get(table_id)
    if not t or not t.get("game"):
        return False, "对局不存在"
    t["game"].pending_insurance = None
    return True, None


def set_emote(table_id, seat_index, emote):
    t = TABLES.get(table_id)
    if t and 0 <= seat_index < len(t["emotes"]):
        t["emotes"][seat_index] = emote


# ──────────────────────────────────────────────────────────
# WebSocket sid ↔ 座位 映射
# ──────────────────────────────────────────────────────────

def bind_sid_to_seat(table_id, sid, seat_index):
    _sid_map[sid] = (table_id, seat_index)


def get_table_and_seat_by_sid(sid):
    return _sid_map.get(sid, (None, None))


def leave_by_sid(sid):
    """WebSocket 断开时清理，返回 table_id 或 None。"""
    entry = _sid_map.pop(sid, None)
    if not entry:
        return None
    table_id, seat_index = entry
    t = TABLES.get(table_id)
    if t and t.get("game"):
        wrapper = t["game"]
        if 0 <= seat_index < len(wrapper.players):
            p = wrapper.players[seat_index]
            if p:
                p.sid = None
    return table_id

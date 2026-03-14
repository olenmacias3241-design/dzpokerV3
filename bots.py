# dzpokerV3/bots.py - 自动机器人玩家
#
# 使用方式：
#   import bots
#   bots.start(socketio)          # 在 run_poker.py 中启动后台线程
#   bots.add_bots_to_table(table_id, count=2, auto_start=True)

import threading
import time
import random
import uuid

import tables
from core.game_logic import GameStage

_socketio = None
_lock = threading.Lock()
# 全局串行：同一时刻只允许一个机器人行动（含思考时间），保证按次序下注
_bot_action_lock = threading.Lock()

BOT_THINK_MIN = 2.0   # 每个机器人随机 2～4 秒，便于看出「一个一个」轮询
BOT_THINK_MAX = 4.0
NEW_ROUND_DELAY = 3.0 # 新一局开始前的等待时间（秒）


# ──────────────────────────────────────────────
# 工具
# ──────────────────────────────────────────────

def _is_bot(user_id):
    for u in tables._tokens.values():
        if u["user_id"] == user_id and u.get("is_bot"):
            return True
    return False


def _create_bot(name):
    token = str(uuid.uuid4())
    uid = "bot_" + token[:6]
    tables._tokens[token] = {
        "user_id": uid,
        "username": name,
        "stack": 10000,
        "is_bot": True,
    }
    return token, uid


# 随机名字池（扑克室风格，避免「机器人X号」）
_BOT_NAME_POOL = [
    "德州老王", "梭哈小王子", "冷静的鱼", "河杀王", "翻牌怪", "跟注侠", "弃牌流", "慢打帝",
    "all-in怪", "老炮儿", "鲨鱼哥", "狐狸精", "稳如狗", "浪子阿杰", "神抽王", "鬼手",
    "大刘", "阿King", "小陈", "牌桌老K", "底池猎人", "Bluff大师", "紧凶流", "松浪流",
    "筹码收割机", "翻牌前弃", "河牌成牌", "听牌不信邪", "偷盲专业户", "价值下注怪",
    "红桃A", "黑桃K", "方片Q", "梅花J", "桌上传说", "深夜牌手", "周末战士", "咖啡续杯",
    "不弃牌", "慢打王", "推all-in", "跟到底", "偷鸡达人", "坚果成牌", "空气 bluff",
]

def _unique_bot_name():
    existing = {u["username"] for u in tables._tokens.values() if u.get("is_bot")}
    for _ in range(100):
        name = random.choice(_BOT_NAME_POOL)
        if name not in existing:
            return name
        name = name + str(random.randint(2, 99))
        if name not in existing:
            return name
    return "玩家" + str(random.randint(1000, 9999))


# ──────────────────────────────────────────────
# 决策逻辑（模拟人类：考虑底池、筹码、跟注额）
# ──────────────────────────────────────────────

def _decide(game_state):
    """
    类人下注逻辑：考虑底池、需跟注额、剩余筹码；可过牌时过牌/下注，需跟注时按跟注占比决定弃牌/跟注/加注/All-in。
    """
    atc = game_state.get("amount_to_call", 0)
    bb = game_state.get("bb", 10)
    pot = max(1, game_state.get("pot", 0))
    current_pid = game_state.get("current_player_id")
    if not current_pid:
        return "check", 0
    player = game_state.get("players", {}).get(current_pid, {})
    stack = player.get("stack", 0)
    bet_this_round = player.get("bet_this_round", 0)
    min_raise = max(bb, game_state.get("last_raise_amount", bb))
    call_amount = max(0, atc - bet_this_round)
    effective_call = min(call_amount, stack)

    # 无人下注时：尽量下注，减少「一起过」；仅小概率过牌
    if atc == 0:
        if stack <= 0:
            return "check", 0
        r = random.random()
        if r < 0.15:
            action, amount = "check", 0
        elif r < 0.55:
            bet_size = max(bb, int(pot * random.uniform(0.5, 1.0)))
            bet_size = min(bet_size, stack)
            action, amount = ("bet", bet_size) if bet_size > 0 else ("check", 0)
        else:
            bet_size = max(bb * 2, int(pot * random.uniform(1.0, 2.0)))
            bet_size = min(bet_size, stack)
            action, amount = ("bet", bet_size) if bet_size > 0 else ("check", 0)
    else:
        if stack <= 0:
            return "check", 0
        # 后端 RAISE 的 amount = 加注增量（非总投入），total_to_put = amount_to_call + amount
        call_ratio = effective_call / stack if stack else 0
        r = random.random()
        if call_ratio >= 0.8:
            action, amount = ("fold", 0) if r < 0.35 else ("all_in", 0)
        elif call_ratio >= 0.5:
            if r < 0.45:
                action, amount = "fold", 0
            elif r < 0.75:
                action, amount = "call", 0
            else:
                action, amount = "all_in", 0
        elif call_ratio >= 0.2:
            if r < 0.30:
                action, amount = "fold", 0
            elif r < 0.60:
                action, amount = "call", 0
            elif r < 0.85:
                # 加注增量 >= min_raise，且 total_to_put <= stack => amount <= stack - amount_to_call
                raise_increment = max(min_raise, int(pot * random.uniform(0.4, 0.8)))
                max_increment = max(0, stack - atc)
                raise_increment = min(raise_increment, max_increment)
                if raise_increment >= min_raise:
                    action, amount = "raise", raise_increment
                else:
                    action, amount = "call", 0
            else:
                action, amount = "all_in", 0
        else:
            if r < 0.15:
                action, amount = "fold", 0
            elif r < 0.50:
                action, amount = "call", 0
            elif r < 0.80:
                raise_increment = max(min_raise, int(pot * random.uniform(0.3, 0.6)))
                max_increment = max(0, stack - atc)
                raise_increment = min(raise_increment, max_increment)
                if raise_increment >= min_raise:
                    action, amount = "raise", raise_increment
                else:
                    action, amount = "call", 0
            else:
                action, amount = "all_in", 0

    print(f"[Bot] 决策: {action}, 金额: {amount}, 需跟注: {atc}, 底池: {pot}, 筹码: {stack}")
    return action, amount


def _think_time_for_action(action, amount):
    """返回机器人下注前思考时间（秒），便于看出轮次、避免一起过。"""
    return random.uniform(BOT_THINK_MIN, BOT_THINK_MAX)


# ──────────────────────────────────────────────
# 广播
# ──────────────────────────────────────────────

def _broadcast(table_id):
    if not _socketio:
        return
    t = tables.TABLES.get(table_id)
    if not t or not t.get("game"):
        return
    wrapper = t["game"]
    emotes = t.get("emotes")
    # 对每个在线真人玩家发送含私牌的状态（每人只发一次，避免重复推送导致界面断片）
    for p in wrapper.players:
        if p and p.sid:
            state = wrapper.get_state(private_for_player_sid=p.sid, emotes=emotes)
            _socketio.emit("game:state_update", state, room=p.sid, namespace="/")


# ──────────────────────────────────────────────
# 后台循环
# ──────────────────────────────────────────────

def _bot_loop():
    print("[Bot] 后台循环开始运行")
    while True:
        time.sleep(0.5)
        try:
            for tid, table in list(tables.TABLES.items()):
                if table.get("status") != "playing":
                    continue
                wrapper = table.get("game")
                if not wrapper:
                    continue

                gs = wrapper.state
                stage = gs.get("stage")

                # 手牌结束 → 等待后开新局
                if stage in (GameStage.ENDED, None) or (stage and stage.name == "ENDED"):
                    # 标记避免重复触发
                    if table.get("_bot_new_round_pending"):
                        continue
                    table["_bot_new_round_pending"] = True
                    print(f"[Bot] 牌桌 {tid} 手牌结束，{NEW_ROUND_DELAY}秒后开始新一局")
                    def _start_new(tid=tid, t=table, w=wrapper):
                        time.sleep(NEW_ROUND_DELAY)
                        try:
                            with _lock:
                                w.start_new_round()
                                t["_bot_new_round_pending"] = False
                            print(f"[Bot] 牌桌 {tid} 新一局已开始")
                            _sync_real_player_sids(tid)
                            if _socketio:
                                _socketio.emit("game:deal_phase", {"phase": "hole_cards"}, room=str(tid), namespace="/")
                            _broadcast(tid)
                        except Exception as e:
                            print(f"[Bot] start_new_round error: {e}")
                            t["_bot_new_round_pending"] = False
                    threading.Thread(target=_start_new, daemon=True).start()
                    continue

                # 检查是否轮到机器人（优先 _tokens，其次用游戏状态里的 is_bot 兜底）
                current_pid = gs.get("current_player_id")
                if not current_pid:
                    continue
                is_bot_turn = _is_bot(current_pid) or gs.get("players", {}).get(current_pid, {}).get("is_bot")
                if not is_bot_turn:
                    continue

                # 找到座位
                seat = next(
                    (i for i, pid in enumerate(wrapper._seat_to_pid) if pid == current_pid),
                    None
                )
                if seat is None:
                    continue

                # 全局串行：同一时刻只允许一个机器人行动（含思考时间），保证按次序
                with _bot_action_lock:
                    gs = wrapper.state
                    if gs.get("current_player_id") != current_pid:
                        continue
                    bot_name = tables._tokens.get(
                        next((tok for tok, u in tables._tokens.items() if u["user_id"] == current_pid), ""),
                        {}
                    ).get("username", current_pid)
                    print(f"[Bot] 牌桌 {tid}, 座位 {seat}, {bot_name} 开始思考...")
                    with _lock:
                        if gs.get("current_player_id") != current_pid:
                            continue
                        action, amount = _decide(gs)
                    think_time = _think_time_for_action(action, amount)
                    time.sleep(think_time)
                    with _lock:
                        if wrapper.state.get("current_player_id") != current_pid:
                            print(f"[Bot] {bot_name} 思考期间状态已改变，跳过")
                            continue
                        gs = wrapper.state
                        print(f"[Bot] 牌桌 {tid}, {bot_name} 执行: {action} {amount}")
                        db = None
                        try:
                            from database import SessionLocal
                            db = SessionLocal()
                        except Exception:
                            pass
                        try:
                            amt_int = int(amount) if isinstance(amount, (int, float)) else 0
                            ok, err = tables.process_action(db, tid, seat, action, amt_int)
                            if ok:
                                if db:
                                    db.commit()
                                print(f"[Bot] {bot_name} 行动成功: {action} {amount}")
                            else:
                                if db:
                                    db.rollback()
                                print(f"[Bot] {bot_name} 行动失败: {err}, 尝试兜底策略")
                                fallback = "check" if gs.get("amount_to_call", 0) == 0 else "call"
                                ok2, err2 = tables.process_action(db, tid, seat, fallback, 0)
                                if ok2:
                                    if db:
                                        db.commit()
                                    print(f"[Bot] {bot_name} 兜底成功: {fallback}")
                                else:
                                    if db:
                                        db.rollback()
                                    print(f"[Bot] {bot_name} 兜底也失败: {err2}")
                        except Exception as e:
                            if db:
                                try:
                                    db.rollback()
                                except Exception:
                                    pass
                            print(f"[Bot] process_action error: {e}")
                        finally:
                            if db:
                                try:
                                    db.close()
                                except Exception:
                                    pass
                    # 广播最新状态（含 current_player_id = 下一个行动者），确保轮到下一个角色
                    next_pid = wrapper.state.get("current_player_id") if wrapper else None
                    if next_pid:
                        next_name = tables._tokens.get(
                            next((tok for tok, u in tables._tokens.items() if u.get("user_id") == next_pid), ""),
                            {}
                        ).get("username", next_pid)
                        print(f"[Bot] 牌桌 {tid} 下一个行动者: {next_name} ({next_pid})")
                    _broadcast(tid)
                    # 给前端一点时间收到 state 再继续下一轮，避免「一起过」的错觉
                    time.sleep(0.4)
                    # 每轮只处理一个机器人，下一轮再轮询，避免多人「一起过」
                    break

        except Exception as e:
            print(f"[Bot] loop error: {e}")
            import traceback
            traceback.print_exc()


# ──────────────────────────────────────────────
# 公开 API
# ──────────────────────────────────────────────

def add_bots_to_table(table_id, count=1, auto_start=False):
    """
    向指定牌桌添加 count 个机器人。
    auto_start=True 时若已有 >= 2 名玩家则自动开局。

    返回 (added_list, error_str)
    """
    t = tables.TABLES.get(table_id)
    if not t:
        return [], "牌桌不存在"
    if t["status"] != "waiting":
        return [], "游戏已在进行中"

    added = []
    db = None
    try:
        from database import SessionLocal
        db = SessionLocal()
    except Exception:
        pass

    for _ in range(count):
        empty_seats = [i for i, uid in enumerate(t["seats"]) if uid is None]
        if not empty_seats:
            break
        name = _unique_bot_name()
        tok, uid = _create_bot(name)
        seat_idx = empty_seats[0]
        # 与 API 一致：sit(db, table_id, token, seat)，无 db 时传 None
        ok, err = tables.sit(db if db else None, table_id, tok, seat_idx, auto_start=False)
        if ok:
            added.append({"name": name, "seat": seat_idx})
            print(f"[Bot] add_bots_to_table: {name} 入座成功 seat={seat_idx}")
        else:
            tables._tokens.pop(tok, None)
            print(f"[Bot] add_bots_to_table: 入座失败 seat={seat_idx} name={name} err={err}")
    if db:
        try:
            db.close()
        except Exception:
            pass

    if auto_start:
        seated = sum(1 for s in t["seats"] if s is not None)
        if seated >= 2:
            tables.start_game(None, table_id, "")  # db=None, token="" (只检查人数)

    return added, None


def _sync_real_player_sids(table_id):
    """把 _sid_map 中真人玩家的 sid 同步到 GameWrapper，返回已同步的 sid 列表。"""
    t = tables.TABLES.get(table_id)
    if not t or not t.get("game"):
        return []
    wrapper = t["game"]
    synced = []
    for sid, (tid, seat) in list(tables._sid_map.items()):
        if tid != table_id:
            continue
        if 0 <= seat < len(wrapper.players) and wrapper.players[seat]:
            wrapper.players[seat].sid = sid
            synced.append((seat, sid))
    return synced


def fill_table_with_bots(table_id, delay=2.0):
    """
    延迟后自动填满所有空位（机器人），若已有 >= 2 人则自动开局。
    在玩家入座后调用。
    """
    def _do():
        time.sleep(delay)
        try:
            print(f"[Bot] fill_table_with_bots: 开始执行 牌桌 {table_id}")
            t = tables.TABLES.get(table_id)
            if not t:
                print(f"[Bot] fill_table_with_bots: 牌桌 {table_id} 不存在")
                return
            if t.get("status") != "waiting":
                print(f"[Bot] fill_table_with_bots: 牌桌 {table_id} 状态={t.get('status')}，跳过")
                return
            empty = [i for i, s in enumerate(t["seats"]) if s is None]
            if not empty:
                print(f"[Bot] fill_table_with_bots: 牌桌 {table_id} 无空位，直接尝试开局")
            else:
                added, err = add_bots_to_table(table_id, count=len(empty), auto_start=False)
                print(f"[Bot] fill_table_with_bots: 牌桌 {table_id} 添加 {len(added)} 个机器人")
                if err:
                    print(f"[Bot] fill_table_with_bots: add_bots_to_table 错误: {err}")
            t = tables.TABLES.get(table_id)
            seated = sum(1 for s in t["seats"] if s is not None) if t else 0
            if t and seated >= 2:
                ok, msg = tables.start_game(None, table_id, "")
                if ok:
                    print(f"[Bot] fill_table_with_bots: 牌桌 {table_id} 已开局")
                else:
                    print(f"[Bot] fill_table_with_bots: 牌桌 {table_id} 开局失败: {msg}")
            else:
                print(f"[Bot] fill_table_with_bots: 牌桌 {table_id} 人数={seated}，不足 2 人未开局")

            if not _socketio:
                return

            # 广播公共牌桌状态（让大厅/等待界面更新）
            pub = tables.get_table_state_public(table_id)
            if pub:
                _socketio.emit("table:state", pub, room=str(table_id), namespace="/")

            # 若游戏已开始，把真人玩家 sid 绑到 GameWrapper 并推送私有游戏状态
            t = tables.TABLES.get(table_id)
            if t and t.get("game"):
                synced = _sync_real_player_sids(table_id)
                if _socketio:
                    _socketio.emit("game:deal_phase", {"phase": "hole_cards"}, room=str(table_id), namespace="/")
                wrapper = t["game"]
                emotes = t.get("emotes")
                for seat, sid in synced:
                    state = wrapper.get_state(private_for_player_sid=sid, emotes=emotes)
                    _socketio.emit("game:state_update", state, room=sid, namespace="/")

        except Exception as e:
            print(f"[Bot] fill_table_with_bots error: {e}")
            import traceback
            traceback.print_exc()

    threading.Thread(target=_do, daemon=True).start()


def start(socketio_instance):
    """启动机器人后台线程，需传入 Flask-SocketIO 实例用于广播。"""
    global _socketio
    _socketio = socketio_instance
    t = threading.Thread(target=_bot_loop, daemon=True)
    t.start()
    print("[Bot] 后台线程已启动")

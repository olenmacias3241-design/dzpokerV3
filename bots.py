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

BOT_THINK_MIN = 0.8   # 机器人最短思考时间（秒）
BOT_THINK_MAX = 2.5   # 机器人最长思考时间（秒）
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


def _unique_bot_name():
    existing = {u["username"] for u in tables._tokens.values() if u.get("is_bot")}
    i = 1
    while True:
        name = f"机器人{i}号"
        if name not in existing:
            return name
        i += 1


# ──────────────────────────────────────────────
# 决策逻辑
# ──────────────────────────────────────────────

def _decide(game_state):
    """
    随机策略（用于测试）：
    - 可以过牌时：50% 过牌，30% 下注，20% 大额下注
    - 需要跟注时：40% 跟注，30% 弃牌，20% 加注，10% All-in
    - 下注金额随机：1-5倍 BB
    """
    atc = game_state.get("amount_to_call", 0)
    bb = game_state.get("bb", 10)
    
    # 随机下注倍数（1-5倍 BB）
    bet_multiplier = random.randint(1, 5)

    if atc == 0:
        # 可以过牌
        r = random.random()
        if r < 0.50:
            action, amount = "check", 0
        elif r < 0.80:
            action, amount = "bet", bb * bet_multiplier
        else:
            # 大额下注（5-10倍 BB）
            action, amount = "bet", bb * random.randint(5, 10)
    else:
        # 需要跟注
        r = random.random()
        if r < 0.40:
            action, amount = "call", 0
        elif r < 0.70:
            action, amount = "fold", 0
        elif r < 0.90:
            action, amount = "raise", atc + bb * bet_multiplier
        else:
            # 10% 概率 All-in
            action, amount = "all_in", 0
    
    print(f"[Bot] 决策: {action}, 金额: {amount}, 需跟注: {atc}, BB: {bb}")
    return action, amount


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
    # 对每个在线真人玩家发送含私牌的状态（含表情供展示）
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
                            _broadcast(tid)
                        except Exception as e:
                            print(f"[Bot] start_new_round error: {e}")
                            t["_bot_new_round_pending"] = False
                    threading.Thread(target=_start_new, daemon=True).start()
                    continue

                # 检查是否轮到机器人
                current_pid = gs.get("current_player_id")
                if not current_pid or not _is_bot(current_pid):
                    continue

                # 找到座位
                seat = next(
                    (i for i, pid in enumerate(wrapper._seat_to_pid) if pid == current_pid),
                    None
                )
                if seat is None:
                    continue

                # 获取机器人信息
                bot_name = tables._tokens.get(
                    next((tok for tok, u in tables._tokens.items() if u["user_id"] == current_pid), ""),
                    {}
                ).get("username", current_pid)
                
                print(f"[Bot] 牌桌 {tid}, 座位 {seat}, {bot_name} 开始思考...")

                # 模拟思考
                think_time = random.uniform(BOT_THINK_MIN, BOT_THINK_MAX)
                time.sleep(think_time)

                with _lock:
                    # 再次确认还轮到该机器人（避免在睡眠期间状态已改变）
                    if gs.get("current_player_id") != current_pid:
                        print(f"[Bot] {bot_name} 思考期间状态已改变，跳过")
                        continue
                    
                    action, amount = _decide(gs)
                    print(f"[Bot] 牌桌 {tid}, {bot_name} 执行: {action} {amount}")
                    
                    from database import SessionLocal
                    db = SessionLocal()
                    try:
                        ok, err = tables.process_action(db, tid, seat, action, amount)
                        if ok:
                            db.commit()
                            print(f"[Bot] {bot_name} 行动成功: {action} {amount}")
                        else:
                            db.rollback()
                            print(f"[Bot] {bot_name} 行动失败: {err}, 尝试兜底策略")
                            # 兜底：能过牌就过牌，否则跟注
                            fallback = "check" if gs.get("amount_to_call", 0) == 0 else "call"
                            ok2, err2 = tables.process_action(db, tid, seat, fallback, 0)
                            if ok2:
                                db.commit()
                                print(f"[Bot] {bot_name} 兜底成功: {fallback}")
                            else:
                                db.rollback()
                                print(f"[Bot] {bot_name} 兜底也失败: {err2}")
                    except Exception as e:
                        try:
                            db.rollback()
                        except Exception:
                            pass
                        print(f"[Bot] process_action db error: {e}")
                    finally:
                        try:
                            db.close()
                        except Exception:
                            pass

                _broadcast(tid)

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
    for _ in range(count):
        empty_seats = [i for i, uid in enumerate(t["seats"]) if uid is None]
        if not empty_seats:
            break
        name = _unique_bot_name()
        tok, uid = _create_bot(name)
        seat_idx = empty_seats[0]
        ok, err = tables.sit(table_id, tok, seat_idx, auto_start=False)
        if ok:
            added.append({"name": name, "seat": seat_idx})
        else:
            # 清理无效 token
            tables._tokens.pop(tok, None)

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
            t = tables.TABLES.get(table_id)
            if not t or t.get("status") != "waiting":
                return
            empty = [i for i, s in enumerate(t["seats"]) if s is None]
            if not empty:
                return
            # 先填满所有空位（不自动开局），再统一开局
            added, _ = add_bots_to_table(table_id, count=len(empty), auto_start=False)
            t = tables.TABLES.get(table_id)
            if t and sum(1 for s in t["seats"] if s is not None) >= 2:
                tables.start_game(None, table_id, "")

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
                wrapper = t["game"]
                emotes = t.get("emotes")
                for seat, sid in synced:
                    state = wrapper.get_state(private_for_player_sid=sid, emotes=emotes)
                    _socketio.emit("game:state_update", state, room=sid, namespace="/")

        except Exception as e:
            print(f"[Bot] fill_table_with_bots error: {e}")

    threading.Thread(target=_do, daemon=True).start()


def start(socketio_instance):
    """启动机器人后台线程，需传入 Flask-SocketIO 实例用于广播。"""
    global _socketio
    _socketio = socketio_instance
    t = threading.Thread(target=_bot_loop, daemon=True)
    t.start()
    print("[Bot] 后台线程已启动")

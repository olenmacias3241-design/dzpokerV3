# dzpokerV3/app.py - 多人在线牌桌：服务端监管所有牌桌，客户端仅监控单桌
# 本进程为唯一服务端：维护 TABLES、游戏逻辑、WebSocket 按桌推送。

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit, join_room

import tables
from database import SessionLocal
from core import game_logic
import config

app = Flask(__name__)
app.config["SECRET_KEY"] = getattr(__import__("config"), "SECRET_KEY", "dzpoker-secret")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


def _is_api_request():
    return request.path.startswith("/api/")


@app.errorhandler(500)
def _json_500(e):
    if _is_api_request():
        return jsonify({"error": "服务器错误"}), 500
    raise


def _game_state_for_seat(table_id, seat_index):
    """返回给某座位的游戏 state（含自己的底牌）。用临时 sid 让 get_state 识别。"""
    t = tables.TABLES.get(table_id)
    if not t or not t.get("game"):
        return None
    game = t["game"]
    fake_sid = "_seat_" + str(seat_index)
    if 0 <= seat_index < len(game.players):
        if game.players[seat_index]:
            game.players[seat_index].sid = fake_sid
    out = game.get_state(private_for_player_sid=fake_sid if 0 <= seat_index < 2 else None, emotes=t.get("emotes"))
    for p in game.players:
        if p:
            p.sid = None
    return out


# ---------- 页面 ----------
@app.route("/ping")
def ping():
    return "OK", 200, {"Content-Type": "text/plain"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/lobby")
def lobby():
    return render_template("lobby.html")


@app.route("/mall")
def mall():
    return render_template("mall.html")


# ---------- 登录 ----------
@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    """游客登录（仅用户名，无密码），返回 token。"""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    out = tables.login(username)
    return jsonify(out)


# ---------- 认证 API（注册/登录 + 密码，写数据库，返回 JWT）----------
@app.route("/api/auth/register", methods=["POST"])
def api_auth_register():
    db = SessionLocal()
    try:
        data = request.get_json() or {}
        # ... (validation)
        from services import auth
        user, err = auth.create_user(db, data.get("username"), data.get("password"), data.get("email"))
        if err:
            return jsonify({"ok": False, "message": err}), 400
        
        token = auth.encode_jwt(user.id)
        return jsonify({
            "ok": True, "userId": user.id, "token": token,
            "userProfile": auth.user_to_profile(user),
        })
    finally:
        db.close()



@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    db = SessionLocal()
    try:
        data = request.get_json() or {}
        from services import auth
        user, err = auth.verify_user(db, data.get("username"), data.get("password"))
        
        if err:
            return jsonify({"ok": False, "message": err}), 401
        
        token = auth.encode_jwt(user.id)
        return jsonify({
            "ok": True, "userId": user.id, "token": token,
            "userProfile": auth.user_to_profile(user),
        })
    finally:
        db.close()



def _auth_token():
    h = request.headers.get("Authorization") or ""
    if h.startswith("Bearer "):
        return h[7:].strip()
    if request.is_json and request.json:
        return request.json.get("token") or request.json.get("access_token")
    return request.form.get("token") or request.args.get("token")


@app.route("/api/auth/me")
def api_auth_me():
    token = _auth_token()
    if not token:
        return jsonify({"ok": False, "message": "未登录"}), 401
    user = tables.get_user(token)
    if not user:
        return jsonify({"ok": False, "message": "登录已失效"}), 401
    from services.auth import get_user_by_id, user_to_profile
    db = SessionLocal()
    try:
        db_user = get_user_by_id(db, user["user_id"])
    finally:
        db.close()
    if not db_user:
        return jsonify({"ok": True, "userProfile": {"userId": user["user_id"], "username": user["username"], "coinsBalance": 0}})
    return jsonify({"ok": True, "userProfile": user_to_profile(db_user)})


@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    return jsonify({"ok": True})


@app.route("/api/users/<int:user_id>")
def api_user_profile(user_id):
    from services.auth import get_user_by_id, user_to_profile
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"ok": False, "message": "用户不存在"}), 404
    return jsonify({"ok": True, "userProfile": user_to_profile(user)})


# ---------- 大厅 ----------
@app.route("/api/lobby/tables")
def api_lobby_tables():
    db = SessionLocal()
    try:
        tables_list = tables.list_tables(db)
        return jsonify({"tables": tables_list})
    finally:
        db.close()


@app.route("/api/lobby/tables", methods=["POST"])
def api_lobby_create_table():
    db = SessionLocal()
    try:
        data = request.get_json() or {}
        name = (data.get("tableName") or "").strip()
        sb = int(data.get("sb", 5))
        bb = int(data.get("bb", 10))
        max_players = data.get("maxPlayers", 6)
        
        t = tables.create_table(
            db=db,
            table_name=name or None,
            sb=sb,
            bb=bb,
            max_players=max_players,
        )
        
        # The response can be simplified as create_table now returns less info
        return jsonify({
            "tableId": t["table_id"],
            "tableName": t["table_name"],
            "blinds": t["blinds"],
            "maxPlayers": t["max_players"],
            "status": t["status"],
        })
    finally:
        db.close()


@app.route("/api/lobby/quick-start", methods=["POST"])
def api_lobby_quick_start():
    data = request.get_json() or {}
    token = data.get("token", "").strip()
    if not token or not tables.get_user(token):
        return jsonify({"message": "请先登录"}), 400
    for tid, t in list(tables.TABLES.items()):
        if t["status"] == "waiting" and None in t["seats"]:
            seat = t["seats"].index(None)
            ok, _ = tables.sit(tid, token, seat)
            if ok:
                return jsonify({"tableId": tid, "seatNumber": seat})
    t = tables.create_table()
    tables.sit(t["table_id"], token, 0)
    return jsonify({"tableId": t["table_id"], "seatNumber": 0})


# ---------- 牌桌 ----------
@app.route("/api/tables/<int:table_id>")
def api_table_state(table_id):
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip() or request.args.get("token", "")
    state, err = tables.get_table_state(table_id, token)
    if err:
        return jsonify({"error": err}), 404
    if state["status"] == "playing" and tables.TABLES.get(table_id, {}).get("game"):
        state["game_state"] = _game_state_for_seat(table_id, state["my_seat"])
    return jsonify(state)


@app.route("/api/tables/<int:table_id>/sit", methods=["POST"], strict_slashes=False)
def api_table_sit(table_id):
    db = SessionLocal()
    try:
        data = request.get_json(silent=True) or {}
        token = (data.get("token") or "").strip()
        seat = data.get("seat", 0)
        
        # sit function now requires a db session
        ok, msg = tables.sit(db, table_id, token, seat)

        if not ok:
            return jsonify({"error": msg}), 400

        # 玩家入座后自动让机器人填满剩余座位并开局
        import bots
        bots.fill_table_with_bots(table_id, delay=2.0)

        return jsonify({"tableId": table_id, "seatNumber": seat})
    except Exception as err:
        db.rollback()
        if _is_api_request():
            return jsonify({"error": "落座失败", "detail": str(err)}), 500
        raise
    finally:
        db.close()


@app.route("/api/tables/<int:table_id>/leave", methods=["POST"], strict_slashes=False)
def api_table_leave(table_id):
    """玩家离开座位（仅等待中有效），并广播牌桌状态。"""
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or request.headers.get("Authorization", "").replace("Bearer ", "") or "").strip()
    ok, msg = tables.leave(table_id, token)
    if not ok:
        return jsonify({"error": msg}), 400
    state = tables.get_table_state_public(table_id)
    if state:
        socketio.emit("table:state", state, room=str(table_id))
    return jsonify(state)


@app.route("/api/tables/<int:table_id>/start", methods=["POST"])
def api_table_start(table_id):
    db = SessionLocal()
    try:
        data = request.get_json() or {}
        token = data.get("token", "").strip()
        
        ok, msg = tables.start_game(db, table_id, token)
        
        if not ok:
            db.rollback()
            return jsonify({"error": msg}), 400
            
        db.commit() # Commit the status change
        
        state, _ = tables.get_table_state(table_id, token)
        if state and state.get("status") == "playing" and tables.TABLES.get(table_id, {}).get("game"):
            state["game_state"] = _game_state_for_seat(table_id, state["my_seat"])
        return jsonify(state)
    except Exception as e:
        db.rollback()
        return jsonify({"error": "开启牌局失败", "detail": str(e)}), 500
    finally:
        db.close()


# ---------- 对局 API（需 token）----------
@app.route("/api/tables/<int:table_id>/game_state")
def api_table_game_state(table_id):
    token = request.args.get("token", request.headers.get("Authorization", "").replace("Bearer ", ""))
    user = tables.get_user(token)
    if not user:
        return jsonify({"error": "请先登录"}), 401
    seat = tables.get_seat_index(table_id, user["user_id"])
    if seat < 0:
        return jsonify({"error": "您未在此桌"}), 403
    gs = _game_state_for_seat(table_id, seat)
    if gs is None:
        return jsonify({"error": "无对局"}), 404
    return jsonify(gs)


@app.route("/api/tables/<int:table_id>/start_round", methods=["POST"])
def api_table_start_round(table_id):
    data = request.get_json() or {}
    token = data.get("token", "").strip()
    user = tables.get_user(token)
    if not user:
        return jsonify({"error": "请先登录"}), 401
    seat = tables.get_seat_index(table_id, user["user_id"])
    if seat < 0:
        return jsonify({"error": "您未在此桌"}), 403
    t = tables.TABLES.get(table_id)
    if not t or not t.get("game"):
        return jsonify({"error": "无对局"}), 404
    t["game"].start_new_round()
    return jsonify(_game_state_for_seat(table_id, seat))


@app.route("/api/tables/<int:table_id>/action", methods=["POST"])
def api_table_action(table_id):
    db = SessionLocal()
    try:
        data = request.get_json() or {}
        token = data.get("token", "").strip()
        user = tables.get_user(token)
        if not user:
            return jsonify({"error": "请先登录"}), 401
        
        seat = tables.get_seat_index(table_id, user["user_id"])
        if seat < 0:
            return jsonify({"error": "您未在此桌"}), 403
            
        ok, msg = tables.process_action(
            db, table_id, seat, data.get("action"), data.get("amount", 0)
        )
        
        if not ok:
            db.rollback()
            return jsonify({"error": msg}), 400
            
        db.commit()
        return jsonify(_game_state_for_seat(table_id, seat))
    except Exception as e:
        db.rollback()
        return jsonify({"error": "执行动作失败", "detail": str(e)}), 500
    finally:
        db.close()


@app.route("/api/tables/<int:table_id>/deal_next", methods=["POST"])
def api_table_deal_next(table_id):
    data = request.get_json() or {}
    token = data.get("token", "").strip()
    user = tables.get_user(token)
    if not user:
        return jsonify({"error": "请先登录"}), 401
    seat = tables.get_seat_index(table_id, user["user_id"])
    if seat < 0:
        return jsonify({"error": "您未在此桌"}), 403
    t = tables.TABLES.get(table_id)
    if t and t.get("game") and getattr(t["game"], "pending_insurance", None):
        ok, msg = tables.resolve_insurance(table_id, token, 0)
        if not ok and msg:
            return jsonify({"error": msg}), 400
    else:
        tables.deal_next_street(table_id)
    return jsonify(_game_state_for_seat(table_id, seat))


@app.route("/api/tables/<int:table_id>/insurance", methods=["POST"])
def api_table_insurance(table_id):
    """买保险（amount>0）或放弃（amount=0）。仅领先玩家可操作。"""
    data = request.get_json() or {}
    token = data.get("token", "").strip()
    amount = data.get("amount", 0)
    user = tables.get_user(token)
    if not user:
        return jsonify({"error": "请先登录"}), 401
    seat = tables.get_seat_index(table_id, user["user_id"])
    if seat < 0:
        return jsonify({"error": "您未在此桌"}), 403
    ok, msg = tables.resolve_insurance(table_id, token, amount)
    if not ok:
        return jsonify({"error": msg or "操作失败"}), 400
    return jsonify(_game_state_for_seat(table_id, seat))


@app.route("/api/tables/<int:table_id>/emote", methods=["POST"])
def api_table_emote(table_id):
    data = request.get_json() or {}
    token = data.get("token", "").strip()
    user = tables.get_user(token)
    if not user:
        return jsonify({"error": "请先登录"}), 401
    seat = tables.get_seat_index(table_id, user["user_id"])
    if seat < 0:
        return jsonify({"error": "您未在此桌"}), 403
    tables.set_emote(table_id, seat, data.get("emote", ""))
    return jsonify(_game_state_for_seat(table_id, seat))


@app.route("/api/tables/<int:table_id>/add_bot", methods=["POST"])
def api_add_bot(table_id):
    """向牌桌添加机器人。body: {count: 1, autoStart: true}"""
    import bots
    data = request.get_json() or {}
    count = max(1, min(int(data.get("count", 1)), 4))
    auto_start = bool(data.get("autoStart", False))
    added, err = bots.add_bots_to_table(table_id, count=count, auto_start=auto_start)
    if err:
        return jsonify({"error": err}), 400
    state = tables.get_table_state_public(table_id)
    socketio.emit("table:state", state, room=str(table_id))
    return jsonify({"added": added, "table": state})


@app.route("/api/mall/products")
def api_mall_products():
    return jsonify({"products": [
        {"id": "t1", "name": "经典绿绒", "category": "table_theme", "price": 0, "icon": "🃏"},
        {"id": "c1", "name": "标准红背", "category": "card_back", "price": 0, "icon": "🂠"},
        {"id": "e1", "name": "基础表情", "category": "emote", "price": 0, "icon": "😊"},
    ]})


# ---------- 俱乐部 API ----------
@app.route("/api/clubs", methods=["GET"])
def api_list_clubs():
    """列出所有俱乐部"""
    from services import clubs
    db = SessionLocal()
    try:
        club_list = clubs.list_clubs(db)
        return jsonify({"clubs": [
            {"id": c.id, "name": c.name, "description": c.description, "owner_id": c.owner_id}
            for c in club_list
        ]})
    finally:
        db.close()


@app.route("/api/clubs", methods=["POST"])
def api_create_club():
    """创建俱乐部"""
    from services import clubs
    db = SessionLocal()
    try:
        data = request.get_json() or {}
        token = data.get("token", "").strip()
        user = tables.get_user(token)
        if not user:
            return jsonify({"error": "请先登录"}), 401
        
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "俱乐部名称不能为空"}), 400
        
        club = clubs.create_club(db, name, user["user_id"], data.get("description"))
        return jsonify({
            "id": club.id,
            "name": club.name,
            "description": club.description,
            "owner_id": club.owner_id
        })
    finally:
        db.close()


@app.route("/api/clubs/<int:club_id>")
def api_get_club(club_id):
    """获取俱乐部详情"""
    from services import clubs
    db = SessionLocal()
    try:
        club = clubs.get_club(db, club_id)
        if not club:
            return jsonify({"error": "俱乐部不存在"}), 404
        
        members = clubs.get_club_members(db, club_id)
        return jsonify({
            "id": club.id,
            "name": club.name,
            "description": club.description,
            "owner_id": club.owner_id,
            "members": [{"user_id": m.user_id, "role": m.role} for m in members]
        })
    finally:
        db.close()


@app.route("/api/clubs/<int:club_id>/join", methods=["POST"])
def api_join_club(club_id):
    """加入俱乐部"""
    from services import clubs
    db = SessionLocal()
    try:
        data = request.get_json() or {}
        token = data.get("token", "").strip()
        user = tables.get_user(token)
        if not user:
            return jsonify({"error": "请先登录"}), 401
        
        member, err = clubs.join_club(db, club_id, user["user_id"])
        if err:
            return jsonify({"error": err}), 400
        
        return jsonify({"message": "加入成功", "club_id": club_id})
    finally:
        db.close()


# ---------- WebSocket ----------
@socketio.on("disconnect")
def ws_disconnect():
    table_id = tables.leave_by_sid(request.sid)
    if table_id is not None:
        state = tables.get_table_state_public(table_id)
        if state:
            emit("table:state", state, room=str(table_id))


@socketio.on("join_table")
def ws_join_table(data):
    table_id = data.get("table_id")
    token = data.get("token", "").strip()
    if table_id is None or not token:
        emit("error", {"message": "缺少 table_id 或 token"})
        return
    table_id = int(table_id)
    user = tables.get_user(token)
    if not user:
        emit("error", {"message": "登录已失效，请重新登录"})
        return
    seat = tables.get_seat_index(table_id, user["user_id"])
    if seat < 0:
        emit("error", {"message": "您未在此桌入座"})
        return
    join_room(str(table_id))
    tables.bind_sid_to_seat(table_id, request.sid, seat)
    t = tables.TABLES.get(table_id)
    if t and t.get("game"):
        game = t["game"]
        game.players[seat].sid = request.sid
        state = game.get_state(private_for_player_sid=request.sid, emotes=t.get("emotes"))
        emit("game:state_update", state)
    else:
        state, _ = tables.get_table_state(table_id, token)
        emit("table:state", state)


def _broadcast_table_state(table_id):
    t = tables.TABLES.get(table_id)
    if not t or not t.get("game"):
        return
    game = t["game"]
    emotes = t.get("emotes")
    for i, p in enumerate(game.players):
        sid = getattr(p, "sid", None)
        if sid:
            state = game.get_state(private_for_player_sid=sid, emotes=emotes)
            emit("game:state_update", state, room=sid)


@socketio.on("game:action")
def ws_game_action(data):
    table_id, seat = tables.get_table_and_seat_by_sid(request.sid)
    if table_id is None:
        emit("error", {"message": "未加入牌桌"})
        return
    
    db = SessionLocal()
    try:
        ok, msg = tables.process_action(
            db, table_id, seat, data.get("action"), data.get("amount", 0)
        )
        if not ok:
            db.rollback()
            emit("error", {"message": msg or "操作失败"})
            return
        db.commit()
        _broadcast_table_state(table_id)
    finally:
        db.close()


@socketio.on("deal_next_street")
def ws_deal_next(data):
    table_id, seat = tables.get_table_and_seat_by_sid(request.sid)
    if table_id is None:
        emit("error", {"message": "未加入牌桌"})
        return
    t = tables.TABLES.get(table_id)
    if t and t.get("game") and getattr(t["game"], "pending_insurance", None):
        token = (data or {}).get("token", "").strip()
        ok, msg = tables.resolve_insurance(table_id, token, 0)
        if not ok and msg:
            emit("error", {"message": msg})
            return
    else:
        tables.deal_next_street(table_id)
    _broadcast_table_state(table_id)


@socketio.on("insurance")
def ws_insurance(data):
    table_id, seat = tables.get_table_and_seat_by_sid(request.sid)
    if table_id is None:
        emit("error", {"message": "未加入牌桌"})
        return
    token = (data or {}).get("token", "").strip()
    amount = int((data or {}).get("amount", 0) or 0)
    ok, msg = tables.resolve_insurance(table_id, token, amount)
    if not ok:
        emit("error", {"message": msg or "操作失败"})
        return
    _broadcast_table_state(table_id)


@socketio.on("start_round")
def ws_start_round(data):
    table_id, seat = tables.get_table_and_seat_by_sid(request.sid)
    if table_id is None:
        emit("error", {"message": "未加入牌桌"})
        return
    t = tables.TABLES.get(table_id)
    if not t or not t.get("game"):
        emit("error", {"message": "无对局"})
        return
    t["game"].start_new_round()
    _broadcast_table_state(table_id)


@socketio.on("game:emote")
def ws_emote(data):
    table_id, seat = tables.get_table_and_seat_by_sid(request.sid)
    if table_id is None:
        return
    tables.set_emote(table_id, seat, data.get("emote", ""))
    _broadcast_table_state(table_id)


# ---------- 回放 API ----------
@app.route("/api/replay/hands")
def api_replay_hands():
    """获取牌局列表"""
    user_id = request.args.get("user_id")
    table_id = request.args.get("table_id")
    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))
    
    db = SessionLocal()
    try:
        from database.models import GameHand, HandParticipant
        
        query = db.query(GameHand)
        
        if user_id:
            query = query.join(HandParticipant).filter(
                HandParticipant.user_id == user_id
            )
        
        if table_id:
            query = query.filter(GameHand.table_id == int(table_id))
        
        total = query.count()
        hands = query.order_by(GameHand.start_time.desc()).offset(offset).limit(limit).all()
        
        result = []
        for hand in hands:
            participants = db.query(HandParticipant).filter_by(hand_id=hand.id).all()
            result.append({
                "hand_id": hand.id,
                "table_id": hand.table_id,
                "start_time": hand.start_time.isoformat() if hand.start_time else None,
                "final_pot": hand.final_pot_size or 0,
                "participants": [
                    {
                        "user_id": p.user_id,
                        "seat": p.seat_number,
                        "win_amount": p.win_amount or 0
                    }
                    for p in participants
                ]
            })
        
        return jsonify({"hands": result, "total": total})
    
    except Exception as e:
        print(f"[Replay] 获取牌局列表失败: {e}")
        return jsonify({"error": "获取牌局列表失败", "detail": str(e)}), 500
    
    finally:
        db.close()


@app.route("/api/replay/hands/<int:hand_id>")
def api_replay_hand_detail(hand_id):
    """获取牌局详情"""
    db = SessionLocal()
    try:
        from database.models import GameHand, HandParticipant
        
        hand = db.query(GameHand).filter_by(id=hand_id).first()
        if not hand:
            return jsonify({"error": "牌局不存在"}), 404
        
        participants = db.query(HandParticipant).filter_by(hand_id=hand_id).all()
        
        # 获取行动记录
        actions = []
        if HandAction:
            actions = db.query(HandAction).filter_by(hand_id=hand_id).order_by(HandAction.action_order).all()
        
        return jsonify({
            "hand_id": hand.id,
            "table_id": hand.table_id,
            "start_time": hand.start_time.isoformat() if hand.start_time else None,
            "community_cards": hand.community_cards.split(",") if hand.community_cards else [],
            "final_pot": hand.final_pot_size or 0,
            "participants": [
                {
                    "user_id": p.user_id,
                    "seat": p.seat_number,
                    "hole_cards": p.hole_cards.split(",") if p.hole_cards else [],
                    "win_amount": p.win_amount or 0
                }
                for p in participants
            ],
            "actions": [
                {
                    "action_id": a.id,
                    "user_id": a.user_id,
                    "action": a.action_type,
                    "amount": a.amount,
                    "stage": a.stage,
                    "order": a.action_order
                }
                for a in actions
            ]
        })
    
    except Exception as e:
        print(f"[Replay] 获取牌局详情失败: {e}")
        return jsonify({"error": "获取牌局详情失败", "detail": str(e)}), 500
    
    finally:
        db.close()


if __name__ == "__main__":
    # 启动机器人后台线程
    import bots
    bots.start(socketio)
    
    socketio.run(app, host="0.0.0.0", port=5002, debug=True, allow_unsafe_werkzeug=True)


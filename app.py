# dzpokerV3/app.py - 多人在线牌桌：服务端监管所有牌桌，客户端仅监控单桌
# 本进程为唯一服务端：维护 TABLES、游戏逻辑、WebSocket 按桌推送。

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime

import tables
from database import SessionLocal
from core import game_logic
import config

app = Flask(__name__)
app.config["SECRET_KEY"] = getattr(__import__("config"), "SECRET_KEY", "dzpoker-secret")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# 机器人后台线程：与 __main__ 中重复调用 start 无害，保证无论用 python app.py 还是 flask run 都能轮询下注
try:
    import bots
    bots.start(socketio)
except Exception as e:
    print("[Startup] 机器人模块启动跳过:", e)


def _is_api_request():
    return request.path.startswith("/api/")


def _ensure_default_table():
    """若没有任何牌桌则创建 1 号桌，避免直接访问 /?table=1 时 404。"""
    if not tables.TABLES:
        t = tables.create_table(db=None, table_name="牌桌 1", sb=5, bb=10, max_players=6)
        print(f"[Startup] 已创建默认牌桌: {t['table_id']} ({t.get('table_name', '')})")


@app.before_request
def _before_request_ensure_table():
    _ensure_default_table()


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


@app.route("/favicon.ico")
def favicon():
    """避免浏览器请求 /favicon.ico 时返回 404。"""
    return "", 204


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/lobby")
def lobby():
    return render_template("lobby.html")


@app.route("/mall")
def mall():
    return render_template("mall.html")


@app.route("/friends")
def friends():
    return render_template("friends.html")


@app.route("/news")
def news():
    return render_template("news.html")


# ---------- 登录 ----------
@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/profile")
def profile_page():
    return render_template("profile.html")


@app.route("/settings")
def settings_page():
    return render_template("settings.html")


@app.route("/clubs")
def clubs_page():
    return render_template("clubs.html")


@app.route("/club/<int:club_id>")
def club_detail_page(club_id):
    return render_template("club_detail.html", club_id=club_id)


@app.route("/tournaments")
def tournaments_page():
    return render_template("tournaments.html")


@app.route("/tournament/<int:tournament_id>")
def tournament_detail_page(tournament_id):
    return render_template("tournament_detail.html", tournament_id=tournament_id)


@app.route("/tournament/<int:tournament_id>/lobby")
def tournament_lobby_page(tournament_id):
    return render_template("tournament_lobby.html", tournament_id=tournament_id)


# ---------- API: 登录/注册 ----------
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
        # 将 JWT token 注册到 _tokens，使游戏操作（入座/下注等）能识别注册用户
        tables._tokens[token] = {
            "user_id": str(user.id),
            "username": user.username or f"user_{user.id}",
            "stack": int(user.coins_balance or 10000),
        }
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
        # 将 JWT token 注册到 _tokens，使游戏操作（入座/下注等）能识别注册用户
        tables._tokens[token] = {
            "user_id": str(user.id),
            "username": user.username or f"user_{user.id}",
            "stack": int(user.coins_balance or 10000),
        }
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
    # 游客 token：user_id 为字符串（如 guest_xxx），不查 DB，直接返回内存中的 profile
    if not isinstance(user.get("user_id"), int):
        return jsonify({
            "ok": True,
            "userProfile": {
                "userId": user["user_id"],
                "username": user.get("username") or "游客",
                "coinsBalance": user.get("coinsBalance", user.get("stack", 0)),
            }
        })
    from services.auth import get_user_by_id, user_to_profile, get_user_stats
    try:
        uid = int(user["user_id"])
    except (TypeError, ValueError):
        return jsonify({"ok": True, "userProfile": {"userId": user["user_id"], "username": user.get("username"), "coinsBalance": 0}})
    db = SessionLocal()
    try:
        db_user = get_user_by_id(db, uid)
        if not db_user:
            return jsonify({"ok": True, "userProfile": {"userId": user["user_id"], "username": user.get("username"), "coinsBalance": 0}})
        stats = get_user_stats(db, uid)
        return jsonify({"ok": True, "userProfile": user_to_profile(db_user, stats)})
    finally:
        db.close()


@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    return jsonify({"ok": True})


# 前端 UI 配置（主题、音效等）持久化，无 DB 时用内存存储，避免 404
_ui_config_store = {}


def _ui_config_token():
    auth = request.headers.get("Authorization") or ""
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return (request.get_json() or {}).get("token") or request.args.get("token") or ""


@app.route("/api/users/me/ui-config", methods=["GET"])
def api_users_me_ui_config_get():
    token = _ui_config_token()
    if not token:
        return jsonify({}), 200
    cfg = _ui_config_store.get(token, {})
    return jsonify(cfg), 200


@app.route("/api/users/me/ui-config", methods=["PUT"])
def api_users_me_ui_config_put():
    token = _ui_config_token()
    if not token:
        return jsonify({"ok": True}), 200
    data = request.get_json() or {}
    _ui_config_store[token] = {k: data[k] for k in ("theme", "uiVersion", "fontSize", "skin", "animationEnabled", "soundEnabled", "reducedMotion") if k in data}
    return jsonify(_ui_config_store.get(token, {})), 200


@app.route("/api/users/<int:user_id>")
def api_user_profile(user_id):
    from services.auth import get_user_by_id, user_to_profile, get_user_stats
    db = SessionLocal()
    try:
        user = get_user_by_id(db, user_id)
        if not user:
            return jsonify({"ok": False, "message": "用户不存在"}), 404
        stats = get_user_stats(db, user_id)
        return jsonify({"ok": True, "userProfile": user_to_profile(user, stats)})
    finally:
        db.close()


# ---------- 通用认证 helper ----------
def _current_user_id(require_db_user=False):
    """从 Bearer JWT 或内存 token 解析 user_id；require_db_user=True 时只接受整数 uid。"""
    token = _auth_token()
    if not token:
        return None, "未登录"
    from services import auth as _auth
    payload = _auth.decode_jwt(token)
    if payload and "user_id" in payload:
        return int(payload["user_id"]), None
    user = tables.get_user(token)
    if user:
        if require_db_user:
            return None, "需要账号登录"
        return user.get("user_id"), None
    return None, "未登录或 token 已过期"


# ---------- 锦标赛（docs/requirements/12） ----------
def _tournament_user_id():
    """从 JWT 或 token 解析出 DB user_id（整数），用于锦标赛报名。"""
    token = _auth_token()
    if not token:
        return None, "未登录"
    from services import auth
    payload = auth.decode_jwt(token)
    if payload and "user_id" in payload:
        return int(payload["user_id"]), None
    user = tables.get_user(token)
    if user and isinstance(user.get("user_id"), int):
        return user["user_id"], None
    return None, "锦标赛需使用账号登录"


@app.route("/api/tournaments")
def api_tournaments_list():
    """赛事列表；支持 ?status= &type= 筛选。"""
    db = SessionLocal()
    try:
        from services import tournaments
        status = request.args.get("status")
        type_ = request.args.get("type")
        lst = tournaments.list_tournaments(db, status=status, type_=type_)
        out = []
        for t in lst:
            reg_count = tournaments.count_registrations(db, t.id)
            starts_at = t.starts_at.isoformat() if t.starts_at else None
            out.append({
                "id": t.id,
                "name": t.name,
                "type": t.type,
                "status": t.status,
                # snake_case（兼容旧模板）
                "buy_in": t.buy_in,
                "fee": t.fee,
                "starting_stack": t.starting_stack,
                "max_players": t.max_players,
                "min_players_to_start": t.min_players_to_start,
                "registered_count": reg_count,
                "starts_at": starts_at,
                # camelCase（供 tournaments.js 使用）
                "buyIn": t.buy_in,
                "startingStack": t.starting_stack,
                "maxPlayers": t.max_players,
                "minPlayersToStart": t.min_players_to_start,
                "registeredCount": reg_count,
                "startsAt": starts_at,
            })
        return jsonify(out)
    finally:
        db.close()


@app.route("/api/tournaments/<int:tournament_id>")
def api_tournament_detail(tournament_id):
    """赛事详情与当前状态。"""
    db = SessionLocal()
    try:
        from services import tournaments
        from database import TournamentRegistration
        uid_for_state, _ = _current_user_id()
        try:
            uid_for_state = int(uid_for_state) if uid_for_state else None
        except (ValueError, TypeError):
            uid_for_state = None
        state = tournaments.get_tournament_state(db, tournament_id, user_id=uid_for_state)
        if not state:
            return jsonify({"error": "赛事不存在"}), 404
        # 附加 camelCase 别名
        state["buyIn"] = state.get("buy_in")
        state["startingStack"] = state.get("starting_stack")
        state["maxPlayers"] = state.get("max_players")
        state["registeredCount"] = state.get("registered_count")
        state["startsAt"] = state.get("starts_at")
        # 当前用户是否已报名
        user_id, _ = _current_user_id()
        state["myRegistration"] = False
        if user_id:
            try:
                uid = int(user_id)
                reg = db.query(TournamentRegistration).filter_by(
                    tournament_id=tournament_id, user_id=uid
                ).filter(
                    TournamentRegistration.unregistered_at.is_(None),
                    TournamentRegistration.refunded_at.is_(None),
                ).first()
                state["myRegistration"] = bool(reg)
            except Exception:
                pass
        return jsonify(state)
    finally:
        db.close()


@app.route("/api/tournaments/<int:tournament_id>/register", methods=["POST"])
def api_tournament_register(tournament_id):
    """报名：扣 buy_in + fee。"""
    user_id, err = _tournament_user_id()
    if err:
        return jsonify({"error": err}), 401
    db = SessionLocal()
    try:
        from services import tournaments
        from services.auth import get_user_by_id
        user = get_user_by_id(db, user_id)
        balance = (user.coins_balance if user else 0) or 0
        reg, err = tournaments.register(db, tournament_id, user_id, balance)
        if err:
            return jsonify({"error": err}), 400
        state = tournaments.get_tournament_state(db, tournament_id)
        return jsonify({"ok": True, "tournament": state})
    finally:
        db.close()


@app.route("/api/tournaments/<int:tournament_id>/unregister", methods=["POST"])
def api_tournament_unregister(tournament_id):
    """取消报名（仅 Registration 阶段），退款。"""
    user_id, err = _tournament_user_id()
    if err:
        return jsonify({"error": err}), 401
    db = SessionLocal()
    try:
        from services import tournaments
        ok, err = tournaments.unregister(db, tournament_id, user_id)
        if not ok:
            return jsonify({"error": err or "取消失败"}), 400
        return jsonify({"ok": True})
    finally:
        db.close()


@app.route("/api/admin/tournaments", methods=["POST"])
def api_admin_create_tournament():
    """管理员创建 SNG 或 MTT 赛事。"""
    db = SessionLocal()
    try:
        from services import tournaments
        data = request.get_json() or {}
        type_ = data.get("type", "SNG")
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "赛事名称不能为空"}), 400
        buy_in = int(data.get("buy_in", 0))
        fee = int(data.get("fee", 0))
        starting_stack = int(data.get("starting_stack", 10000))
        max_players = int(data.get("max_players", 9))
        min_to_start = int(data.get("min_players_to_start", 2))
        blind_levels = data.get("blind_levels") or []
        payout_percents = data.get("payout_percents") or []
        if type_ == "MTT":
            starts_at_str = data.get("starts_at")
            starts_at = None
            if starts_at_str:
                from datetime import datetime as _dt
                try:
                    starts_at = _dt.fromisoformat(starts_at_str.replace("Z", "+00:00"))
                except Exception:
                    pass
            late_reg = int(data.get("late_reg_minutes", 30))
            t = tournaments.create_mtt(
                db, name, buy_in, fee, starting_stack,
                max_players=max_players, min_to_start=min_to_start,
                starts_at=starts_at, late_reg_minutes=late_reg,
                blind_levels=blind_levels, payout_percents=payout_percents,
            )
        else:
            t = tournaments.create_sng(
                db, name, buy_in, fee, starting_stack,
                max_players=max_players, min_to_start=min_to_start,
                blind_levels=blind_levels, payout_percents=payout_percents,
            )
        return jsonify({"ok": True, "id": t.id, "name": t.name, "type": t.type})
    finally:
        db.close()


@app.route("/api/admin/tournaments/<int:tournament_id>/start", methods=["POST"])
def api_admin_start_tournament(tournament_id):
    """管理员手动开赛（测试用），为真实玩家分配座位并补充机器人。"""
    db = SessionLocal()
    try:
        from services import tournaments
        import bots as _bots
        ok, result = tournaments.start_tournament_game(db, tournament_id, tables, _bots)
        if not ok:
            return jsonify({"error": result}), 400
        return jsonify({"ok": True, "game_table_id": result})
    finally:
        db.close()


# ---------- 约局（docs/requirements/13_scheduled_game_mode.md） ----------
def _scheduled_user_id():
    """从 JWT 或 token 解析出 DB user_id，用于约局接口。"""
    token = _auth_token()
    if not token:
        return None, "未登录"
    from services import auth
    payload = auth.decode_jwt(token)
    if payload and "user_id" in payload:
        return int(payload["user_id"]), None
    user = tables.get_user(token)
    if user and isinstance(user.get("user_id"), int):
        return user["user_id"], None
    return None, "约局需使用账号登录"


@app.route("/api/scheduled-games", methods=["GET"])
def api_scheduled_games_list():
    """约局列表；Query: clubId=, status=, mine=true"""
    from services import scheduled_games
    db = SessionLocal()
    try:
        started = scheduled_games.check_and_start_games(db)
        for sg_id, table_id in started:
            socketio.emit("scheduled:table_created", {"scheduledGameId": sg_id, "tableId": table_id}, room=f"scheduled_{sg_id}")
        club_id = request.args.get("clubId", type=int)
        status = request.args.get("status")
        mine = request.args.get("mine", "").lower() in ("1", "true", "yes")
        mine_user_id = None
        if mine:
            uid, err = _scheduled_user_id()
            if err:
                return jsonify({"error": err}), 401
            mine_user_id = uid
        limit = min(100, max(1, request.args.get("limit", type=int) or 50))
        offset = max(0, request.args.get("offset", type=int) or 0)
        lst = scheduled_games.list_games(db, club_id=club_id, status=status, mine_user_id=mine_user_id, limit=limit, offset=offset)
        out = []
        for sg in lst:
            n = scheduled_games.count_players(db, sg.id)
            sb, bb = scheduled_games._parse_blinds(sg.blinds_json)
            out.append({
                "scheduledGameId": sg.id,
                "title": sg.title,
                "hostUserId": sg.host_user_id,
                "clubId": sg.club_id,
                "startAt": sg.start_at.isoformat() if sg.start_at else None,
                "startRule": sg.start_rule,
                "minPlayers": sg.min_players,
                "maxPlayers": sg.max_players,
                "blindsDisplay": f"{sb}/{bb}",
                "status": sg.status,
                "registeredCount": n,
                "tableId": sg.table_id,
            })
        return jsonify(out)
    finally:
        db.close()


@app.route("/api/scheduled-games", methods=["POST"])
def api_scheduled_games_create():
    """创建约局"""
    from services import scheduled_games
    user_id, err = _scheduled_user_id()
    if err:
        return jsonify({"error": err}), 401
    db = SessionLocal()
    try:
        data = request.get_json() or {}
        title = (data.get("title") or "").strip()
        start_at_raw = data.get("startAt")
        if not start_at_raw:
            return jsonify({"error": "缺少 startAt"}), 400
        try:
            if hasattr(start_at_raw, "year"):
                start_at = start_at_raw
            else:
                s = str(start_at_raw).strip().replace("Z", "+00:00")
                start_at = datetime.fromisoformat(s)
        except (ValueError, TypeError):
            return jsonify({"error": "startAt 格式无效，请使用 ISO 格式如 2026-03-15T21:00:00"}), 400
        min_players = int(data.get("minPlayers", 2))
        max_players = int(data.get("maxPlayers", 6))
        blinds = data.get("blinds")
        if blinds is None:
            blinds = "5/10"
        elif isinstance(blinds, dict):
            pass
        else:
            blinds = str(blinds)
        sg, err = scheduled_games.create(
            db, user_id, title, start_at, min_players, max_players, blinds,
            start_rule=data.get("startRule"),
            club_id=data.get("clubId"),
            buy_in_min=data.get("buyInMin"),
            buy_in_max=data.get("buyInMax"),
            initial_chips=data.get("initialChips"),
            password=data.get("password"),
        )
        if err:
            return jsonify({"error": err}), 400
        detail = scheduled_games.to_detail(db, sg, request.host_url or "")
        return jsonify(detail)
    finally:
        db.close()


@app.route("/api/scheduled-games/<int:scheduled_game_id>")
def api_scheduled_game_detail(scheduled_game_id):
    """约局详情（含参与名单、倒计时）；会触发开赛检查"""
    from services import scheduled_games
    db = SessionLocal()
    try:
        started = scheduled_games.check_and_start_games(db)
        for sg_id, table_id in started:
            socketio.emit("scheduled:table_created", {"scheduledGameId": sg_id, "tableId": table_id}, room=f"scheduled_{sg_id}")
        sg = scheduled_games.get(db, scheduled_game_id)
        if not sg:
            return jsonify({"error": "约局不存在"}), 404
        base = request.host_url or ""
        return jsonify(scheduled_games.to_detail(db, sg, base))
    finally:
        db.close()


@app.route("/api/scheduled-games/<int:scheduled_game_id>", methods=["PUT"])
def api_scheduled_game_update(scheduled_game_id):
    """编辑约局（仅局主，Scheduled）"""
    from services import scheduled_games
    user_id, err = _scheduled_user_id()
    if err:
        return jsonify({"error": err}), 401
    db = SessionLocal()
    try:
        data = request.get_json() or {}
        kwargs = {}
        if "title" in data:
            kwargs["title"] = (data.get("title") or "").strip()
        if "startAt" in data:
            try:
                v = data["startAt"]
                if hasattr(v, "year"):
                    kwargs["start_at"] = v
                else:
                    s = str(v).strip().replace("Z", "+00:00")
                    kwargs["start_at"] = datetime.fromisoformat(s)
            except (ValueError, TypeError):
                return jsonify({"error": "startAt 格式无效"}), 400
        if "minPlayers" in data:
            kwargs["min_players"] = int(data["minPlayers"])
        if "maxPlayers" in data:
            kwargs["max_players"] = int(data["maxPlayers"])
        if "blinds" in data:
            kwargs["blinds"] = data["blinds"]
        ok, err = scheduled_games.update(db, scheduled_game_id, user_id, **kwargs)
        if not ok:
            return jsonify({"error": err}), 400
        sg = scheduled_games.get(db, scheduled_game_id)
        socketio.emit("scheduled:updated", scheduled_games.to_detail(db, sg, request.host_url or ""), room=f"scheduled_{scheduled_game_id}")
        return jsonify(scheduled_games.to_detail(db, sg, request.host_url or ""))
    finally:
        db.close()


@app.route("/api/scheduled-games/<int:scheduled_game_id>", methods=["DELETE"])
def api_scheduled_game_cancel(scheduled_game_id):
    """取消约局（仅局主）"""
    from services import scheduled_games
    user_id, err = _scheduled_user_id()
    if err:
        return jsonify({"error": err}), 401
    db = SessionLocal()
    try:
        ok, err = scheduled_games.cancel(db, scheduled_game_id, user_id)
        if not ok:
            return jsonify({"error": err}), 400
        socketio.emit("scheduled:cancelled", {"scheduledGameId": scheduled_game_id}, room=f"scheduled_{scheduled_game_id}")
        return jsonify({"ok": True})
    finally:
        db.close()


@app.route("/api/scheduled-games/<int:scheduled_game_id>/register", methods=["POST"])
def api_scheduled_game_register(scheduled_game_id):
    """报名"""
    from services import scheduled_games
    user_id, err = _scheduled_user_id()
    if err:
        return jsonify({"error": err}), 401
    db = SessionLocal()
    try:
        data = request.get_json() or {}
        ok, err = scheduled_games.register(db, scheduled_game_id, user_id, password=data.get("password"))
        if not ok:
            return jsonify({"error": err}), 400
        sg = scheduled_games.get(db, scheduled_game_id)
        socketio.emit("scheduled:updated", scheduled_games.to_detail(db, sg, request.host_url or ""), room=f"scheduled_{scheduled_game_id}")
        return jsonify(scheduled_games.to_detail(db, sg, request.host_url or ""))
    finally:
        db.close()


@app.route("/api/scheduled-games/<int:scheduled_game_id>/unregister", methods=["POST"])
def api_scheduled_game_unregister(scheduled_game_id):
    """取消报名"""
    from services import scheduled_games
    user_id, err = _scheduled_user_id()
    if err:
        return jsonify({"error": err}), 401
    db = SessionLocal()
    try:
        ok, err = scheduled_games.unregister(db, scheduled_game_id, user_id)
        if not ok:
            return jsonify({"error": err}), 400
        sg = scheduled_games.get(db, scheduled_game_id)
        socketio.emit("scheduled:updated", scheduled_games.to_detail(db, sg, request.host_url or ""), room=f"scheduled_{scheduled_game_id}")
        return jsonify({"ok": True})
    finally:
        db.close()


@app.route("/api/scheduled-games/<int:scheduled_game_id>/players")
def api_scheduled_game_players(scheduled_game_id):
    """参与名单"""
    from services import scheduled_games
    db = SessionLocal()
    try:
        sg = scheduled_games.get(db, scheduled_game_id)
        if not sg:
            return jsonify({"error": "约局不存在"}), 404
        return jsonify({"players": scheduled_games.get_players(db, scheduled_game_id, sg.host_user_id)})
    finally:
        db.close()


@app.route("/api/scheduled-games/<int:scheduled_game_id>/players/<int:user_id>/kick", methods=["POST"])
def api_scheduled_game_kick(scheduled_game_id, user_id):
    """踢出（仅局主）"""
    from services import scheduled_games
    operator_id, err = _scheduled_user_id()
    if err:
        return jsonify({"error": err}), 401
    db = SessionLocal()
    try:
        ok, err = scheduled_games.kick(db, scheduled_game_id, operator_id, user_id)
        if not ok:
            return jsonify({"error": err}), 400
        sg = scheduled_games.get(db, scheduled_game_id)
        socketio.emit("scheduled:updated", scheduled_games.to_detail(db, sg, request.host_url or ""), room=f"scheduled_{scheduled_game_id}")
        return jsonify({"ok": True})
    finally:
        db.close()


@app.route("/api/scheduled-games/<int:scheduled_game_id>/invite-link")
def api_scheduled_game_invite_link(scheduled_game_id):
    """获取邀请链接"""
    from services import scheduled_games
    user_id, err = _scheduled_user_id()
    if err:
        return jsonify({"error": err}), 401
    db = SessionLocal()
    try:
        sg = scheduled_games.get(db, scheduled_game_id)
        if not sg:
            return jsonify({"error": "约局不存在"}), 404
        return jsonify(scheduled_games.get_invite_link(sg, request.host_url or ""))
    finally:
        db.close()


@app.route("/api/clubs/<int:club_id>/scheduled-games")
def api_club_scheduled_games(club_id):
    """俱乐部下约局列表"""
    from services import scheduled_games
    db = SessionLocal()
    try:
        started = scheduled_games.check_and_start_games(db)
        for sg_id, table_id in started:
            socketio.emit("scheduled:table_created", {"scheduledGameId": sg_id, "tableId": table_id}, room=f"scheduled_{sg_id}")
        lst = scheduled_games.list_games(db, club_id=club_id, limit=50)
        out = []
        for sg in lst:
            n = scheduled_games.count_players(db, sg.id)
            sb, bb = scheduled_games._parse_blinds(sg.blinds_json)
            out.append({
                "scheduledGameId": sg.id,
                "title": sg.title,
                "hostUserId": sg.host_user_id,
                "startAt": sg.start_at.isoformat() if sg.start_at else None,
                "startRule": sg.start_rule,
                "minPlayers": sg.min_players,
                "maxPlayers": sg.max_players,
                "blindsDisplay": f"{sb}/{bb}",
                "status": sg.status,
                "registeredCount": n,
                "tableId": sg.table_id,
            })
        return jsonify(out)
    finally:
        db.close()


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
    if not token:
        return jsonify({"error": "请提供 token"}), 404
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

        # 玩家入座后自动让机器人填满剩余座位并开局（延迟 0.5 秒后执行，避免线程未跑）
        import bots
        bots.fill_table_with_bots(table_id, delay=0.5)

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
            # 已在进行中时视为幂等，返回 200 与当前状态
            t = tables.TABLES.get(table_id)
            if t and t.get("status") == "playing" and msg and ("已在进行中" in msg or "already" in msg.lower()):
                state, _ = tables.get_table_state(table_id, token)
                if state and state.get("status") == "playing" and tables.TABLES.get(table_id, {}).get("game"):
                    state["game_state"] = _game_state_for_seat(table_id, state.get("my_seat", -1))
                return jsonify(state or {"status": "playing", "tableId": table_id})
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
    deal_phase, deal_cards = None, []
    if t and t.get("game") and getattr(t["game"], "pending_insurance", None):
        ok, msg = tables.resolve_insurance(table_id, token, 0)
        if not ok and msg:
            return jsonify({"error": msg}), 400
    else:
        ok, msg, deal_phase, deal_cards = tables.deal_next_street(table_id)
        if not ok:
            return jsonify({"error": msg or "发牌失败"}), 400
    resp_state = _game_state_for_seat(table_id, seat)
    if not resp_state:
        return jsonify({"error": "无法获取状态"}), 500
    if deal_phase and deal_cards is not None:
        resp_state["deal_phase"] = deal_phase
        resp_state["deal_cards"] = deal_cards
    return jsonify(resp_state)


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
    _broadcast_table_state(table_id)  # 广播给同桌所有玩家，使表情即时可见
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


@app.route("/api/tables/<int:table_id>/fill_bots", methods=["POST", "GET"])
def api_fill_bots(table_id):
    """手动触发：同步填满机器人并开局（等待中且已有人入座时可用）。"""
    import bots
    t = tables.TABLES.get(table_id)
    if not t:
        return jsonify({"error": "牌桌不存在"}), 404
    if t.get("status") != "waiting":
        return jsonify({"error": "仅等待中可拉机器人", "status": t.get("status")}), 400
    seated = sum(1 for s in t["seats"] if s is not None)
    if seated < 1:
        return jsonify({"error": "请先入座再拉机器人"}), 400
    # 同步执行：直接填满空位并开局，不经过延迟线程
    empty = [i for i, s in enumerate(t["seats"]) if s is None]
    if empty:
        added, err = bots.add_bots_to_table(table_id, count=len(empty), auto_start=False)
        if err:
            return jsonify({"error": err}), 400
    t = tables.TABLES.get(table_id)
    seated = sum(1 for s in t["seats"] if s is not None) if t else 0
    if t and seated >= 2:
        ok, msg = tables.start_game(None, table_id, "")
        if not ok:
            return jsonify({"error": msg or "开局失败"}), 400
    state = tables.get_table_state_public(table_id)
    if state:
        socketio.emit("table:state", state, room=str(table_id))
    return jsonify({"ok": True, "message": "已填满机器人并开局", "table": state})


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
    user_id, err = _current_user_id()
    if err:
        return jsonify({"error": err}), 401
    db = SessionLocal()
    try:
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "俱乐部名称不能为空"}), 400
        club = clubs.create_club(db, name, user_id, data.get("description"))
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
        members = clubs.get_club_members_with_names(db, club_id)
        return jsonify({
            "id": club.id,
            "name": club.name,
            "description": club.description,
            "owner_id": club.owner_id,
            "members": members,
        })
    finally:
        db.close()


@app.route("/api/clubs/<int:club_id>/join", methods=["POST"])
def api_join_club(club_id):
    """加入俱乐部"""
    from services import clubs
    user_id, err = _current_user_id()
    if err:
        return jsonify({"error": err}), 401
    db = SessionLocal()
    try:
        member, err = clubs.join_club(db, club_id, user_id)
        if err:
            return jsonify({"error": err}), 400
        return jsonify({"message": "加入成功", "club_id": club_id})
    finally:
        db.close()


@app.route("/api/clubs/<int:club_id>/leave", methods=["POST"])
def api_leave_club(club_id):
    """离开俱乐部"""
    from services import clubs
    user_id, err = _current_user_id()
    if err:
        return jsonify({"error": err}), 401
    db = SessionLocal()
    try:
        ok, err = clubs.leave_club(db, club_id, user_id)
        if not ok:
            return jsonify({"error": err}), 400
        return jsonify({"ok": True})
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


@socketio.on("join_scheduled_game")
def ws_join_scheduled_game(data):
    """加入约局房间，接收 scheduled:updated / scheduled:table_created / scheduled:cancelled"""
    sg_id = data.get("scheduled_game_id") or data.get("scheduledGameId")
    if sg_id is None:
        emit("error", {"message": "缺少 scheduled_game_id"})
        return
    join_room(f"scheduled_{sg_id}")
    emit("ok", {"room": f"scheduled_{sg_id}"})


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
        ok, msg, phase, new_cards = tables.deal_next_street(table_id)
        if not ok:
            emit("error", {"message": msg or "发牌失败"})
            return
        if phase and new_cards is not None:
            emit("game:deal_phase", {"phase": phase, "cards": new_cards}, room=str(table_id))
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


def _ensure_default_table():
    """启动时若没有任何牌桌，则创建 1 号桌，避免直接访问 /?table=1 时 404。"""
    if not tables.TABLES:
        t = tables.create_table(db=None, table_name="牌桌 1", sb=5, bb=10, max_players=6)
        print(f"[Startup] 已创建默认牌桌: {t['table_id']} ({t.get('table_name', '')})")


if __name__ == "__main__":
    _ensure_default_table()
    socketio.run(app, host="0.0.0.0", port=8080, debug=False, allow_unsafe_werkzeug=True)


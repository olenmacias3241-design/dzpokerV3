# dzpokerV3/services/scheduled_games.py
# 约局后端逻辑（docs/requirements/13_scheduled_game_mode.md）

import json
import secrets
from datetime import datetime
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash, check_password_hash

from database import (
    ScheduledGame,
    ScheduledGamePlayer,
    User,
    ClubMember,
)

# 状态枚举（与 spec 13 一致）
STATUS_SCHEDULED = "Scheduled"
STATUS_READY_TO_START = "ReadyToStart"
STATUS_STARTING = "Starting"
STATUS_RUNNING = "Running"
STATUS_ENDED = "Ended"
STATUS_CANCELLED = "Cancelled"

START_RULE_SCHEDULED = "scheduled"
START_RULE_FULL = "full"
START_RULE_SCHEDULED_OR_FULL = "scheduled_or_full"


def _parse_blinds(blinds_json):
    """blinds_json 可能是 "10/20" 或 {"smallBlind":10,"bigBlind":20}，返回 (sb, bb)。"""
    if not blinds_json:
        return 5, 10
    if isinstance(blinds_json, str):
        try:
            obj = json.loads(blinds_json)
            return int(obj.get("smallBlind", 5)), int(obj.get("bigBlind", 10))
        except Exception:
            parts = blinds_json.replace(" ", "").split("/")
            if len(parts) >= 2:
                return int(parts[0]) or 5, int(parts[1]) or 10
            return 5, 10
    sb = int(blinds_json.get("smallBlind", 5))
    bb = int(blinds_json.get("bigBlind", 10))
    return sb, bb


def _generate_invite_code(db: Session):
    for _ in range(20):
        code = secrets.token_urlsafe(12)[:16]
        if not db.query(ScheduledGame).filter(ScheduledGame.invite_code == code).first():
            return code
    return secrets.token_hex(8)


def create(
    db: Session,
    host_user_id: int,
    title: str,
    start_at: datetime,
    min_players: int,
    max_players: int,
    blinds,  # str or dict
    start_rule: str = START_RULE_SCHEDULED_OR_FULL,
    club_id: int = None,
    buy_in_min: int = None,
    buy_in_max: int = None,
    initial_chips: int = None,
    password: str = None,
):
    """创建约局，局主自动加入参与名单。"""
    if not title or not start_at or min_players < 2 or max_players < min_players:
        return None, "参数无效"
    if start_at <= datetime.utcnow():
        return None, "开赛时间必须在未来"
    if isinstance(blinds, dict):
        blinds_json = json.dumps(blinds)
    else:
        blinds_json = str(blinds) if blinds else "5/10"
    invite_code = _generate_invite_code(db)
    password_hash = generate_password_hash(password, method="pbkdf2:sha256") if password else None
    sg = ScheduledGame(
        title=title.strip(),
        host_user_id=host_user_id,
        club_id=club_id,
        start_at=start_at,
        start_rule=start_rule or START_RULE_SCHEDULED_OR_FULL,
        min_players=min_players,
        max_players=max_players,
        blinds_json=blinds_json,
        buy_in_min=buy_in_min,
        buy_in_max=buy_in_max,
        initial_chips=initial_chips,
        password_hash=password_hash,
        invite_code=invite_code,
        status=STATUS_SCHEDULED,
    )
    db.add(sg)
    db.flush()
    db.add(ScheduledGamePlayer(scheduled_game_id=sg.id, user_id=host_user_id, seat_order=0))
    db.commit()
    db.refresh(sg)
    return sg, None


def get(db: Session, scheduled_game_id: int):
    return db.query(ScheduledGame).filter(ScheduledGame.id == scheduled_game_id).first()


def count_players(db: Session, scheduled_game_id: int):
    return db.query(ScheduledGamePlayer).filter(
        ScheduledGamePlayer.scheduled_game_id == scheduled_game_id
    ).count()


def list_games(
    db: Session,
    club_id: int = None,
    status: str = None,
    mine_user_id: int = None,
    limit: int = 50,
    offset: int = 0,
):
    """列表；club_id 筛选俱乐部下，mine=true 时筛选我创建或我报名的。"""
    q = db.query(ScheduledGame)
    if club_id is not None:
        q = q.filter(ScheduledGame.club_id == club_id)
    if status:
        q = q.filter(ScheduledGame.status == status)
    if mine_user_id is not None:
        sub = db.query(ScheduledGamePlayer.scheduled_game_id).filter(
            ScheduledGamePlayer.user_id == mine_user_id
        )
        q = q.filter(
            (ScheduledGame.host_user_id == mine_user_id) | (ScheduledGame.id.in_(sub))
        )
    return q.order_by(ScheduledGame.start_at.desc()).offset(offset).limit(limit).all()


def update(
    db: Session,
    scheduled_game_id: int,
    operator_user_id: int,
    title: str = None,
    start_at: datetime = None,
    min_players: int = None,
    max_players: int = None,
    blinds=None,
):
    """编辑约局（仅局主，且 status=Scheduled）。"""
    sg = get(db, scheduled_game_id)
    if not sg:
        return False, "约局不存在"
    if sg.host_user_id != operator_user_id:
        return False, "仅局主可编辑"
    if sg.status != STATUS_SCHEDULED:
        return False, "仅预约中可编辑"
    if title is not None:
        sg.title = title.strip()
    if start_at is not None:
        if start_at <= datetime.utcnow():
            return False, "开赛时间必须在未来"
        sg.start_at = start_at
    if min_players is not None:
        if min_players < 2 or count_players(db, scheduled_game_id) > min_players:
            return False, "最少人数无效"
        sg.min_players = min_players
    if max_players is not None:
        if max_players < min(sg.min_players, count_players(db, scheduled_game_id)):
            return False, "最大人数无效"
        sg.max_players = max_players
    if blinds is not None:
        sg.blinds_json = json.dumps(blinds) if isinstance(blinds, dict) else str(blinds)
    db.commit()
    return True, None


def cancel(db: Session, scheduled_game_id: int, operator_user_id: int):
    """取消约局（仅局主，Scheduled 或 ReadyToStart）。"""
    sg = get(db, scheduled_game_id)
    if not sg:
        return False, "约局不存在"
    if sg.host_user_id != operator_user_id:
        return False, "仅局主可取消"
    if sg.status not in (STATUS_SCHEDULED, STATUS_READY_TO_START):
        return False, "当前状态不可取消"
    sg.status = STATUS_CANCELLED
    db.commit()
    return True, None


def register(
    db: Session,
    scheduled_game_id: int,
    user_id: int,
    password: str = None,
):
    """报名：校验俱乐部成员、密码、未满员，加入名单。"""
    sg = get(db, scheduled_game_id)
    if not sg:
        return False, "约局不存在"
    if sg.status != STATUS_SCHEDULED:
        return False, "当前不可报名"
    n = count_players(db, scheduled_game_id)
    if n >= sg.max_players:
        return False, "已满员"
    if sg.password_hash and not (password and check_password_hash(sg.password_hash, password)):
        return False, "密码错误"
    if sg.club_id:
        member = db.query(ClubMember).filter_by(
            club_id=sg.club_id, user_id=user_id
        ).first()
        if not member:
            return False, "仅俱乐部成员可报名"
    existing = db.query(ScheduledGamePlayer).filter_by(
        scheduled_game_id=scheduled_game_id, user_id=user_id
    ).first()
    if existing:
        return False, "已报名"
    user = db.query(User).filter(User.id == user_id).first()
    buy_in = sg.buy_in_min or sg.initial_chips or 0
    if buy_in and user and (user.coins_balance or 0) < buy_in:
        return False, "余额不足"
    db.add(ScheduledGamePlayer(
        scheduled_game_id=scheduled_game_id,
        user_id=user_id,
        seat_order=n,
    ))
    db.commit()
    n += 1
    if n >= sg.max_players and sg.start_rule in (START_RULE_FULL, START_RULE_SCHEDULED_OR_FULL):
        sg.status = STATUS_READY_TO_START
        db.commit()
    return True, None


def unregister(db: Session, scheduled_game_id: int, user_id: int):
    """取消报名（仅 Scheduled 且未满员时可取消）。"""
    sg = get(db, scheduled_game_id)
    if not sg:
        return False, "约局不存在"
    if sg.status != STATUS_SCHEDULED:
        return False, "当前不可取消报名"
    row = db.query(ScheduledGamePlayer).filter_by(
        scheduled_game_id=scheduled_game_id, user_id=user_id
    ).first()
    if not row:
        return False, "未报名"
    if sg.host_user_id == user_id:
        return False, "局主不可取消报名"
    db.delete(row)
    db.commit()
    return True, None


def get_players(db: Session, scheduled_game_id: int, host_user_id: int = None):
    """参与名单，按 seat_order 排序，含用户昵称等。"""
    if host_user_id is None:
        sg = get(db, scheduled_game_id)
        host_user_id = sg.host_user_id if sg else None
    rows = db.query(ScheduledGamePlayer, User).join(
        User, ScheduledGamePlayer.user_id == User.id
    ).filter(ScheduledGamePlayer.scheduled_game_id == scheduled_game_id).order_by(
        ScheduledGamePlayer.seat_order
    ).all()
    return [
        {
            "user_id": r.user_id,
            "username": u.username or f"user_{u.id}",
            "nickname": u.nickname,
            "avatar_url": u.avatar_url,
            "seat_order": r.seat_order,
            "registered_at": r.registered_at.isoformat() if r.registered_at else None,
            "is_host": r.user_id == host_user_id,
        }
        for r, u in rows
    ]


def kick(db: Session, scheduled_game_id: int, operator_user_id: int, kicked_user_id: int):
    """踢出（仅局主，仅 Scheduled）。"""
    sg = get(db, scheduled_game_id)
    if not sg:
        return False, "约局不存在"
    if sg.host_user_id != operator_user_id:
        return False, "仅局主可踢人"
    if sg.status != STATUS_SCHEDULED:
        return False, "仅预约中可踢人"
    if kicked_user_id == sg.host_user_id:
        return False, "不能踢出局主"
    row = db.query(ScheduledGamePlayer).filter_by(
        scheduled_game_id=scheduled_game_id, user_id=kicked_user_id
    ).first()
    if not row:
        return False, "该用户未报名"
    db.delete(row)
    db.commit()
    return True, None


def get_invite_link(sg: ScheduledGame, base_url: str = ""):
    """返回邀请链接与 inviteCode。"""
    base = (base_url or "").rstrip("/")
    url = f"{base}/scheduled/join?code={sg.invite_code}" if base else f"/scheduled/join?code={sg.invite_code}"
    return {"url": url, "inviteCode": sg.invite_code}


def to_detail(db: Session, sg: ScheduledGame, base_url: str = ""):
    """约局详情（API 用），含参与名单、倒计时。"""
    sb, bb = _parse_blinds(sg.blinds_json)
    n = count_players(db, sg.id)
    players = get_players(db, sg.id, sg.host_user_id)
    now = datetime.utcnow()
    countdown_seconds = None
    if sg.start_at and sg.status in (STATUS_SCHEDULED, STATUS_READY_TO_START) and sg.start_at > now:
        countdown_seconds = int((sg.start_at - now).total_seconds())
    return {
        "scheduledGameId": sg.id,
        "title": sg.title,
        "hostUserId": sg.host_user_id,
        "clubId": sg.club_id,
        "startAt": sg.start_at.isoformat() if sg.start_at else None,
        "startRule": sg.start_rule,
        "minPlayers": sg.min_players,
        "maxPlayers": sg.max_players,
        "blinds": {"smallBlind": sb, "bigBlind": bb},
        "blindsDisplay": f"{sb}/{bb}",
        "buyInMin": sg.buy_in_min,
        "buyInMax": sg.buy_in_max,
        "initialChips": sg.initial_chips,
        "inviteCode": sg.invite_code,
        "status": sg.status,
        "tableId": sg.table_id,
        "registeredCount": n,
        "players": players,
        "countdownSeconds": countdown_seconds,
        "inviteLink": get_invite_link(sg, base_url) if sg else None,
        "createdAt": sg.created_at.isoformat() if sg.created_at else None,
        "updatedAt": sg.updated_at.isoformat() if sg.updated_at else None,
    }


def should_start(sg: ScheduledGame, now: datetime, player_count: int):
    """是否满足开赛条件（按 start_rule）。"""
    if sg.status not in (STATUS_SCHEDULED, STATUS_READY_TO_START):
        return False
    if player_count < sg.min_players:
        return False
    if sg.start_rule == START_RULE_SCHEDULED:
        return now >= sg.start_at
    if sg.start_rule == START_RULE_FULL:
        return player_count >= sg.max_players
    return (now >= sg.start_at) or (player_count >= sg.max_players)


def check_and_start_games(db: Session):
    """检查并开赛所有满足条件的约局。返回 [(scheduled_game_id, table_id), ...] 供调用方推送 WebSocket。"""
    now = datetime.utcnow()
    candidates = db.query(ScheduledGame).filter(
        ScheduledGame.status.in_([STATUS_SCHEDULED, STATUS_READY_TO_START])
    ).all()
    started = []
    for sg in candidates:
        n = count_players(db, sg.id)
        if should_start(sg, now, n):
            tid, err = start_scheduled_game(db, sg)
            if tid is not None:
                started.append((sg.id, tid))
    return started


def start_scheduled_game(db: Session, sg: ScheduledGame):
    """
    开赛：创建内存牌桌、按报名顺序入座、扣买入发筹码、开局。
    若有效人数 < min_players 则流局（Cancelled）。
    """
    import tables
    sg.status = STATUS_STARTING
    db.commit()
    db.refresh(sg)
    try:
        sb, bb = _parse_blinds(sg.blinds_json)
        max_players = sg.max_players
        buy_in = sg.buy_in_min or sg.initial_chips or 1000
        stack = sg.initial_chips or 1000
        name = sg.title or f"约局{sg.id}"
        t = tables.create_table(db=None, table_name=name, sb=sb, bb=bb, max_players=max_players)
        tid = t["table_id"]
        t["scheduled_game_id"] = sg.id
        players = (
            db.query(ScheduledGamePlayer)
            .filter(ScheduledGamePlayer.scheduled_game_id == sg.id)
            .order_by(ScheduledGamePlayer.seat_order)
            .all()
        )
        valid = []
        for p in players:
            user = db.query(User).filter(User.id == p.user_id).first()
            if not user:
                continue
            if (user.coins_balance or 0) < buy_in:
                continue
            valid.append((p.user_id, user))
        if len(valid) < sg.min_players:
            sg.status = STATUS_CANCELLED
            db.commit()
            return None, "人数不足，流局"
        for seat_idx, (user_id, user) in enumerate(valid):
            token = tables.token_for_db_user(user_id, user.username or user.nickname or f"user_{user_id}")
            user.coins_balance = (user.coins_balance or 0) - buy_in
            tables.sit(db, tid, token, seat_idx, auto_start=False)
            tbl = tables.TABLES.get(tid)
            if tbl and seat_idx < len(tbl["stacks"]):
                tbl["stacks"][seat_idx] = stack
        db.commit()
        first_token = tables.token_for_db_user(valid[0][0], valid[0][1].username or f"user_{valid[0][0]}")
        ok, err = tables.start_game(db, tid, first_token)
        if not ok:
            sg.status = STATUS_CANCELLED
            db.commit()
            return None, err or "开局失败"
        sg.status = STATUS_RUNNING
        sg.table_id = tid
        db.commit()
        return tid, None
    except Exception as e:
        sg.status = STATUS_SCHEDULED
        db.rollback()
        return None, str(e)

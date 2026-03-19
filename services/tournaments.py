# dzpokerV3/services/tournaments.py
# 锦标赛后端逻辑（docs/requirements/12_tournaments_sng_mtt.md）
# 状态：Registration → LateRegistration(MTT)/Running → Break(MTT) → Running → Finished

import json
from datetime import datetime
from sqlalchemy.orm import Session

from database import (
    Tournament, TournamentRegistration, TournamentBlindLevel, TournamentPayout,
    TournamentTable, TournamentPlayer, User, SessionLocal,
)


# 状态枚举（与 spec 12 一致）
STATUS_REGISTRATION = "Registration"
STATUS_LATE_REGISTRATION = "LateRegistration"
STATUS_RUNNING = "Running"
STATUS_BREAK = "Break"
STATUS_FINISHED = "Finished"


def list_tournaments(db: Session, status=None, type_=None):
    """赛事列表；可按 status、type 筛选。"""
    q = db.query(Tournament)
    if status:
        q = q.filter(Tournament.status == status)
    if type_:
        q = q.filter(Tournament.type == type_)
    return q.order_by(Tournament.starts_at.desc().nullslast(), Tournament.id.desc()).all()


def get_tournament(db: Session, tournament_id: int):
    return db.query(Tournament).filter(Tournament.id == tournament_id).first()


def count_registrations(db: Session, tournament_id: int):
    return db.query(TournamentRegistration).filter(
        TournamentRegistration.tournament_id == tournament_id,
        TournamentRegistration.unregistered_at.is_(None),
        TournamentRegistration.refunded_at.is_(None),
    ).count()


def register(db: Session, tournament_id: int, user_id: int, user_coins_balance: int):
    """报名：扣 buy_in + fee，写入 tournament_registrations。"""
    t = get_tournament(db, tournament_id)
    if not t:
        return None, "赛事不存在"
    if t.status != STATUS_REGISTRATION and not (t.type == "MTT" and t.status == STATUS_LATE_REGISTRATION):
        return None, "当前不可报名"
    total = t.buy_in + t.fee
    if user_coins_balance < total:
        return None, "筹码不足"
    existing = db.query(TournamentRegistration).filter_by(
        tournament_id=tournament_id, user_id=user_id
    ).first()
    if existing and existing.unregistered_at is None and existing.refunded_at is None:
        return None, "已报名"
    if existing:
        existing.unregistered_at = None
        existing.refunded_at = None
        existing.registered_at = datetime.utcnow()
        reg = existing
    else:
        reg = TournamentRegistration(tournament_id=tournament_id, user_id=user_id)
        db.add(reg)
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.coins_balance = (user.coins_balance or 0) - total
    db.commit()
    db.refresh(reg)
    return reg, None


def unregister(db: Session, tournament_id: int, user_id: int):
    """取消报名：仅 Registration 阶段可取消，退款 buy_in + fee。"""
    t = get_tournament(db, tournament_id)
    if not t:
        return False, "赛事不存在"
    if t.status != STATUS_REGISTRATION:
        return False, "已开赛不可取消报名"
    reg = db.query(TournamentRegistration).filter_by(
        tournament_id=tournament_id, user_id=user_id
    ).first()
    if not reg or reg.unregistered_at or reg.refunded_at:
        return False, "未报名或已取消"
    reg.unregistered_at = datetime.utcnow()
    reg.refunded_at = datetime.utcnow()
    total = t.buy_in + t.fee
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.coins_balance = (user.coins_balance or 0) + total
    db.commit()
    return True, None


def get_blind_levels(db: Session, tournament_id: int):
    """返回已配置的盲注级别列表，按 level_index 排序。"""
    return db.query(TournamentBlindLevel).filter_by(
        tournament_id=tournament_id
    ).order_by(TournamentBlindLevel.level_index).all()


def get_payouts(db: Session, tournament_id: int):
    """返回奖励结构列表。"""
    return db.query(TournamentPayout).filter_by(
        tournament_id=tournament_id
    ).order_by(TournamentPayout.rank_from).all()


def get_tournament_state(db: Session, tournament_id: int, user_id: int = None):
    """返回赛事状态摘要（供 API/WebSocket）。user_id 用于返回玩家自己的桌信息。"""
    t = get_tournament(db, tournament_id)
    if not t:
        return None
    reg_count = count_registrations(db, tournament_id)
    levels = get_blind_levels(db, tournament_id)
    current_level = None
    if levels and t.current_level_index < len(levels):
        current_level = levels[t.current_level_index]
    # 仍在局中的玩家数
    players_in = db.query(TournamentPlayer).filter_by(
        tournament_id=tournament_id, rank=None
    ).count() if t.status in (STATUS_RUNNING, STATUS_BREAK, STATUS_LATE_REGISTRATION) else reg_count

    # 牌桌列表
    tbls = db.query(TournamentTable).filter_by(tournament_id=tournament_id).all()
    game_tables = []
    for tbl in tbls:
        game_table_id = None
        try:
            game_table_id = int(tbl.status)
        except (ValueError, TypeError):
            pass
        player_count = db.query(TournamentPlayer).filter_by(
            tournament_id=tournament_id, table_id=tbl.id, rank=None
        ).filter(TournamentPlayer.eliminated_at.is_(None)).count()
        game_tables.append({
            "table_id": tbl.id,
            "table_number": tbl.table_number,
            "game_table_id": game_table_id,
            "players_count": player_count,
        })

    # 当前用户的桌信息
    my_game_table_id = None
    my_table_number = None
    my_seat = None
    if user_id:
        tp = db.query(TournamentPlayer).filter_by(
            tournament_id=tournament_id, user_id=user_id, rank=None
        ).filter(TournamentPlayer.eliminated_at.is_(None)).first()
        if tp and tp.table_id:
            tbl = db.query(TournamentTable).filter_by(id=tp.table_id).first()
            if tbl:
                my_table_number = tbl.table_number
                try:
                    my_game_table_id = int(tbl.status)
                except (ValueError, TypeError):
                    pass
            my_seat = tp.seat_index

    return {
        "tournament_id": t.id,
        "name": t.name,
        "type": t.type,
        "status": t.status,
        "buy_in": t.buy_in,
        "fee": t.fee,
        "starting_stack": t.starting_stack,
        "max_players": t.max_players,
        "min_players_to_start": t.min_players_to_start,
        "registered_count": reg_count,
        "players_remaining": players_in,
        "current_level_index": t.current_level_index,
        "current_level": {
            "small_blind": current_level.small_blind,
            "big_blind": current_level.big_blind,
            "ante": getattr(current_level, "ante", 0) or 0,
            "duration_minutes": current_level.duration_minutes,
        } if current_level else None,
        "starts_at": t.starts_at.isoformat() if t.starts_at else None,
        "blind_structure_json": t.blind_structure_json,
        "payout_structure_json": t.payout_structure_json,
        "game_tables": game_tables,
        "myGameTableId": my_game_table_id,
        "myTableNumber": my_table_number,
        "mySeat": my_seat,
    }


def create_sng(db: Session, name: str, buy_in: int, fee: int, starting_stack: int,
               max_players: int = 9, min_to_start: int = 2,
               blind_levels: list = None, payout_percents: list = None):
    """
    创建 SNG。blind_levels: [{"small_blind", "big_blind", "ante", "duration_minutes"}, ...]
    payout_percents: [{"rank_from", "rank_to", "percent"}, ...] 如 9 人 [{"rank_from":1,"rank_to":1,"percent":50}, ...]
    """
    t = Tournament(
        name=name,
        type="SNG",
        buy_in=buy_in,
        fee=fee,
        starting_stack=starting_stack,
        max_players=max_players,
        min_players_to_start=min_to_start,
        status=STATUS_REGISTRATION,
        blind_structure_json=json.dumps(blind_levels or []),
        payout_structure_json=json.dumps(payout_percents or []),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    if blind_levels:
        for i, lv in enumerate(blind_levels):
            bl = TournamentBlindLevel(
                tournament_id=t.id,
                level_index=i,
                small_blind=int(lv.get("small_blind", 0)),
                big_blind=int(lv.get("big_blind", 0)),
                ante=int(lv.get("ante", 0)),
                duration_minutes=int(lv.get("duration_minutes", 5)),
            )
            db.add(bl)
    if payout_percents:
        for p in payout_percents:
            pay = TournamentPayout(
                tournament_id=t.id,
                rank_from=int(p.get("rank_from", 1)),
                rank_to=int(p.get("rank_to", 1)),
                percent_value=float(p.get("percent", 0)),
                is_percent=True,
            )
            db.add(pay)
    db.commit()
    return t


def create_mtt(db: Session, name: str, buy_in: int, fee: int, starting_stack: int,
               max_players: int = 100, min_to_start: int = 10,
               starts_at=None, late_reg_minutes: int = 30,
               blind_levels: list = None, payout_percents: list = None):
    """创建 MTT，逻辑同 create_sng 但支持定时开赛和补充报名窗口。"""
    t = Tournament(
        name=name,
        type="MTT",
        buy_in=buy_in,
        fee=fee,
        starting_stack=starting_stack,
        max_players=max_players,
        min_players_to_start=min_to_start,
        status=STATUS_REGISTRATION,
        starts_at=starts_at,
        late_reg_minutes=late_reg_minutes,
        blind_structure_json=json.dumps(blind_levels or []),
        payout_structure_json=json.dumps(payout_percents or []),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    if blind_levels:
        for i, lv in enumerate(blind_levels):
            bl = TournamentBlindLevel(
                tournament_id=t.id,
                level_index=i,
                small_blind=int(lv.get("small_blind", 0)),
                big_blind=int(lv.get("big_blind", 0)),
                ante=int(lv.get("ante", 0)),
                duration_minutes=int(lv.get("duration_minutes", 5)),
            )
            db.add(bl)
    if payout_percents:
        for p in payout_percents:
            pay = TournamentPayout(
                tournament_id=t.id,
                rank_from=int(p.get("rank_from", 1)),
                rank_to=int(p.get("rank_to", 1)),
                percent_value=float(p.get("percent", 0)),
                is_percent=True,
            )
            db.add(pay)
    db.commit()
    return t


def start_tournament_game(db: Session, tournament_id: int, tables_mod, bots_mod):
    """
    开赛：为已报名玩家创建真实内存牌桌，机器人补空位，然后开局。
    成功返回 (True, game_table_id)，失败返回 (False, error_msg)。
    """
    t = get_tournament(db, tournament_id)
    if not t:
        return False, "赛事不存在"
    if t.status not in (STATUS_REGISTRATION, STATUS_LATE_REGISTRATION):
        return False, f"当前状态 {t.status} 不可开赛"

    regs = db.query(TournamentRegistration).filter_by(
        tournament_id=tournament_id
    ).filter(
        TournamentRegistration.unregistered_at.is_(None),
        TournamentRegistration.refunded_at.is_(None),
    ).all()

    if len(regs) < t.min_players_to_start:
        return False, f"报名人数 {len(regs)} 不足 {t.min_players_to_start}"

    # 取第一级盲注
    levels = get_blind_levels(db, tournament_id)
    sb = int(levels[0].small_blind) if levels else 5
    bb = int(levels[0].big_blind) if levels else 10

    # 创建内存牌桌
    table_dict = tables_mod.create_table(
        db=None,
        table_name=t.name,
        sb=sb,
        bb=bb,
        max_players=t.max_players,
    )
    game_table_id = table_dict["table_id"]
    table_dict["tournament_id"] = tournament_id  # 标记为锦标赛桌

    # 为每位真实玩家分配 token，设置起始筹码，落座
    user_tokens = []
    for seat_idx, reg in enumerate(regs):
        if seat_idx >= t.max_players:
            break
        user = db.query(User).filter(User.id == reg.user_id).first()
        username = (user.username if user else None) or f"用户{reg.user_id}"
        tok = tables_mod.token_for_db_user(reg.user_id, username)
        tables_mod._tokens[tok]["stack"] = int(t.starting_stack)
        ok, err = tables_mod.sit(game_table_id, tok, seat_idx, auto_start=False)
        if ok:
            user_tokens.append((reg.user_id, seat_idx))

    # 机器人补空位
    empty = t.max_players - len(user_tokens)
    if empty > 0:
        bots_mod.add_bots_to_table(game_table_id, count=empty, auto_start=False)

    # 开局
    tables_mod.start_game(None, game_table_id, None)

    # 写 DB：TournamentTable.status 存 game_table_id（复用该字段做关联）
    tbl = TournamentTable(
        tournament_id=tournament_id,
        table_number=1,
        status=str(game_table_id),
    )
    db.add(tbl)
    db.flush()

    # 写 TournamentPlayer（仅真实玩家）
    for uid, seat_idx in user_tokens:
        existing = db.query(TournamentPlayer).filter_by(
            tournament_id=tournament_id, user_id=uid
        ).first()
        if existing:
            existing.table_id = tbl.id
            existing.seat_index = seat_idx
            existing.chips = int(t.starting_stack)
        else:
            db.add(TournamentPlayer(
                tournament_id=tournament_id,
                user_id=uid,
                table_id=tbl.id,
                seat_index=seat_idx,
                chips=int(t.starting_stack),
            ))

    t.status = STATUS_RUNNING
    db.commit()
    return True, game_table_id


def finish_tournament(db: Session, tournament_id: int):
    """结算赛事：按 payout 结构分配奖金，更新玩家余额，赛事状态改为 Finished。"""
    t = get_tournament(db, tournament_id)
    if not t:
        return
    prize_pool = count_registrations(db, tournament_id) * int(t.buy_in)
    payouts = get_payouts(db, tournament_id)
    all_players = db.query(TournamentPlayer).filter_by(tournament_id=tournament_id).all()

    for payout in payouts:
        for tp in all_players:
            if tp.rank is not None and payout.rank_from <= tp.rank <= payout.rank_to:
                prize = int(prize_pool * float(payout.percent_value) / 100)
                tp.prize_amount = prize
                user = db.query(User).filter(User.id == tp.user_id).first()
                if user:
                    user.coins_balance = (user.coins_balance or 0) + prize
                print(f"[Tournament {tournament_id}] 奖金: user={tp.user_id} rank={tp.rank} prize={prize}")

    t.status = STATUS_FINISHED
    db.commit()
    print(f"[Tournament {tournament_id}] 赛事结束，共 {len(all_players)} 人参赛，奖池 {prize_pool}")


def post_hand_tournament_hook(db: Session, table_id: int, tables_mod):
    """
    每手牌结束后被 bots.py 调用。
    检查真实玩家筹码，标记淘汰；若只剩 ≤1 名真实玩家则结束赛事。
    """
    t_dict = tables_mod.TABLES.get(table_id)
    if not t_dict:
        return
    tournament_id = t_dict.get("tournament_id")
    if not tournament_id:
        return
    tournament = get_tournament(db, tournament_id)
    if not tournament or tournament.status != STATUS_RUNNING:
        return

    wrapper = t_dict.get("game")
    if not wrapper:
        return
    state = wrapper.state

    # 检查每位真实玩家（整数 uid）的当前筹码
    for pid, ps in (state.get("players") or {}).items():
        try:
            uid = int(pid)
        except (ValueError, TypeError):
            continue  # 机器人，跳过
        tp = db.query(TournamentPlayer).filter_by(
            tournament_id=tournament_id, user_id=uid
        ).first()
        if not tp or tp.rank is not None or tp.eliminated_at is not None:
            continue
        if (ps.get("stack") or 0) <= 0:
            tp.eliminated_at = datetime.utcnow()
            print(f"[Tournament {tournament_id}] 玩家 {uid} 筹码归零，标记淘汰")

    db.flush()

    # 统计尚存活的真实玩家
    alive = db.query(TournamentPlayer).filter_by(
        tournament_id=tournament_id, rank=None
    ).filter(TournamentPlayer.eliminated_at.is_(None)).all()

    if len(alive) <= 1:
        # 分配 rank：按淘汰时间排序，越早淘汰 rank 越大
        all_players = db.query(TournamentPlayer).filter_by(
            tournament_id=tournament_id
        ).all()
        total = len(all_players)
        eliminated = sorted(
            [p for p in all_players if p.eliminated_at is not None and p.rank is None],
            key=lambda p: p.eliminated_at or datetime.utcnow(),
        )
        for i, p in enumerate(eliminated):
            p.rank = total - i  # 最先淘汰的拿最大 rank（最差名次）
        if alive:
            alive[0].rank = 1
        db.commit()
        finish_tournament(db, tournament_id)


def try_start_tournament(db: Session, tournament_id: int):
    """
    SNG：报名人数 >= max_players 或 >= min_players_to_start 且满足开赛条件时，开赛。
    开赛：创建 tournament_tables、tournament_players，状态改为 Running。
    """
    t = get_tournament(db, tournament_id)
    if not t or t.status != STATUS_REGISTRATION:
        return False, None
    reg_count = count_registrations(db, tournament_id)
    if reg_count < t.min_players_to_start:
        return False, None
    # SNG 满员即开或到 min 即开（此处简化为达到 min 即开）
    t.status = STATUS_RUNNING
    # 为每个已报名玩家创建 TournamentPlayer，分配起始筹码
    regs = db.query(TournamentRegistration).filter_by(
        tournament_id=tournament_id
    ).filter(
        TournamentRegistration.unregistered_at.is_(None),
        TournamentRegistration.refunded_at.is_(None),
    ).all()
    # 创建一张桌（单桌 SNG）
    tbl = TournamentTable(tournament_id=t.id, table_number=1, status="active")
    db.add(tbl)
    db.flush()
    for i, reg in enumerate(regs):
        pl = TournamentPlayer(
            tournament_id=t.id,
            user_id=reg.user_id,
            table_id=tbl.id,
            seat_index=i,
            chips=t.starting_stack,
        )
        db.add(pl)
    db.commit()
    return True, t

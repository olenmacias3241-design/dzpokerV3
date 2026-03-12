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


def get_tournament_state(db: Session, tournament_id: int):
    """返回赛事状态摘要（供 API/WebSocket）。"""
    t = get_tournament(db, tournament_id)
    if not t:
        return None
    reg_count = count_registrations(db, tournament_id)
    levels = get_blind_levels(db, tournament_id)
    current_level = None
    if levels and t.current_level_index < len(levels):
        current_level = levels[t.current_level_index]
    payouts = get_payouts(db, tournament_id)
    # 仍在局中的玩家数
    players_in = db.query(TournamentPlayer).filter_by(
        tournament_id=tournament_id, rank=None
    ).count() if t.status in (STATUS_RUNNING, STATUS_BREAK, STATUS_LATE_REGISTRATION) else reg_count
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

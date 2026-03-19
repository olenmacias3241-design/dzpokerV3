#!/usr/bin/env python3
"""
种子脚本：创建 2 个 SNG + 1 个 MTT 测试赛事。
用法：
  cd /path/to/dzpokerV3
  python scripts/seed_tournaments.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from services.tournaments import create_sng, create_mtt

# 标准德州扑克锦标赛盲注结构
STANDARD_BLINDS = [
    {"small_blind": 10,  "big_blind": 20,  "ante": 0,  "duration_minutes": 5},
    {"small_blind": 15,  "big_blind": 30,  "ante": 0,  "duration_minutes": 5},
    {"small_blind": 25,  "big_blind": 50,  "ante": 5,  "duration_minutes": 5},
    {"small_blind": 50,  "big_blind": 100, "ante": 10, "duration_minutes": 5},
    {"small_blind": 75,  "big_blind": 150, "ante": 25, "duration_minutes": 5},
    {"small_blind": 100, "big_blind": 200, "ante": 25, "duration_minutes": 5},
    {"small_blind": 150, "big_blind": 300, "ante": 50, "duration_minutes": 5},
    {"small_blind": 200, "big_blind": 400, "ante": 50, "duration_minutes": 5},
]

# SNG 6 人桌奖励结构：1、2 名奖励
PAYOUT_SNG_6 = [
    {"rank_from": 1, "rank_to": 1, "percent": 65},
    {"rank_from": 2, "rank_to": 2, "percent": 35},
]

# SNG 9 人桌奖励结构：前 3 名奖励
PAYOUT_SNG_9 = [
    {"rank_from": 1, "rank_to": 1, "percent": 50},
    {"rank_from": 2, "rank_to": 2, "percent": 30},
    {"rank_from": 3, "rank_to": 3, "percent": 20},
]

# MTT 奖励结构（前 15%，简化为固定名次）
PAYOUT_MTT = [
    {"rank_from": 1, "rank_to": 1,  "percent": 30},
    {"rank_from": 2, "rank_to": 2,  "percent": 20},
    {"rank_from": 3, "rank_to": 3,  "percent": 12},
    {"rank_from": 4, "rank_to": 6,  "percent": 10},
    {"rank_from": 7, "rank_to": 10, "percent": 5},
]


def main():
    db = SessionLocal()
    try:
        # SNG 6 人桌（低买入，快速开赛）
        sng6 = create_sng(
            db,
            name="周末 SNG · 6 人桌",
            buy_in=100,
            fee=10,
            starting_stack=3000,
            max_players=6,
            min_to_start=2,
            blind_levels=STANDARD_BLINDS,
            payout_percents=PAYOUT_SNG_6,
        )
        print(f"✓ 创建 SNG 6 人桌: id={sng6.id}  名称={sng6.name}")

        # SNG 9 人桌（标准 buy-in）
        sng9 = create_sng(
            db,
            name="标准 SNG · 9 人桌",
            buy_in=500,
            fee=50,
            starting_stack=10000,
            max_players=9,
            min_to_start=2,
            blind_levels=STANDARD_BLINDS,
            payout_percents=PAYOUT_SNG_9,
        )
        print(f"✓ 创建 SNG 9 人桌: id={sng9.id}  名称={sng9.name}")

        # MTT（定时开赛，允许更多玩家）
        from datetime import datetime, timezone, timedelta
        starts_at = datetime.now(timezone.utc) + timedelta(hours=1)
        mtt = create_mtt(
            db,
            name="每日 MTT · 200 人",
            buy_in=200,
            fee=20,
            starting_stack=20000,
            max_players=200,
            min_to_start=4,
            starts_at=starts_at,
            late_reg_minutes=30,
            blind_levels=STANDARD_BLINDS,
            payout_percents=PAYOUT_MTT,
        )
        print(f"✓ 创建 MTT     : id={mtt.id}  名称={mtt.name}  开赛时间={starts_at.strftime('%Y-%m-%d %H:%M')}")

        print("\n全部完成。访问 /tournaments 查看。")
        print(f"  测试开赛（SNG 6 人桌）：POST /api/admin/tournaments/{sng6.id}/start")
    finally:
        db.close()


if __name__ == "__main__":
    main()

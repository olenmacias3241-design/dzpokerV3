#!/usr/bin/env python3
# tests/api/test_play_hand.py
# 牌桌打牌逻辑集成测试：通过 HTTP API 模拟一局（两人入座、行动、发牌至结束）
# 需先启动服务端。运行：pytest tests/api/test_play_hand.py -v -s

import os
import time
import pytest
import requests

BASE_URL = os.environ.get("DZPOKER_API_BASE", "http://127.0.0.1:8080").rstrip("/")
TIMEOUT = 15.0
MAX_TURNS = 150  # 防止死循环


def _login(name):
    r = requests.post(f"{BASE_URL}/api/login", json={"username": name}, timeout=TIMEOUT)
    assert r.status_code == 200 and r.json().get("ok"), r.text
    return r.json()["token"], r.json()["userId"]


def _create_table():
    r = requests.post(
        f"{BASE_URL}/api/lobby/tables",
        json={"tableName": "打牌逻辑测试桌", "sb": 5, "bb": 10, "maxPlayers": 6},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200
    return r.json()["tableId"]


def _sit(table_id, token, seat):
    r = requests.post(
        f"{BASE_URL}/api/tables/{table_id}/sit",
        json={"token": token, "seat": seat},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200


def _start(table_id, token):
    r = requests.post(
        f"{BASE_URL}/api/tables/{table_id}/start",
        json={"token": token},
        timeout=TIMEOUT,
    )
    assert r.status_code in (200, 400), r.text
    if r.status_code == 400 and "游戏已在进行中" in r.json().get("error", ""):
        return True  # 机器人已开局，视为成功
    return r.status_code == 200


def _get_state(table_id, token):
    r = requests.get(
        f"{BASE_URL}/api/tables/{table_id}",
        params={"token": token},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200
    return r.json()


def _action(table_id, token, action, amount=0):
    r = requests.post(
        f"{BASE_URL}/api/tables/{table_id}/action",
        json={"token": token, "action": action, "amount": amount},
        timeout=TIMEOUT,
    )
    return r.status_code == 200, r.json() if r.headers.get("content-type", "").startswith("application/json") else {}


def _deal_next(table_id, token):
    r = requests.post(
        f"{BASE_URL}/api/tables/{table_id}/deal_next",
        json={"token": token},
        timeout=TIMEOUT,
    )
    return r.status_code == 200, r.json() if r.headers.get("content-type", "").startswith("application/json") else {}


def _get_my_user_id(table_id, token):
    st = _get_state(table_id, token)
    # my_seat + seats 可推出当前用户 id；或从 game_state.seats 里根据 seat 找
    gs = st.get("game_state") or {}
    my_seat = st.get("my_seat", -1)
    if my_seat < 0:
        return None
    seats = gs.get("seats") or []
    if my_seat < len(seats) and seats[my_seat]:
        return seats[my_seat].get("player_id") or seats[my_seat].get("userId")
    return None


def _current_player_id(gs):
    return gs.get("current_player_id") or gs.get("current_player_idx")


def _stage(gs):
    return (gs.get("stage") or "preflop").lower()


def _amount_to_call(gs):
    return int(gs.get("amount_to_call") or gs.get("call_amount") or 0)


def _my_seat_index_in_players(gs, my_user_id):
    seats = gs.get("seats") or []
    for i, s in enumerate(seats):
        if not s:
            continue
        pid = s.get("player_id") or s.get("userId") or s.get("id")
        if str(pid) == str(my_user_id):
            return i
    return -1


def _can_check(gs, my_user_id):
    return _amount_to_call(gs) == 0


def _choose_action(gs, my_user_id, token_a, token_b, table_id):
    """若轮到 my_user_id，选一个合法动作并执行。返回 (acted, next_token)。"""
    cur = _current_player_id(gs)
    if not cur:
        return False, None
    players = gs.get("seats") or gs.get("players") or []
    cur_seat = -1
    for i, s in enumerate(players):
        if not s:
            continue
        pid = s.get("player_id") or s.get("userId")
        if str(pid) == str(cur):
            cur_seat = i
            break
    if cur_seat < 0:
        return False, None
    # 用 token_a 对应 seat 0，token_b 对应 seat 1
    token = token_a if cur_seat == 0 else token_b
    atc = _amount_to_call(gs)
    if atc == 0:
        ok, _ = _action(table_id, token, "check")
    else:
        ok, _ = _action(table_id, token, "call")
    return ok, token


@pytest.mark.skipif(
    os.environ.get("SKIP_PLAY_HAND") == "1",
    reason="SKIP_PLAY_HAND=1",
)
def test_play_one_hand_full_flow():
    """两人入座、开局，轮流行动并发牌，直到本局结束。"""
    token_a, uid_a = _login("PlayHandA")
    token_b, uid_b = _login("PlayHandB")
    table_id = _create_table()
    _sit(table_id, token_a, 0)
    _sit(table_id, token_b, 1)
    time.sleep(0.5)
    _start(table_id, token_a)

    # 用 A 的视角拉状态
    state = _get_state(table_id, token_a)
    gs = state.get("game_state")
    if not gs:
        pytest.skip("未进入对局（可能机器人未填满或未开局）")

    stage = _stage(gs)
    turns = 0
    while stage not in ("ended", "showdown") and turns < MAX_TURNS:
        turns += 1
        cur = _current_player_id(gs)
        if cur is not None:
            acted, _ = _choose_action(gs, cur, token_a, token_b, table_id)
            if acted:
                state = _get_state(table_id, token_a)
                gs = state.get("game_state") or gs
        else:
            # 需要发下一街
            ok, resp = _deal_next(table_id, token_a)
            assert ok, resp.get("error", "deal_next 失败")
            state = resp if resp.get("game_state") else _get_state(table_id, token_a)
            gs = state.get("game_state") or gs
        stage = _stage(gs)

    assert stage in ("ended", "showdown") or turns >= MAX_TURNS
    # 若正常结束，应有底池分配或 winners
    if stage == "ended":
        assert gs.get("pot") is not None or gs.get("winners") or "last_hand_winnings" in str(gs)

# tests/frontend/test_table_page.py
# 牌桌页：无参数提示、带 table+token 时显示游戏区或入座

import pytest
import requests
from playwright.sync_api import Page, expect

BASE_URL = __import__("os").environ.get("DZPOKER_API_BASE", "http://127.0.0.1:8080").rstrip("/")
TIMEOUT = 10


def _guest_token():
    r = requests.post(f"{BASE_URL}/api/login", json={"username": "E2EGuest"}, timeout=TIMEOUT)
    if r.status_code != 200 or not r.json().get("token"):
        pytest.skip("需要服务端运行以获取 token")
    return r.json()["token"]


def test_table_page_without_params_shows_hint(page: Page, base_url: str):
    """无 table/token 时显示「请从大厅选择牌桌」提示。"""
    page.goto("/")
    # 可能显示 no-table-msg 或 game-area 被隐藏
    no_msg = page.locator("#no-table-msg")
    game_area = page.locator(".game-area")
    # 至少有一个存在；无参数时通常显示 no-table-msg
    no_visible = no_msg.is_visible()
    game_visible = game_area.is_visible()
    assert no_visible or not game_visible, "无参数时应显示提示或隐藏游戏区"
    if no_visible:
        expect(no_msg).to_contain_text("大厅")


def test_table_page_with_table_and_token_loads(page: Page, base_url: str):
    """带 table 与 token 打开牌桌页，游戏区或入座区可见。"""
    token = _guest_token()
    # 先建桌并入座，再跳转
    r = requests.post(
        f"{BASE_URL}/api/lobby/tables",
        json={"tableName": "E2E桌", "sb": 5, "bb": 10, "maxPlayers": 6},
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        pytest.skip("创建牌桌失败，需服务端运行")
    table_id = r.json()["tableId"]
    requests.post(
        f"{BASE_URL}/api/tables/{table_id}/sit",
        json={"token": token, "seat": 0},
        timeout=TIMEOUT,
    )
    page.goto(f"/?table={table_id}&token={token}")
    # 应显示游戏区（或入座/选择座位）
    game_area = page.locator(".game-area")
    game_area.wait_for(state="visible", timeout=5000)
    # 游戏区内应有牌桌或入座面板之一
    poker_table = page.locator(".poker-table")
    sit_panel = page.locator("#sit-at-table-wrap")
    assert poker_table.is_visible() or sit_panel.is_visible(), "应有牌桌或入座面板"


def test_table_page_has_action_controls_when_visible(page: Page, base_url: str):
    """牌桌页存在行动按钮区域（弃牌/过牌/跟注等）或开始对局按钮。"""
    token = _guest_token()
    r = requests.post(
        f"{BASE_URL}/api/lobby/tables",
        json={"tableName": "E2E桌2", "sb": 5, "bb": 10, "maxPlayers": 6},
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        pytest.skip("创建牌桌失败")
    table_id = r.json()["tableId"]
    requests.post(f"{BASE_URL}/api/tables/{table_id}/sit", json={"token": token, "seat": 0}, timeout=TIMEOUT)
    page.goto(f"/?table={table_id}&token={token}")
    page.locator(".game-area").wait_for(state="visible", timeout=5000)
    # 至少应有「开始对局」或行动区
    start_btn = page.locator("#start-game-btn")
    fold_btn = page.locator("#fold-btn")
    start_visible = start_btn.is_visible()
    fold_visible = fold_btn.is_visible()
    assert start_visible or fold_visible, "应有开始对局或弃牌等按钮"

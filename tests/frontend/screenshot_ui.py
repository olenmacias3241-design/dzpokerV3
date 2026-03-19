#!/usr/bin/env python3
"""
dzpokerV3 前端 UI 截图工具
用法：
  python3 tests/frontend/screenshot_ui.py          # 截全部状态
  python3 tests/frontend/screenshot_ui.py lobby     # 仅截大厅
  python3 tests/frontend/screenshot_ui.py table     # 仅截牌桌（自动创建桌+机器人）

截图保存在 tests/frontend/screenshots/ 目录下。
"""

import sys
import time
import json
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:5001"
OUT  = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "mobile":  {"width": 390,  "height": 844},
}


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def api(method, path, **kwargs):
    return requests.request(method, BASE + path, **kwargs).json()


def guest_login(username="测试玩家"):
    return api("POST", "/api/login", json={"username": username})["token"]


def create_table_with_bots():
    """创建一张桌，用机器人填满，返回 (table_id, token)。"""
    token = guest_login()
    # 创建桌
    resp = api("POST", "/api/tables", json={
        "token": token, "name": "截图测试桌", "sb": 5, "bb": 10, "max_players": 6
    })
    table_id = resp.get("tableId") or resp.get("table_id")
    # 入座
    api("POST", f"/api/tables/{table_id}/sit", json={"token": token, "seat": 0})
    # 等机器人填满并开局
    time.sleep(4)
    return table_id, token


# ──────────────────────────────────────────────
# 截图场景
# ──────────────────────────────────────────────

def shot_lobby(page, vp_name):
    """大厅页面"""
    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    time.sleep(1)
    path = OUT / f"lobby_{vp_name}.png"
    page.screenshot(path=str(path), full_page=False)
    print(f"  ✓ {path.name}")


def shot_table_states(page, vp_name, table_id, token):
    """牌桌各状态"""
    url = f"{BASE}/?table={table_id}&token={token}"

    # 等待中/刚开局
    page.goto(url)
    page.wait_for_load_state("networkidle")
    time.sleep(1.5)
    path = OUT / f"table_preflop_{vp_name}.png"
    page.screenshot(path=str(path), full_page=False)
    print(f"  ✓ {path.name}")

    # 操作栏（如果轮到自己）
    action_bar = page.locator("#action-bar, .action-bar, [data-testid='action-bar']").first
    if action_bar.is_visible():
        path = OUT / f"table_action_bar_{vp_name}.png"
        page.screenshot(path=str(path), full_page=False)
        print(f"  ✓ {path.name}")

    # 等翻牌
    time.sleep(5)
    path = OUT / f"table_mid_game_{vp_name}.png"
    page.screenshot(path=str(path), full_page=False)
    print(f"  ✓ {path.name}")


def shot_themes(page, table_id, token):
    """10 种主题各截一张（desktop 只截）"""
    url = f"{BASE}/?table={table_id}&token={token}"
    page.goto(url)
    page.wait_for_load_state("networkidle")
    time.sleep(1)
    for i in range(1, 11):
        # 尝试点击主题按钮
        btn = page.locator(f"[data-theme='{i}'], .theme-btn:nth-child({i})").first
        if btn.count() > 0:
            btn.click()
            time.sleep(0.3)
        else:
            # 通过 JS 切换
            page.evaluate(f"document.body.setAttribute('data-theme', '{i}')")
            time.sleep(0.3)
        path = OUT / f"theme_{i:02d}.png"
        page.screenshot(path=str(path), full_page=False)
    print(f"  ✓ 10 个主题截图完成")


# ──────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────

def run(mode="all"):
    # 检查服务是否运行
    try:
        requests.get(BASE, timeout=3)
    except Exception:
        print(f"❌ 服务未运行，请先执行: python3 app.py")
        print(f"   然后重新运行此脚本")
        sys.exit(1)

    table_id, token = None, None
    if mode in ("all", "table", "themes"):
        print("🎲 创建测试牌桌（等待机器人填充，约4秒）...")
        try:
            table_id, token = create_table_with_bots()
            print(f"   牌桌 ID: {table_id}")
        except Exception as e:
            print(f"⚠️  创建牌桌失败（跳过牌桌截图）: {e}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        for vp_name, vp in VIEWPORTS.items():
            if vp_name == "mobile" and mode == "themes":
                continue  # 主题只截 desktop

            print(f"\n📐 视口: {vp_name} ({vp['width']}×{vp['height']})")
            ctx = browser.new_context(viewport=vp)
            page = ctx.new_page()
            page.set_default_timeout(15000)

            if mode in ("all", "lobby"):
                print("  [大厅]")
                shot_lobby(page, vp_name)

            if mode in ("all", "table") and table_id:
                print("  [牌桌]")
                shot_table_states(page, vp_name, table_id, token)

            ctx.close()

        if mode in ("all", "themes") and table_id:
            print(f"\n🎨 [主题]")
            ctx = browser.new_context(viewport=VIEWPORTS["desktop"])
            page = ctx.new_page()
            shot_themes(page, table_id, token)
            ctx.close()

        browser.close()

    # 汇总
    shots = sorted(OUT.glob("*.png"))
    print(f"\n✅ 共 {len(shots)} 张截图保存在: {OUT}/")
    for f in shots:
        size_kb = f.stat().st_size // 1024
        print(f"   {f.name}  ({size_kb} KB)")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    run(mode)

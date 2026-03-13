# tests/frontend/test_lobby_page.py
# 大厅页：牌桌列表、创建牌桌、马上游玩

import pytest
from playwright.sync_api import Page, expect


def test_lobby_page_loads(page: Page, base_url: str):
    """大厅页可打开，标题与主要区域存在。"""
    page.goto("/lobby")
    expect(page).to_have_title(lambda t: "大厅" in t or "DZPoker" in t)
    expect(page.locator("h1.lobby-title")).to_contain_text("大厅")
    expect(page.locator("#table-list")).to_be_visible()
    expect(page.locator("#create-table-btn")).to_be_visible()
    expect(page.locator("#quick-start-btn")).to_be_visible()


def test_lobby_table_list_loading_or_rendered(page: Page, base_url: str):
    """牌桌列表区域先显示加载中或最终渲染出牌桌/占位。"""
    page.goto("/lobby")
    table_list = page.locator("#table-list")
    table_list.wait_for(state="visible", timeout=5000)
    # 要么是「加载中…」，要么是 .table-card 或 .lobby-loading 消失后的内容
    loading = page.locator(".lobby-loading")
    cards = page.locator(".table-card")
    # 等待一下让前端请求完成
    page.wait_for_timeout(2000)
    has_loading = loading.is_visible()
    has_cards = cards.count() > 0
    assert has_loading or has_cards, "牌桌列表应有加载提示或牌桌卡片"


def test_lobby_create_table_panel_opens(page: Page, base_url: str):
    """点击「创建牌桌」后弹出创建面板，含表单与取消按钮。"""
    page.goto("/lobby")
    page.locator("#create-table-btn").click()
    panel = page.locator("#create-table-panel")
    expect(panel).to_be_visible()
    expect(panel.locator("#create-table-title")).to_contain_text("创建牌桌")
    expect(panel.locator("#ct-name")).to_be_visible()
    expect(panel.locator("#ct-sb")).to_be_visible()
    expect(panel.locator("#ct-bb")).to_be_visible()
    expect(panel.locator("#create-table-cancel")).to_be_visible()


def test_lobby_filters_exist(page: Page, base_url: str):
    """筛选控件存在：盲注、人数、应用按钮。"""
    page.goto("/lobby")
    expect(page.locator("#filter-blinds")).to_be_visible()
    expect(page.locator("#filter-players")).to_be_visible()
    expect(page.locator("#filter-apply")).to_be_visible()

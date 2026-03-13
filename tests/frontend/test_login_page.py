# tests/frontend/test_login_page.py
# 登录页：表单、提交、错误提示

import pytest
from playwright.sync_api import Page, expect


def test_login_page_loads(page: Page, base_url: str):
    """登录页可打开，含标题与登录表单。"""
    page.goto("/login")
    expect(page).to_have_title(lambda t: "登录" in t or "DZPoker" in t)
    expect(page.locator("#login-form")).to_be_visible()
    expect(page.locator("#username")).to_be_visible()
    expect(page.locator("#password")).to_be_visible()
    expect(page.locator("#login-form button[type='submit']")).to_be_visible()


def test_login_form_accepts_input(page: Page, base_url: str):
    """可在用户名、密码框输入。"""
    page.goto("/login")
    page.locator("#username").fill("testuser")
    page.locator("#password").fill("test1234")
    expect(page.locator("#username")).to_have_value("testuser")
    expect(page.locator("#password")).to_have_value("test1234")


def test_login_register_link_exists(page: Page, base_url: str):
    """存在「立即注册」链接。"""
    page.goto("/login")
    link = page.get_by_role("link", name=lambda s: "注册" in (s or ""))
    expect(link).to_be_visible()
    expect(link).to_have_attribute("href", "/register")

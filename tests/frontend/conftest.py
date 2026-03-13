# tests/frontend/conftest.py
# 前端 E2E 测试：Playwright 浏览器 + 页面 fixture
# 运行前需先启动服务端：python app.py
# 运行：pytest tests/frontend -v
# 有界面：pytest tests/frontend -v --headed
# 指定地址：DZPOKER_API_BASE=http://127.0.0.1:8080 pytest tests/frontend -v

import os
import pytest
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

BASE_URL = os.environ.get("DZPOKER_API_BASE", "http://127.0.0.1:8080").rstrip("/")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=os.environ.get("HEADLESS", "true").lower() == "true")
        yield browser
        browser.close()


@pytest.fixture
def context(browser: Browser, base_url: str):
    context = browser.new_context(base_url=base_url)
    yield context
    context.close()


@pytest.fixture
def page(context: BrowserContext):
    return context.new_page()

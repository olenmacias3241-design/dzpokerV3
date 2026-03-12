# dzpokerV3/tests/api/conftest.py
# 后端 API 测试的 pytest 配置与 fixture
# 运行：pytest tests/api -v（需先启动服务端 python app.py）
# 指定地址：DZPOKER_API_BASE=http://127.0.0.1:5002 pytest tests/api -v

import os
import pytest
import requests

BASE_URL = os.environ.get("DZPOKER_API_BASE", "http://127.0.0.1:8080").rstrip("/")
DEFAULT_TIMEOUT = 10.0


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def timeout():
    return DEFAULT_TIMEOUT


@pytest.fixture
def guest_token(base_url, timeout):
    """游客登录，返回 token。"""
    r = requests.post(
        f"{base_url}/api/login",
        json={"username": "ApiTestGuest"},
        timeout=timeout,
    )
    assert r.status_code == 200, f"登录失败: {r.status_code} {r.text}"
    data = r.json()
    assert data.get("ok") and data.get("token"), f"登录响应异常: {data}"
    return data["token"]


@pytest.fixture
def table_id(base_url, guest_token, timeout):
    """创建一张牌桌并返回 table_id。"""
    r = requests.post(
        f"{base_url}/api/lobby/tables",
        json={
            "tableName": "API测试桌",
            "sb": 5,
            "bb": 10,
            "maxPlayers": 6,
        },
        timeout=timeout,
    )
    assert r.status_code == 200, f"创建牌桌失败: {r.status_code} {r.text}"
    return r.json()["tableId"]


@pytest.fixture
def seated_at_table(base_url, table_id, guest_token, timeout):
    """已入座（座位 0）的 (token, table_id)。"""
    r = requests.post(
        f"{base_url}/api/tables/{table_id}/sit",
        json={"token": guest_token, "seat": 0},
        timeout=timeout,
    )
    assert r.status_code == 200, f"入座失败: {r.status_code} {r.text}"
    return guest_token, table_id

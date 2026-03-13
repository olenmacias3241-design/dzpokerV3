# dzpokerV3/tests/api/test_api_backend.py
# 后端 HTTP API 接口测试（本目录下运行：pytest tests/api -v）
# 需先启动服务端：python app.py

import pytest
import requests


# ---------- 健康与页面 ----------
class TestPing:
    def test_ping_returns_200(self, base_url, timeout):
        r = requests.get(f"{base_url}/ping", timeout=timeout)
        assert r.status_code == 200
        assert "OK" in r.text or r.text.strip() == "OK"


# ---------- 游客登录 ----------
class TestGuestLogin:
    def test_login_success(self, base_url, timeout):
        r = requests.post(
            f"{base_url}/api/login",
            json={"username": "TestUser"},
            timeout=timeout,
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert "token" in data
        assert "userId" in data
        assert data.get("username") == "TestUser"

    def test_login_empty_username_fails(self, base_url, timeout):
        r = requests.post(
            f"{base_url}/api/login",
            json={"username": ""},
            timeout=timeout,
        )
        assert r.status_code == 200  # 当前实现返回 200
        data = r.json()
        assert data.get("ok") is False or "message" in data


# ---------- 认证 API（需数据库，失败则跳过）----------
class TestAuthRegisterLogin:
    def test_auth_register(self, base_url, timeout):
        r = requests.post(
            f"{base_url}/api/auth/register",
            json={
                "username": "apitestuser",
                "password": "test1234",
                "email": "apitest@example.com",
            },
            timeout=timeout,
        )
        if r.status_code == 500 or (r.status_code == 400 and "数据库" in r.text):
            pytest.skip("数据库未配置或连接失败，跳过注册测试")
        if r.status_code == 400 and "已存在" in r.json().get("message", ""):
            pytest.skip("测试用户已存在，跳过注册")
        assert r.status_code == 200, f"注册失败: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("ok") is True
        assert "token" in data
        assert "userId" in data

    def test_auth_login(self, base_url, timeout):
        r = requests.post(
            f"{base_url}/api/auth/login",
            json={"username": "apitestuser", "password": "test1234"},
            timeout=timeout,
        )
        if r.status_code == 500:
            pytest.skip("数据库未配置，跳过登录测试")
        if r.status_code == 401:
            pytest.skip("无测试账号，跳过登录测试")
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert "token" in data
        assert "userProfile" in data


# ---------- auth/me（需 token）----------
class TestAuthMe:
    def test_auth_me_with_guest_token(self, base_url, guest_token, timeout):
        r = requests.get(
            f"{base_url}/api/auth/me",
            headers={"Authorization": f"Bearer {guest_token}"},
            timeout=timeout,
        )
        if r.status_code == 401:
            pytest.skip("auth/me 仅支持 JWT，游客 token 无效")
        if r.status_code == 500:
            pytest.skip("auth/me 对游客 token 返回 500（依赖 DB 或 JWT）")
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True

    def test_auth_me_without_token_returns_401(self, base_url, timeout):
        r = requests.get(f"{base_url}/api/auth/me", timeout=timeout)
        assert r.status_code == 401


# ---------- 大厅 ----------
class TestLobby:
    def test_lobby_tables_list(self, base_url, timeout):
        r = requests.get(f"{base_url}/api/lobby/tables", timeout=timeout)
        assert r.status_code == 200
        data = r.json()
        assert "tables" in data
        assert isinstance(data["tables"], list)

    def test_lobby_create_table(self, base_url, timeout):
        r = requests.post(
            f"{base_url}/api/lobby/tables",
            json={
                "tableName": "pytest_create_table",
                "sb": 5,
                "bb": 10,
                "maxPlayers": 6,
            },
            timeout=timeout,
        )
        assert r.status_code == 200
        data = r.json()
        assert "tableId" in data
        assert data.get("tableName") or data.get("blinds") or data.get("tableId")

    def test_lobby_quick_start_requires_token(self, base_url, timeout):
        r = requests.post(
            f"{base_url}/api/lobby/quick-start",
            json={},
            timeout=timeout,
        )
        assert r.status_code in (400, 401)
        data = r.json()
        assert "message" in data or "error" in data

    def test_lobby_quick_start_with_token(self, base_url, guest_token, timeout):
        r = requests.post(
            f"{base_url}/api/lobby/quick-start",
            json={"token": guest_token},
            timeout=timeout,
        )
        assert r.status_code == 200
        data = r.json()
        assert "tableId" in data
        assert "seatNumber" in data


# ---------- 牌桌：获取状态、入座、离开 ----------
class TestTableStateAndSit:
    def test_get_table_state_requires_token(self, base_url, table_id, timeout):
        r = requests.get(f"{base_url}/api/tables/{table_id}", timeout=timeout)
        assert r.status_code == 404  # 无 token 时当前实现返回 404

    def test_get_table_state_with_token(self, base_url, seated_at_table, timeout):
        token, table_id = seated_at_table
        r = requests.get(
            f"{base_url}/api/tables/{table_id}",
            params={"token": token},
            timeout=timeout,
        )
        assert r.status_code == 200
        data = r.json()
        assert "tableId" in data or "status" in data
        assert data.get("my_seat") == 0

    def test_sit_success(self, base_url, table_id, guest_token, timeout):
        r = requests.post(
            f"{base_url}/api/tables/{table_id}/sit",
            json={"token": guest_token, "seat": 0},
            timeout=timeout,
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("seatNumber") == 0 or data.get("tableId") == table_id

    def test_leave_table(self, base_url, seated_at_table, timeout):
        token, table_id = seated_at_table
        r = requests.post(
            f"{base_url}/api/tables/{table_id}/leave",
            json={"token": token},
            timeout=timeout,
        )
        assert r.status_code == 200
        data = r.json()
        assert "status" in data or "seats" in data or "tableId" in data


# ---------- 牌桌：开局、对局 API ----------
class TestTableStartAndGame:
    def test_start_game_after_two_players(self, base_url, timeout):
        login_a = requests.post(
            f"{base_url}/api/login",
            json={"username": "StartTestA"},
            timeout=timeout,
        )
        login_b = requests.post(
            f"{base_url}/api/login",
            json={"username": "StartTestB"},
            timeout=timeout,
        )
        assert login_a.status_code == 200 and login_b.status_code == 200
        token_a = login_a.json()["token"]
        token_b = login_b.json()["token"]

        create = requests.post(
            f"{base_url}/api/lobby/tables",
            json={"tableName": "StartTest", "sb": 5, "bb": 10, "maxPlayers": 6},
            timeout=timeout,
        )
        assert create.status_code == 200
        tid = create.json()["tableId"]

        requests.post(
            f"{base_url}/api/tables/{tid}/sit",
            json={"token": token_a, "seat": 0},
            timeout=timeout,
        )
        requests.post(
            f"{base_url}/api/tables/{tid}/sit",
            json={"token": token_b, "seat": 1},
            timeout=timeout,
        )

        r = requests.post(
            f"{base_url}/api/tables/{tid}/start",
            json={"token": token_a},
            timeout=timeout,
        )
        assert r.status_code == 200, f"开局失败: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("status") == "playing" or "game_state" in data

    def test_game_state_requires_auth(self, base_url, table_id, timeout):
        r = requests.get(
            f"{base_url}/api/tables/{table_id}/game_state",
            timeout=timeout,
        )
        assert r.status_code in (401, 403, 404)

    def test_game_state_with_token(self, base_url, seated_at_table, timeout):
        token, table_id = seated_at_table
        r = requests.get(
            f"{base_url}/api/tables/{table_id}/game_state",
            params={"token": token},
            timeout=timeout,
        )
        if r.status_code == 404:
            pytest.skip("牌桌未开局，无 game_state")
        assert r.status_code == 200
        data = r.json()
        assert "stage" in data or "pot" in data or "players" in data or "seats" in data


# ---------- 对局：action、deal_next、emote ----------
class TestTableAction:
    def test_action_requires_auth(self, base_url, table_id, timeout):
        r = requests.post(
            f"{base_url}/api/tables/{table_id}/action",
            json={"action": "fold", "amount": 0},
            timeout=timeout,
        )
        assert r.status_code in (400, 401, 403)

    def test_action_with_token_when_not_playing(self, base_url, seated_at_table, timeout):
        token, table_id = seated_at_table
        r = requests.post(
            f"{base_url}/api/tables/{table_id}/action",
            json={"token": token, "action": "fold", "amount": 0},
            timeout=timeout,
        )
        assert r.status_code in (200, 400)
        if r.status_code == 400:
            assert "error" in r.json()

    def test_emote_with_token(self, base_url, seated_at_table, timeout):
        token, table_id = seated_at_table
        r = requests.post(
            f"{base_url}/api/tables/{table_id}/emote",
            json={"token": token, "emote": "smile"},
            timeout=timeout,
        )
        assert r.status_code == 200


# ---------- 商城 ----------
class TestMall:
    def test_mall_products(self, base_url, timeout):
        r = requests.get(f"{base_url}/api/mall/products", timeout=timeout)
        assert r.status_code == 200
        data = r.json()
        assert "products" in data
        assert isinstance(data["products"], list)


# ---------- 俱乐部（可选）----------
class TestClubs:
    def test_clubs_list(self, base_url, timeout):
        r = requests.get(f"{base_url}/api/clubs", timeout=timeout)
        if r.status_code == 500:
            pytest.skip("俱乐部服务依赖数据库或未实现")
        assert r.status_code == 200
        data = r.json()
        assert "clubs" in data


# ---------- 回放 API ----------
class TestReplay:
    def test_replay_hands_list(self, base_url, timeout):
        r = requests.get(
            f"{base_url}/api/replay/hands",
            params={"limit": 5},
            timeout=timeout,
        )
        if r.status_code == 500:
            pytest.skip("回放依赖数据库")
        assert r.status_code == 200
        data = r.json()
        assert "hands" in data or "error" in data
        if "hands" in data:
            assert isinstance(data["hands"], list)


# ---------- add_bot ----------
class TestAddBot:
    def test_add_bot_requires_table(self, base_url, guest_token, timeout):
        r = requests.post(
            f"{base_url}/api/tables/99999/add_bot",
            json={"count": 1, "autoStart": False},
            timeout=timeout,
        )
        assert r.status_code in (400, 404, 500)

    def test_add_bot_success(self, base_url, table_id, timeout):
        r = requests.post(
            f"{base_url}/api/tables/{table_id}/add_bot",
            json={"count": 1, "autoStart": False},
            timeout=timeout,
        )
        assert r.status_code == 200
        data = r.json()
        assert "added" in data or "table" in data

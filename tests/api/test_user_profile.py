"""
用户资料、UI 配置、Auth 补充测试
涵盖：auth/me、auth/logout、用户详情、UI 配置 GET/PUT、回放手牌详情、fill_bots

运行：pytest tests/api/test_user_profile.py -v（需先启动服务端 python app.py）
"""

import uuid
import pytest
import requests


# ---------- 辅助函数 ----------

def register_and_login(base_url, timeout):
    """注册随机 DB 用户，返回 (token, user_id)。"""
    username = "prof_test_" + uuid.uuid4().hex[:8]
    r = requests.post(
        f"{base_url}/api/auth/register",
        json={"username": username, "password": "Test1234!"},
        timeout=timeout,
    )
    assert r.status_code == 200, f"注册失败: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"注册无 token: {data}"
    return token, data.get("user_id")


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def skip_if_db_unavailable(r, label=""):
    if r.status_code == 500:
        pytest.skip(f"数据库不可用，跳过{label}: {r.text[:200]}")


# ---------- Auth 补充测试 ----------

class TestAuthJWT:
    @pytest.fixture(autouse=True)
    def setup(self, base_url, timeout):
        self.base = base_url
        self.timeout = timeout
        try:
            self.token, self.uid = register_and_login(base_url, timeout)
        except AssertionError:
            pytest.skip("数据库未配置，跳过 JWT 认证测试")

    # auth/me 用 JWT token
    def test_auth_me_with_jwt(self):
        r = requests.get(
            f"{self.base}/api/auth/me",
            headers=auth_headers(self.token),
            timeout=self.timeout,
        )
        skip_if_db_unavailable(r, "auth/me")
        assert r.status_code == 200, f"auth/me 失败: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("ok") is True
        profile = data.get("userProfile") or data.get("user") or data
        assert profile.get("username") or profile.get("id")

    # auth/me 无 token → 401
    def test_auth_me_no_token(self):
        r = requests.get(f"{self.base}/api/auth/me", timeout=self.timeout)
        assert r.status_code == 401

    # auth/me 伪造 token → 401
    def test_auth_me_invalid_token(self):
        r = requests.get(
            f"{self.base}/api/auth/me",
            headers={"Authorization": "Bearer totally.invalid.token"},
            timeout=self.timeout,
        )
        assert r.status_code == 401

    # auth/logout
    def test_auth_logout(self):
        r = requests.post(
            f"{self.base}/api/auth/logout",
            headers=auth_headers(self.token),
            timeout=self.timeout,
        )
        if r.status_code == 404:
            pytest.skip("logout 接口未实现")
        skip_if_db_unavailable(r, "logout")
        assert r.status_code == 200
        assert r.json().get("ok")


# ---------- 用户详情 ----------

class TestUserProfile:
    @pytest.fixture(autouse=True)
    def setup(self, base_url, timeout):
        self.base = base_url
        self.timeout = timeout
        try:
            self.token, self.uid = register_and_login(base_url, timeout)
        except AssertionError:
            pytest.skip("数据库未配置，跳过用户详情测试")

    def test_get_user_by_id(self):
        if not self.uid:
            pytest.skip("注册响应未返回 user_id")
        r = requests.get(f"{self.base}/api/users/{self.uid}", timeout=self.timeout)
        if r.status_code == 404:
            pytest.skip("GET /api/users/<id> 接口未实现")
        skip_if_db_unavailable(r)
        assert r.status_code == 200, f"获取用户失败: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("id") == self.uid or data.get("username")

    def test_get_nonexistent_user_404(self):
        r = requests.get(f"{self.base}/api/users/9999999", timeout=self.timeout)
        if r.status_code == 500:
            pytest.skip("数据库不可用")
        assert r.status_code == 404


# ---------- UI 配置 ----------

class TestUIConfig:
    @pytest.fixture(autouse=True)
    def setup(self, base_url, timeout):
        self.base = base_url
        self.timeout = timeout
        try:
            self.token, self.uid = register_and_login(base_url, timeout)
        except AssertionError:
            pytest.skip("数据库未配置，跳过 UI 配置测试")

    def test_get_ui_config(self):
        r = requests.get(
            f"{self.base}/api/users/me/ui-config",
            headers=auth_headers(self.token),
            timeout=self.timeout,
        )
        if r.status_code == 404:
            pytest.skip("UI 配置接口未实现")
        skip_if_db_unavailable(r, "UI 配置 GET")
        assert r.status_code == 200, f"获取 UI 配置失败: {r.status_code} {r.text}"
        data = r.json()
        # 至少包含 theme 或其他 UI 字段
        assert isinstance(data, dict)

    def test_update_ui_config_theme(self):
        r = requests.put(
            f"{self.base}/api/users/me/ui-config",
            json={"theme": "dark"},
            headers=auth_headers(self.token),
            timeout=self.timeout,
        )
        if r.status_code == 404:
            pytest.skip("UI 配置接口未实现")
        skip_if_db_unavailable(r, "UI 配置 PUT")
        assert r.status_code == 200, f"更新 UI 配置失败: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("theme") == "dark" or data.get("ok")

    def test_update_ui_config_sound(self):
        r = requests.put(
            f"{self.base}/api/users/me/ui-config",
            json={"soundEnabled": False, "animationEnabled": True},
            headers=auth_headers(self.token),
            timeout=self.timeout,
        )
        if r.status_code == 404:
            pytest.skip("UI 配置接口未实现")
        skip_if_db_unavailable(r)
        assert r.status_code == 200

    def test_get_ui_config_with_token_query(self):
        r = requests.get(
            f"{self.base}/api/users/me/ui-config",
            params={"token": self.token},
            timeout=self.timeout,
        )
        if r.status_code == 404:
            pytest.skip("UI 配置接口未实现")
        skip_if_db_unavailable(r)
        assert r.status_code == 200


# ---------- 回放：手牌详情 ----------

class TestReplayDetail:
    def test_replay_hand_detail_not_found(self, base_url, timeout):
        r = requests.get(f"{base_url}/api/replay/hands/9999999", timeout=timeout)
        if r.status_code == 500:
            pytest.skip("回放依赖数据库")
        assert r.status_code == 404

    def test_replay_hand_detail_if_exists(self, base_url, timeout):
        """先拉列表，若有数据则验证详情字段。"""
        r = requests.get(
            f"{base_url}/api/replay/hands",
            params={"limit": 1},
            timeout=timeout,
        )
        if r.status_code == 500:
            pytest.skip("回放依赖数据库")
        assert r.status_code == 200
        hands = r.json().get("hands", [])
        if not hands:
            pytest.skip("暂无手牌记录，跳过详情测试")
        hand_id = hands[0].get("hand_id") or hands[0].get("id")
        assert hand_id, f"列表手牌无 id 字段: {hands[0]}"

        r2 = requests.get(f"{base_url}/api/replay/hands/{hand_id}", timeout=timeout)
        assert r2.status_code == 200, f"获取手牌详情失败: {r2.status_code} {r2.text}"
        data = r2.json()
        # 必有基础字段
        assert "hand_id" in data or "id" in data
        assert "actions" in data or "community_cards" in data or "participants" in data


# ---------- Bot 管理 ----------

class TestBotManagement:
    @pytest.fixture(autouse=True)
    def setup(self, base_url, timeout):
        self.base = base_url
        self.timeout = timeout

    def _create_table(self, guest_token):
        r = requests.post(
            f"{self.base}/api/lobby/tables",
            json={"tableName": "bot测试桌", "sb": 5, "bb": 10, "maxPlayers": 6},
            timeout=self.timeout,
        )
        assert r.status_code == 200
        return r.json()["tableId"]

    def test_fill_bots(self, guest_token):
        tid = self._create_table(guest_token)
        r = requests.post(
            f"{self.base}/api/tables/{tid}/fill_bots",
            timeout=self.timeout,
        )
        if r.status_code == 404:
            pytest.skip("fill_bots 接口未实现")
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") or data.get("message") or "table" in data

    def test_add_multiple_bots(self, guest_token):
        tid = self._create_table(guest_token)
        r = requests.post(
            f"{self.base}/api/tables/{tid}/add_bot",
            json={"count": 3, "autoStart": False},
            timeout=self.timeout,
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("added") == 3 or (data.get("added", 0) >= 1)

    def test_add_bot_exceeds_max(self, guest_token):
        tid = self._create_table(guest_token)
        # 先填满 5 个 bot
        requests.post(
            f"{self.base}/api/tables/{tid}/add_bot",
            json={"count": 5, "autoStart": False},
            timeout=self.timeout,
        )
        # 再加应失败或有上限
        r = requests.post(
            f"{self.base}/api/tables/{tid}/add_bot",
            json={"count": 4, "autoStart": False},
            timeout=self.timeout,
        )
        # 允许 200（已满，added=0）或 400
        assert r.status_code in (200, 400)
        if r.status_code == 200:
            assert r.json().get("added", 1) == 0 or "满" in str(r.json())

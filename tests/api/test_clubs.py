"""
俱乐部 API 测试
运行：pytest tests/api/test_clubs.py -v（需先启动服务端 python app.py）
"""

import uuid
import pytest
import requests


# ---------- 辅助函数 ----------

def register_and_login(base_url, timeout):
    """注册并登录一个随机用户，返回 (token, user_id)。"""
    username = "club_test_" + uuid.uuid4().hex[:8]
    password = "Test1234!"
    r = requests.post(
        f"{base_url}/api/auth/register",
        json={"username": username, "password": password},
        timeout=timeout,
    )
    assert r.status_code == 200, f"注册失败: {r.status_code} {r.text}"
    data = r.json()
    assert data.get("access_token"), f"注册无 token: {data}"
    return data["access_token"], data.get("user_id")


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- 测试 ----------

class TestClubs:
    @pytest.fixture(autouse=True)
    def setup(self, base_url, timeout):
        self.base = base_url
        self.timeout = timeout
        self.token1, self.uid1 = register_and_login(base_url, timeout)
        self.token2, self.uid2 = register_and_login(base_url, timeout)

    # 1. 列表
    def test_list_clubs(self):
        r = requests.get(f"{self.base}/api/clubs", timeout=self.timeout)
        assert r.status_code == 200
        data = r.json()
        assert "clubs" in data
        assert isinstance(data["clubs"], list)

    # 2. 创建俱乐部
    def test_create_club(self):
        name = "测试俱乐部_" + uuid.uuid4().hex[:6]
        r = requests.post(
            f"{self.base}/api/clubs",
            json={"name": name, "description": "单元测试俱乐部"},
            headers=auth_headers(self.token1),
            timeout=self.timeout,
        )
        assert r.status_code == 200, f"创建失败: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("id")
        assert data.get("name") == name
        self.club_id = data["id"]
        return data["id"]

    # 3. 创建后能查到详情（含成员和用户名）
    def test_get_club_detail(self):
        club_id = self.test_create_club()
        r = requests.get(f"{self.base}/api/clubs/{club_id}", timeout=self.timeout)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == club_id
        assert "members" in data
        assert len(data["members"]) >= 1
        # 成员应有 username 字段
        m = data["members"][0]
        assert "username" in m, f"成员缺少 username 字段: {m}"

    # 4. 其他用户加入
    def test_join_club(self):
        club_id = self.test_create_club()
        r = requests.post(
            f"{self.base}/api/clubs/{club_id}/join",
            json={},
            headers=auth_headers(self.token2),
            timeout=self.timeout,
        )
        assert r.status_code == 200, f"加入失败: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("message") or data.get("ok")

    # 5. 重复加入应返回 400
    def test_join_duplicate(self):
        club_id = self.test_create_club()
        requests.post(
            f"{self.base}/api/clubs/{club_id}/join",
            json={},
            headers=auth_headers(self.token2),
            timeout=self.timeout,
        )
        r = requests.post(
            f"{self.base}/api/clubs/{club_id}/join",
            json={},
            headers=auth_headers(self.token2),
            timeout=self.timeout,
        )
        assert r.status_code == 400
        assert r.json().get("error")

    # 6. 成员离开
    def test_leave_club(self):
        club_id = self.test_create_club()
        requests.post(
            f"{self.base}/api/clubs/{club_id}/join",
            json={},
            headers=auth_headers(self.token2),
            timeout=self.timeout,
        )
        r = requests.post(
            f"{self.base}/api/clubs/{club_id}/leave",
            json={},
            headers=auth_headers(self.token2),
            timeout=self.timeout,
        )
        assert r.status_code == 200, f"离开失败: {r.status_code} {r.text}"
        assert r.json().get("ok")

    # 7. 所有者不能离开
    def test_owner_cannot_leave(self):
        club_id = self.test_create_club()
        r = requests.post(
            f"{self.base}/api/clubs/{club_id}/leave",
            json={},
            headers=auth_headers(self.token1),
            timeout=self.timeout,
        )
        assert r.status_code == 400
        assert "所有者" in r.json().get("error", "")

    # 8. 未登录创建应返回 401
    def test_create_club_unauthorized(self):
        r = requests.post(
            f"{self.base}/api/clubs",
            json={"name": "未授权测试"},
            timeout=self.timeout,
        )
        assert r.status_code == 401

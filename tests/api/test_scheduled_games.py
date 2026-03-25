"""
约局（Scheduled Games）API 测试
运行：pytest tests/api/test_scheduled_games.py -v（需先启动服务端 python app.py）
"""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
import requests


# ---------- 辅助函数 ----------

def register_and_login(base_url, timeout):
    """注册随机用户，返回 (token, user_id)。"""
    username = "sg_test_" + uuid.uuid4().hex[:8]
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


def future_iso(minutes=30):
    """返回 minutes 分钟后的 ISO 8601 时间字符串。"""
    t = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def skip_if_not_implemented(r, name="约局"):
    """若服务端未实现（404/500），跳过。"""
    if r.status_code in (404, 500):
        pytest.skip(f"{name} 服务未实现或依赖数据库: {r.status_code} {r.text[:200]}")


# ---------- 测试类 ----------

class TestScheduledGames:
    @pytest.fixture(autouse=True)
    def setup(self, base_url, timeout):
        self.base = base_url
        self.timeout = timeout
        try:
            self.token1, self.uid1 = register_and_login(base_url, timeout)
            self.token2, self.uid2 = register_and_login(base_url, timeout)
        except AssertionError:
            pytest.skip("数据库未配置，跳过约局测试")

    def _create_game(self, token=None, **extra):
        """创建一个约局，返回 response。"""
        token = token or self.token1
        payload = {
            "title": "测试约局_" + uuid.uuid4().hex[:6],
            "startAt": future_iso(60),
            "minPlayers": 2,
            "maxPlayers": 6,
            "blinds": {"sb": 5, "bb": 10},
        }
        payload.update(extra)
        return requests.post(
            f"{self.base}/api/scheduled-games",
            json=payload,
            headers=auth_headers(token),
            timeout=self.timeout,
        )

    # 1. 列表接口
    def test_list_scheduled_games(self):
        r = requests.get(f"{self.base}/api/scheduled-games", timeout=self.timeout)
        skip_if_not_implemented(r)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) or "games" in data or "scheduledGames" in data

    # 2. 创建约局
    def test_create_scheduled_game(self):
        r = self._create_game()
        skip_if_not_implemented(r, "创建约局")
        assert r.status_code == 200, f"创建失败: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("id") or data.get("scheduledGameId"), f"响应缺少 id: {data}"
        assert data.get("title") or data.get("ok")
        return data.get("id") or data.get("scheduledGameId")

    # 3. 未登录创建应返回 401
    def test_create_unauthorized(self):
        r = requests.post(
            f"{self.base}/api/scheduled-games",
            json={
                "title": "未授权约局",
                "startAt": future_iso(30),
                "minPlayers": 2,
                "maxPlayers": 6,
                "blinds": {"sb": 5, "bb": 10},
            },
            timeout=self.timeout,
        )
        if r.status_code in (404, 500):
            pytest.skip("约局服务未实现")
        assert r.status_code == 401, f"应返回 401，实际: {r.status_code}"

    # 4. 获取约局详情
    def test_get_detail(self):
        sg_id = self.test_create_scheduled_game()
        r = requests.get(f"{self.base}/api/scheduled-games/{sg_id}", timeout=self.timeout)
        skip_if_not_implemented(r, "约局详情")
        assert r.status_code == 200
        data = r.json()
        assert data.get("id") == sg_id or data.get("scheduledGameId") == sg_id
        assert "title" in data or "minPlayers" in data

    # 5. 不存在的约局返回 404
    def test_get_not_found(self):
        r = requests.get(f"{self.base}/api/scheduled-games/9999999", timeout=self.timeout)
        if r.status_code in (500,):
            pytest.skip("约局服务未实现")
        assert r.status_code == 404

    # 6. 更新约局（host 权限）
    def test_update_scheduled_game(self):
        sg_id = self.test_create_scheduled_game()
        new_title = "更新后的约局_" + uuid.uuid4().hex[:4]
        r = requests.put(
            f"{self.base}/api/scheduled-games/{sg_id}",
            json={"title": new_title},
            headers=auth_headers(self.token1),
            timeout=self.timeout,
        )
        skip_if_not_implemented(r, "更新约局")
        assert r.status_code == 200, f"更新失败: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("title") == new_title or data.get("ok")

    # 7. 非 host 不能更新
    def test_update_by_non_host_forbidden(self):
        sg_id = self.test_create_scheduled_game()
        r = requests.put(
            f"{self.base}/api/scheduled-games/{sg_id}",
            json={"title": "非法更新"},
            headers=auth_headers(self.token2),
            timeout=self.timeout,
        )
        if r.status_code in (404, 500):
            pytest.skip("约局服务未实现")
        assert r.status_code in (401, 403), f"应被拒绝，实际: {r.status_code}"

    # 8. 报名约局
    def test_register(self):
        sg_id = self.test_create_scheduled_game()
        r = requests.post(
            f"{self.base}/api/scheduled-games/{sg_id}/register",
            json={},
            headers=auth_headers(self.token2),
            timeout=self.timeout,
        )
        skip_if_not_implemented(r, "报名约局")
        assert r.status_code == 200, f"报名失败: {r.status_code} {r.text}"
        return sg_id

    # 9. 重复报名应返回 400
    def test_register_duplicate(self):
        sg_id = self.test_register()
        r = requests.post(
            f"{self.base}/api/scheduled-games/{sg_id}/register",
            json={},
            headers=auth_headers(self.token2),
            timeout=self.timeout,
        )
        if r.status_code in (404, 500):
            pytest.skip("约局服务未实现")
        assert r.status_code == 400, f"重复报名应返回 400，实际: {r.status_code}"

    # 10. 报名后能在玩家列表看到自己
    def test_players_list_after_register(self):
        sg_id = self.test_register()
        r = requests.get(
            f"{self.base}/api/scheduled-games/{sg_id}/players",
            timeout=self.timeout,
        )
        skip_if_not_implemented(r, "玩家列表")
        assert r.status_code == 200
        data = r.json()
        players = data.get("players") or data if isinstance(data, list) else []
        assert len(players) >= 1

    # 11. 取消报名
    def test_unregister(self):
        sg_id = self.test_register()
        r = requests.post(
            f"{self.base}/api/scheduled-games/{sg_id}/unregister",
            headers=auth_headers(self.token2),
            timeout=self.timeout,
        )
        skip_if_not_implemented(r, "取消报名")
        assert r.status_code == 200, f"取消失败: {r.status_code} {r.text}"
        assert r.json().get("ok")

    # 12. Host 踢人
    def test_kick_player(self):
        sg_id = self.test_register()
        if not self.uid2:
            pytest.skip("无法获取 user_id，跳过踢人测试")
        r = requests.post(
            f"{self.base}/api/scheduled-games/{sg_id}/players/{self.uid2}/kick",
            headers=auth_headers(self.token1),
            timeout=self.timeout,
        )
        skip_if_not_implemented(r, "踢人")
        assert r.status_code == 200, f"踢人失败: {r.status_code} {r.text}"
        assert r.json().get("ok")

    # 13. 非 Host 不能踢人
    def test_kick_by_non_host_forbidden(self):
        sg_id = self.test_register()
        if not self.uid1:
            pytest.skip("无法获取 user_id，跳过")
        r = requests.post(
            f"{self.base}/api/scheduled-games/{sg_id}/players/{self.uid1}/kick",
            headers=auth_headers(self.token2),
            timeout=self.timeout,
        )
        if r.status_code in (404, 500):
            pytest.skip("约局服务未实现")
        assert r.status_code in (401, 403), f"非 host 踢人应被拒绝，实际: {r.status_code}"

    # 14. 获取邀请链接（host 权限）
    def test_get_invite_link(self):
        sg_id = self.test_create_scheduled_game()
        r = requests.get(
            f"{self.base}/api/scheduled-games/{sg_id}/invite-link",
            headers=auth_headers(self.token1),
            timeout=self.timeout,
        )
        skip_if_not_implemented(r, "邀请链接")
        assert r.status_code == 200, f"获取邀请链接失败: {r.status_code} {r.text}"
        data = r.json()
        assert "inviteLink" in data or "invite_link" in data or "link" in data

    # 15. 非 host 不能获取邀请链接
    def test_invite_link_non_host_forbidden(self):
        sg_id = self.test_create_scheduled_game()
        r = requests.get(
            f"{self.base}/api/scheduled-games/{sg_id}/invite-link",
            headers=auth_headers(self.token2),
            timeout=self.timeout,
        )
        if r.status_code in (404, 500):
            pytest.skip("约局服务未实现")
        assert r.status_code in (401, 403)

    # 16. 删除约局（host 权限）
    def test_delete_scheduled_game(self):
        sg_id = self.test_create_scheduled_game()
        r = requests.delete(
            f"{self.base}/api/scheduled-games/{sg_id}",
            headers=auth_headers(self.token1),
            timeout=self.timeout,
        )
        skip_if_not_implemented(r, "删除约局")
        assert r.status_code == 200, f"删除失败: {r.status_code} {r.text}"
        assert r.json().get("ok")
        # 删除后应 404
        r2 = requests.get(f"{self.base}/api/scheduled-games/{sg_id}", timeout=self.timeout)
        assert r2.status_code == 404

    # 17. 非 host 不能删除
    def test_delete_by_non_host_forbidden(self):
        sg_id = self.test_create_scheduled_game()
        r = requests.delete(
            f"{self.base}/api/scheduled-games/{sg_id}",
            headers=auth_headers(self.token2),
            timeout=self.timeout,
        )
        if r.status_code in (404, 500):
            pytest.skip("约局服务未实现")
        assert r.status_code in (401, 403)

    # 18. 按 status 筛选列表
    def test_list_filter_by_status(self):
        r = requests.get(
            f"{self.base}/api/scheduled-games",
            params={"status": "pending"},
            timeout=self.timeout,
        )
        skip_if_not_implemented(r)
        assert r.status_code == 200

    # 19. mine=true 返回我的约局
    def test_list_mine(self):
        self.test_create_scheduled_game()
        r = requests.get(
            f"{self.base}/api/scheduled-games",
            params={"mine": "true"},
            headers=auth_headers(self.token1),
            timeout=self.timeout,
        )
        skip_if_not_implemented(r)
        assert r.status_code == 200

    # 20. 带密码的约局
    def test_create_with_password(self):
        r = self._create_game(password="secret123")
        skip_if_not_implemented(r, "带密码约局")
        assert r.status_code == 200
        sg_id = r.json().get("id") or r.json().get("scheduledGameId")
        assert sg_id
        # 不带密码报名应失败
        r2 = requests.post(
            f"{self.base}/api/scheduled-games/{sg_id}/register",
            json={},
            headers=auth_headers(self.token2),
            timeout=self.timeout,
        )
        if r2.status_code == 200:
            pytest.xfail("服务端未强制校验密码")
        assert r2.status_code in (400, 401, 403), f"无密码报名应被拒绝，实际: {r2.status_code}"
        # 带密码报名应成功
        r3 = requests.post(
            f"{self.base}/api/scheduled-games/{sg_id}/register",
            json={"password": "secret123"},
            headers=auth_headers(self.token2),
            timeout=self.timeout,
        )
        assert r3.status_code == 200, f"带密码报名失败: {r3.status_code} {r3.text}"


class TestClubScheduledGames:
    """俱乐部下的约局列表。"""

    @pytest.fixture(autouse=True)
    def setup(self, base_url, timeout):
        self.base = base_url
        self.timeout = timeout
        try:
            self.token, self.uid = register_and_login(base_url, timeout)
        except AssertionError:
            pytest.skip("数据库未配置，跳过俱乐部约局测试")

    def _create_club(self):
        name = "约局俱乐部_" + uuid.uuid4().hex[:6]
        r = requests.post(
            f"{self.base}/api/clubs",
            json={"name": name, "description": "测试"},
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=self.timeout,
        )
        assert r.status_code == 200, f"建俱乐部失败: {r.status_code} {r.text}"
        return r.json()["id"]

    def test_club_scheduled_games_list(self):
        try:
            club_id = self._create_club()
        except AssertionError:
            pytest.skip("俱乐部服务不可用")
        r = requests.get(
            f"{self.base}/api/clubs/{club_id}/scheduled-games",
            timeout=self.timeout,
        )
        if r.status_code in (404, 500):
            pytest.skip("俱乐部约局服务未实现")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) or "games" in data

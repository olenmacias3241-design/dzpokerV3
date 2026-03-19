"""
锦标赛 API 测试（SNG + MTT）
运行：pytest tests/api/test_tournaments.py -v（需先启动服务端 python app.py）
"""

import uuid
import pytest
import requests

# 测试用标准盲注结构
BLIND_LEVELS = [
    {"small_blind": 10, "big_blind": 20, "ante": 0, "duration_minutes": 5},
    {"small_blind": 25, "big_blind": 50, "ante": 5, "duration_minutes": 5},
    {"small_blind": 50, "big_blind": 100, "ante": 10, "duration_minutes": 5},
]

PAYOUT_SNG = [
    {"rank_from": 1, "rank_to": 1, "percent": 65},
    {"rank_from": 2, "rank_to": 2, "percent": 35},
]


def register_and_login(base_url, timeout):
    username = "tourn_test_" + uuid.uuid4().hex[:8]
    r = requests.post(
        f"{base_url}/api/auth/register",
        json={"username": username, "password": "Test1234!"},
        timeout=timeout,
    )
    assert r.status_code == 200, f"注册失败: {r.text}"
    data = r.json()
    return data["access_token"], data.get("user_id")


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestTournaments:
    @pytest.fixture(autouse=True)
    def setup(self, base_url, timeout):
        self.base = base_url
        self.timeout = timeout
        self.token1, _ = register_and_login(base_url, timeout)

    # 1. 列表接口返回数组 + camelCase 字段
    def test_list_tournaments(self):
        r = requests.get(f"{self.base}/api/tournaments", timeout=self.timeout)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        if len(data) > 0:
            t = data[0]
            assert "buyIn" in t, f"列表缺少 buyIn 字段: {t}"
            assert "maxPlayers" in t, f"列表缺少 maxPlayers 字段: {t}"
            assert "registeredCount" in t, f"列表缺少 registeredCount 字段: {t}"

    # 2. 管理员创建 SNG
    def test_admin_create_sng(self):
        r = requests.post(
            f"{self.base}/api/admin/tournaments",
            json={
                "type": "SNG",
                "name": f"测试SNG_{uuid.uuid4().hex[:6]}",
                "buy_in": 100,
                "fee": 10,
                "starting_stack": 3000,
                "max_players": 6,
                "min_players_to_start": 2,
                "blind_levels": BLIND_LEVELS,
                "payout_percents": PAYOUT_SNG,
            },
            timeout=self.timeout,
        )
        assert r.status_code == 200, f"创建失败: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("ok")
        assert data.get("id")
        assert data.get("type") == "SNG"
        return data["id"]

    # 3. 创建 MTT
    def test_admin_create_mtt(self):
        r = requests.post(
            f"{self.base}/api/admin/tournaments",
            json={
                "type": "MTT",
                "name": f"测试MTT_{uuid.uuid4().hex[:6]}",
                "buy_in": 200,
                "fee": 20,
                "starting_stack": 10000,
                "max_players": 50,
                "min_players_to_start": 4,
                "blind_levels": BLIND_LEVELS,
                "payout_percents": PAYOUT_SNG,
                "late_reg_minutes": 30,
            },
            timeout=self.timeout,
        )
        assert r.status_code == 200, f"MTT 创建失败: {r.status_code} {r.text}"
        data = r.json()
        assert data["type"] == "MTT"

    # 4. 详情接口 - myRegistration 初始为 false
    def test_tournament_detail_my_registration_false(self):
        t_id = self.test_admin_create_sng()
        r = requests.get(
            f"{self.base}/api/tournaments/{t_id}",
            headers=auth_headers(self.token1),
            timeout=self.timeout,
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("myRegistration") is False, f"未报名应为 false: {data}"

    # 5. 报名
    def test_register(self):
        t_id = self.test_admin_create_sng()
        r = requests.post(
            f"{self.base}/api/tournaments/{t_id}/register",
            headers=auth_headers(self.token1),
            timeout=self.timeout,
        )
        assert r.status_code == 200, f"报名失败: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("ok")
        return t_id

    # 6. 报名后 myRegistration 为 true
    def test_my_registration_after_register(self):
        t_id = self.test_register()
        r = requests.get(
            f"{self.base}/api/tournaments/{t_id}",
            headers=auth_headers(self.token1),
            timeout=self.timeout,
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("myRegistration") is True, f"报名后应为 true: {data}"
        assert data.get("registeredCount", 0) >= 1

    # 7. 重复报名应返回 400
    def test_register_duplicate(self):
        t_id = self.test_register()
        r = requests.post(
            f"{self.base}/api/tournaments/{t_id}/register",
            headers=auth_headers(self.token1),
            timeout=self.timeout,
        )
        assert r.status_code == 400

    # 8. 取消报名
    def test_unregister(self):
        t_id = self.test_register()
        r = requests.post(
            f"{self.base}/api/tournaments/{t_id}/unregister",
            headers=auth_headers(self.token1),
            timeout=self.timeout,
        )
        assert r.status_code == 200, f"取消失败: {r.status_code} {r.text}"
        assert r.json().get("ok")

    # 9. Admin 开赛：报名 2 个玩家后开赛
    def test_admin_start_tournament(self):
        t_id = self.test_admin_create_sng()
        token2, _ = register_and_login(self.base, self.timeout)

        # 两个用户分别报名
        r1 = requests.post(
            f"{self.base}/api/tournaments/{t_id}/register",
            headers=auth_headers(self.token1),
            timeout=self.timeout,
        )
        assert r1.status_code == 200, f"用户1报名失败: {r1.text}"

        r2 = requests.post(
            f"{self.base}/api/tournaments/{t_id}/register",
            headers=auth_headers(token2),
            timeout=self.timeout,
        )
        assert r2.status_code == 200, f"用户2报名失败: {r2.text}"

        # 管理员开赛
        r = requests.post(
            f"{self.base}/api/admin/tournaments/{t_id}/start",
            timeout=self.timeout,
        )
        assert r.status_code == 200, f"开赛失败: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("ok")
        assert data.get("game_table_id")

        # 赛事状态应变为 Running
        detail = requests.get(f"{self.base}/api/tournaments/{t_id}", timeout=self.timeout).json()
        assert detail.get("status") == "Running", f"状态应为 Running: {detail}"

    # 10. 按类型筛选
    def test_filter_by_type(self):
        self.test_admin_create_sng()
        r = requests.get(f"{self.base}/api/tournaments?type=SNG", timeout=self.timeout)
        assert r.status_code == 200
        data = r.json()
        assert all(t["type"] == "SNG" for t in data), "筛选 SNG 应只含 SNG"

    # 11. 不存在的赛事返回 404
    def test_not_found(self):
        r = requests.get(f"{self.base}/api/tournaments/999999", timeout=self.timeout)
        assert r.status_code == 404

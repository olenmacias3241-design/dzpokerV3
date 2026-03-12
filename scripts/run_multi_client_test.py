#!/usr/bin/env python3
# dzpokerV3/scripts/run_multi_client_test.py
# 多客户端 HTTP 测试：模拟 2 个客户端登录、建桌、入座、拉取状态。
# 需先启动服务端：python app.py（默认端口 8080）
# 用法：python scripts/run_multi_client_test.py [--base-url http://127.0.0.1:8080]

import os
import sys
import argparse
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    import requests
except ImportError:
    print("需要安装 requests: pip install requests")
    sys.exit(2)


def main():
    p = argparse.ArgumentParser(description="多客户端 HTTP 测试")
    p.add_argument("--base-url", default="http://127.0.0.1:8080", help="服务端根地址")
    p.add_argument("--timeout", type=float, default=10.0, help="请求超时秒数")
    args = p.parse_args()
    base = args.base_url.rstrip("/")

    errors = []
    print("多客户端测试: 2 个客户端登录 → 建桌 → 入座 → 拉取状态")
    print("base_url =", base)

    # 1) 两个客户端登录
    r1 = requests.post(f"{base}/api/login", json={"username": "MultiClientA"}, timeout=args.timeout)
    r2 = requests.post(f"{base}/api/login", json={"username": "MultiClientB"}, timeout=args.timeout)
    if r1.status_code != 200 or not r1.json().get("ok"):
        errors.append("ClientA 登录失败: " + str(r1.status_code) + " " + str(r1.text))
    if r2.status_code != 200 or not r2.json().get("ok"):
        errors.append("ClientB 登录失败: " + str(r2.status_code) + " " + str(r2.text))
    if errors:
        print("\n".join(errors))
        return 1

    token_a = r1.json()["token"]
    token_b = r2.json()["token"]
    print("  ClientA/B 登录成功")

    # 2) ClientA 建桌
    r = requests.post(
        f"{base}/api/lobby/tables",
        json={"tableName": "MultiClientTest", "sb": 5, "bb": 10, "maxPlayers": 6},
        timeout=args.timeout,
    )
    if r.status_code != 200:
        errors.append("建桌失败: " + str(r.status_code) + " " + r.text)
        print("\n".join(errors))
        return 1
    table_id = r.json()["tableId"]
    print("  建桌成功 table_id =", table_id)

    # 3) 两人入座
    r_a = requests.post(
        f"{base}/api/tables/{table_id}/sit",
        json={"token": token_a, "seat": 0},
        timeout=args.timeout,
    )
    r_b = requests.post(
        f"{base}/api/tables/{table_id}/sit",
        json={"token": token_b, "seat": 1},
        timeout=args.timeout,
    )
    if r_a.status_code != 200:
        errors.append("ClientA 入座失败: " + str(r_a.status_code) + " " + (r_a.json() or {}).get("error", r_a.text))
    if r_b.status_code != 200:
        errors.append("ClientB 入座失败: " + str(r_b.status_code) + " " + (r_b.json() or {}).get("error", r_b.text))
    if errors:
        print("\n".join(errors))
        return 1
    print("  ClientA 座位0、ClientB 座位1 入座成功")

    # 4) 等待机器人填满并开局（fill_table_with_bots delay=2.0）
    time.sleep(3.0)

    # 5) 两个客户端分别拉取牌桌状态
    r_state_a = requests.get(f"{base}/api/tables/{table_id}", params={"token": token_a}, timeout=args.timeout)
    r_state_b = requests.get(f"{base}/api/tables/{table_id}", params={"token": token_b}, timeout=args.timeout)

    if r_state_a.status_code != 200:
        errors.append("ClientA 拉取状态失败: " + str(r_state_a.status_code))
    if r_state_b.status_code != 200:
        errors.append("ClientB 拉取状态失败: " + str(r_state_b.status_code))
    if errors:
        print("\n".join(errors))
        return 1

    state_a = r_state_a.json()
    state_b = r_state_b.json()
    status = state_a.get("status") or state_b.get("status")
    print("  牌桌状态 status =", status)

    if status not in ("waiting", "playing"):
        errors.append("预期 status 为 waiting 或 playing，实际: " + str(status))
    if state_a.get("my_seat") != 0:
        errors.append("ClientA my_seat 应为 0，实际: " + str(state_a.get("my_seat")))
    if state_b.get("my_seat") != 1:
        errors.append("ClientB my_seat 应为 1，实际: " + str(state_b.get("my_seat")))

    if errors:
        print("断言失败:")
        print("\n".join(errors))
        return 1
    print("多客户端测试通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

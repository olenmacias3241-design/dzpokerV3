#!/usr/bin/env python3
# dzpokerV3/scripts/run_api_tests.py
# 运行后端 API 测试（入口脚本，实际用例在 tests/api/）
# 用法：python scripts/run_api_tests.py
# 或直接：pytest tests/api -v

import os
import sys
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main():
    base = os.environ.get("DZPOKER_API_BASE", "http://127.0.0.1:8080")
    print("后端 API 测试（需服务端已启动）")
    print("  DZPOKER_API_BASE =", base)
    print()
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/api",
            "-v",
            "--tb=short",
        ],
        cwd=ROOT,
        env={**os.environ, "DZPOKER_API_BASE": base.rstrip("/")},
    )
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())

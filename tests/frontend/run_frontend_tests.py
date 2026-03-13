#!/usr/bin/env python3
# 运行前端 E2E 测试（需先启动服务端并安装 playwright + chromium）
# 用法：python tests/frontend/run_frontend_tests.py

import os
import sys
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
os.chdir(ROOT)

def main():
    base = os.environ.get("DZPOKER_API_BASE", "http://127.0.0.1:8080")
    print("前端 E2E 测试（tests/frontend）")
    print("  DZPOKER_API_BASE =", base)
    print()
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/frontend", "-v", "--tb=short"],
        cwd=ROOT,
        env={**os.environ, "DZPOKER_API_BASE": base.rstrip("/")},
    )
    return r.returncode

if __name__ == "__main__":
    sys.exit(main())

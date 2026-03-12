#!/usr/bin/env python3
# dzpokerV3/scripts/run_batch_tests.py
# 批量运行单元测试，供 TASKS.md「运行批量/多客户端测试并记录」使用。
# 用法：在项目根目录执行 python scripts/run_batch_tests.py

import os
import sys
import subprocess
import unittest

# 确保从项目根运行
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def run_unittest_discover():
    """运行 tests/ 下所有 unittest 用例。"""
    r = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = (r.stdout or "") + (r.stderr or "")
    # 解析运行数、失败数（简化：看 returncode）
    ok = r.returncode == 0
    run = out.count(" ... ") + out.count(" ... ok") + out.count(" ... FAIL")
    if "Ran " in out:
        for line in out.splitlines():
            if line.strip().startswith("Ran "):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        run = int(parts[1])
                    except ValueError:
                        pass
                break
    failures = out.count("FAIL:")
    errors = out.count("ERROR:")
    return ok, run, failures + errors, out


def run_script(script_path):
    """执行单个测试脚本（如 test_pot_distribution.py），返回是否成功。"""
    try:
        r = subprocess.run(
            [sys.executable, script_path],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return r.returncode == 0, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"
    except Exception as e:
        return False, "", str(e)


def main():
    print("=" * 60)
    print("dzpokerV3 批量单元测试")
    print("=" * 60)

    all_ok = True
    summary = []

    # 1. tests/ 下 unittest
    print("\n[1/2] tests/ (unittest discover)")
    ok, run, fail_count, out = run_unittest_discover()
    if out:
        print(out[-2000:] if len(out) > 2000 else out)  # 打印最后 2000 字符
    all_ok = all_ok and ok
    summary.append(("tests/ (unittest)", ok, run, fail_count))

    # 2. 根目录独立测试脚本（若存在且可导入则运行）
    print("\n[2/2] 根目录独立测试脚本")
    for name in ["test_pot_distribution", "test_side_pots"]:
        path = os.path.join(ROOT, f"{name}.py")
        if not os.path.isfile(path):
            summary.append((name, None, 0, 0))  # skip
            continue
        ok, out, err = run_script(path)
        if err and not ok:
            print(f"  {name}: FAIL")
            if err.strip():
                print(err[:500])
        else:
            print(f"  {name}: OK" if ok else f"  {name}: FAIL")
        if ok is not None:
            all_ok = all_ok and ok
        summary.append((name, ok, 1, 0 if ok else 1))

    # 汇总
    print("\n" + "=" * 60)
    print("汇总")
    print("=" * 60)
    for item in summary:
        name, ok, run, fail = item
        if ok is None:
            print(f"  {name}: (未执行)")
        else:
            status = "通过" if ok else "失败"
            print(f"  {name}: {status} (运行 {run}, 失败 {fail})")
    print("\n整体: " + ("全部通过" if all_ok else "存在失败"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

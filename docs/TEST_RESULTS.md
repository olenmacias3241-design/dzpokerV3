# 批量与多客户端测试说明及结果

本文档记录「运行批量/多客户端测试并记录」任务的执行方式与简要结果。详见 TASKS.md 后端任务。

## 如何运行

### 1. 批量单元测试（无需启动服务）

在项目根目录执行：

```bash
python3 scripts/run_batch_tests.py
```

- 自动执行 `tests/` 下所有 `test_*.py`（unittest discover）。
- 自动执行根目录下的 `test_pot_distribution.py`、`test_side_pots.py`（若存在）。

### 2. 多客户端 HTTP 测试（需先启动服务端）

1. 启动服务：`python app.py`（默认端口 8080）。
2. 另开终端执行：

```bash
python3 scripts/run_multi_client_test.py
```

可选参数：`--base-url http://127.0.0.1:8080`、`--timeout 10`。

流程：2 个客户端登录 → 建桌 → 两人入座 → 等待机器人填满并开局 → 两个客户端分别拉取牌桌状态并校验。

## 最近一次运行结果（记录用）

| 项目 | 结果 | 说明 |
|------|------|------|
| tests/ (unittest) | 17 个用例，1 个失败 | 失败：`test_game_logic.test_end_of_preflop_round`（期望 Preflop 结束后进入 Flop，当前实现未在该用例中推进阶段） |
| test_pot_distribution.py | 失败 | 依赖已废弃的 `PotManager` 类，当前 `core.pot_manager` 仅提供 `calculate_side_pots` / `distribute_pots`，需后续对齐或移除该脚本 |
| test_side_pots.py | 通过 | 使用 `core.pot_manager.calculate_side_pots` 等现有接口 |
| 多客户端测试 | 通过 | 2 客户端登录→建桌→入座→拉取状态通过（需服务端已启动） |

## 相关文件

- 批量测试入口：`scripts/run_batch_tests.py`
- 多客户端测试：`scripts/run_multi_client_test.py`
- 单元测试目录：`tests/`

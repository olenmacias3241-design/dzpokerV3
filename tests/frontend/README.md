# 前端页面 E2E 测试

使用 Playwright 对大厅、登录、牌桌页进行浏览器端测试。

## 准备

1. 安装依赖：`pip install -r requirements.txt`
2. 安装浏览器：`playwright install chromium`
3. 启动服务端：`python app.py`（默认 8080）

## 运行

在项目根目录：

```bash
# 无头模式
pytest tests/frontend -v

# 有界面
pytest tests/frontend -v --headed

# 指定服务地址
DZPOKER_API_BASE=http://127.0.0.1:8080 pytest tests/frontend -v
```

## 用例说明

| 文件 | 用例 |
|------|------|
| test_lobby_page.py | 大厅页加载、牌桌列表区域、创建牌桌面板、筛选控件 |
| test_login_page.py | 登录页加载、表单输入、注册链接 |
| test_table_page.py | 无参数时提示、带 table+token 时游戏区/入座区、行动按钮存在 |

部分用例依赖服务端（创建桌、入座、获取 token），服务未启动时会 skip。

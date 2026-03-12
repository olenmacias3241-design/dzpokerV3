# 后端 API 接口测试

本目录包含对 dzpokerV3 后端 HTTP 接口的 pytest 用例与运行脚本。

## 目录结构

- `conftest.py` - pytest 配置与 fixture（base_url、guest_token、table_id 等）
- `test_api_backend.py` - 接口用例（登录、大厅、牌桌、对局、商城、俱乐部、回放等）
- `run_api_tests.py` - 一键运行脚本
- `README.md` - 本说明

## 运行前

1. 安装依赖：`pip install pytest requests`（或项目根目录 `pip install -r requirements.txt`）
2. 启动服务端：在项目根目录执行 `python app.py`（默认端口 8080）

## 运行方式

在**项目根目录**下任选其一：

```bash
# 方式一：使用本目录脚本
python tests/api/run_api_tests.py

# 方式二：直接 pytest
pytest tests/api -v

# 指定服务地址（例如端口 5002）
DZPOKER_API_BASE=http://127.0.0.1:5002 pytest tests/api -v
```

也可继续使用脚本入口（会调用 tests/api）：

```bash
python scripts/run_api_tests.py
```

## 环境变量

- `DZPOKER_API_BASE` - 服务端根地址，默认 `http://127.0.0.1:8080`

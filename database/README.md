# 数据库配置与初始化

## 1. 环境变量（推荐）

在项目根目录复制 `.env.example` 为 `.env`，并填写本地 MySQL 信息（例如 root / Tonny@100 / dzpoker）：

```bash
cp .env.example .env
# 编辑 .env，设置 MYSQL_PASSWORD=你的密码
```

`.env` 已被 `.gitignore` 忽略，不会提交到仓库。

## 2. 安装依赖

```bash
pip install -r requirements.txt
```

## 3. 初始化表结构

确保 MySQL 已启动，且账号密码正确，然后执行：

```bash
cd dzpokerV3
python -m database.connection
```

或：

```bash
python database/connection.py
```

会自动创建数据库（若不存在）并执行 `database/schema.sql` 建表。

## 4. 表结构概览

| 表名 | 说明 |
|------|------|
| `users` | 用户：用户名、密码哈希、金币、等级、经验、总局数/胜局/最大底池等 |
| `game_tables` | 牌桌：盲注、带入限制、人数、状态 |
| `table_seats` | 牌桌座位：谁坐在哪桌哪座、桌上筹码 |
| `game_hands` | 牌局记录：每手公共牌、底池、开始时间 |
| `hand_participants` | 参与记录：每手每人的手牌、是否弃牌、是否赢家、输赢金额 |

在代码中获取连接示例：

```python
from database import get_connection

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id, username, coins_balance FROM users LIMIT 10")
        for row in cur.fetchall():
            print(row)
```

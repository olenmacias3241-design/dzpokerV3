# dzpokerV3/config.py - 统一配置入口，从 .env 读取所有环境变量
import os
from dotenv import load_dotenv

load_dotenv()

# ---------- 应用 ----------
SECRET_KEY = os.environ.get("SECRET_KEY", "dzpoker-secret")
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

# ---------- 游戏配置 ----------
# 玩家行动时间（秒）
PLAYER_ACTION_TIMEOUT = int(os.environ.get("PLAYER_ACTION_TIMEOUT", 15))
# 最小行动时间（秒）
PLAYER_ACTION_TIMEOUT_MIN = int(os.environ.get("PLAYER_ACTION_TIMEOUT_MIN", 10))
# 最大行动时间（秒）
PLAYER_ACTION_TIMEOUT_MAX = int(os.environ.get("PLAYER_ACTION_TIMEOUT_MAX", 30))

# ---------- MySQL ----------
MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "dzpoker")
MYSQL_CHARSET = os.environ.get("MYSQL_CHARSET", "utf8mb4")

# SQLAlchemy 连接 URL（供 database/__init__.py 使用）
DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    f"?charset={MYSQL_CHARSET}"
)


def get_mysql_connect_kwargs() -> dict:
    """返回 PyMySQL connect() 所需参数（供 database/connection.py 使用）。"""
    return {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "database": MYSQL_DATABASE,
        "charset": MYSQL_CHARSET,
    }

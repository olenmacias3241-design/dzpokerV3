# dzpokerV3/database/connection.py
# 使用 config 中的 MySQL 配置获取连接，或执行 schema 初始化

import os
import sys

# 保证项目根在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _get_config():
    from config import get_mysql_connect_kwargs
    return get_mysql_connect_kwargs()

def get_connection():
    """返回一个 PyMySQL 连接（调用方负责 close）。若未安装 PyMySQL 会抛出 ImportError。"""
    import pymysql
    kwargs = _get_config()
    return pymysql.connect(**kwargs)

def init_db(drop_first=False):
    """
    创建数据库（若不存在）并执行 schema.sql 建表。
    drop_first: 是否先删除已存在的表（按 schema 中的顺序）。
    """
    from config import MYSQL_DATABASE
    import pymysql

    kwargs = _get_config()
    # 先连到无 database 的 server，创建库
    conn = pymysql.connect(
        host=kwargs["host"],
        port=kwargs["port"],
        user=kwargs["user"],
        password=kwargs["password"],
        charset=kwargs["charset"],
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
    finally:
        conn.close()

    # 再连到具体库执行 schema
    conn = pymysql.connect(**kwargs)
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    if not os.path.isfile(schema_path):
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    try:
        with conn.cursor() as cur:
            cur.execute("SET FOREIGN_KEY_CHECKS = 0")
            cur.execute(
                "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s",
                (MYSQL_DATABASE,),
            )
            for (tname,) in cur.fetchall():
                cur.execute(f"DROP TABLE IF EXISTS `{tname}`")
            conn.commit()
            cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
    finally:
        conn.close()

    conn = pymysql.connect(**kwargs)
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # 按语句执行：仅执行 CREATE TABLE（表已在上面全部删除）
    statements = [
        s.strip() for s in sql.split(";")
        if s.strip() and not s.strip().startswith("--")
    ]
    try:
        with conn.cursor() as cur:
            for stmt in statements:
                if stmt.upper().startswith("CREATE TABLE"):
                    cur.execute(stmt)
        conn.commit()
    finally:
        conn.close()

    conn = pymysql.connect(**kwargs)
    try:
        with conn.cursor() as cur:
            cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db(drop_first=False)
    print("Database and tables initialized.")

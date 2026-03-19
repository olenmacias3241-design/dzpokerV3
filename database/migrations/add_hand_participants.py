"""数据库迁移：创建 hand_participants 表（一手牌参与者与输赢）"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pymysql
from config import get_mysql_connect_kwargs


def upgrade():
    """创建 hand_participants 表"""
    conn = pymysql.connect(**get_mysql_connect_kwargs())
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hand_participants (
                hand_id INT UNSIGNED NOT NULL,
                user_id INT UNSIGNED NOT NULL,
                seat_number INT NOT NULL,
                hole_cards VARCHAR(32) NOT NULL DEFAULT '',
                win_amount BIGINT NOT NULL DEFAULT 0,
                PRIMARY KEY (hand_id, user_id),
                FOREIGN KEY (hand_id) REFERENCES hands(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        print("✅ hand_participants 表创建成功")
    except Exception as e:
        conn.rollback()
        print(f"❌ 创建表失败: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def downgrade():
    conn = pymysql.connect(**get_mysql_connect_kwargs())
    cursor = conn.cursor()
    try:
        cursor.execute("DROP TABLE IF EXISTS hand_participants")
        conn.commit()
        print("✅ hand_participants 表删除成功")
    except Exception as e:
        conn.rollback()
        print(f"❌ 删除表失败: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "down":
        downgrade()
    else:
        upgrade()

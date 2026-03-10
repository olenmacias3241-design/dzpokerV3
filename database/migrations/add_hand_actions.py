"""数据库迁移：创建 hand_actions 表"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pymysql
from config import get_mysql_connect_kwargs

def upgrade():
    """创建 hand_actions 表"""
    conn = pymysql.connect(**get_mysql_connect_kwargs())
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hand_actions (
                id INT PRIMARY KEY AUTO_INCREMENT,
                hand_id INT NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                action_type VARCHAR(20) NOT NULL,
                amount BIGINT,
                stage VARCHAR(20) NOT NULL,
                action_order INT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hand_id) REFERENCES game_hands(id),
                INDEX idx_hand_id (hand_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        conn.commit()
        print("✅ hand_actions 表创建成功")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 创建表失败: {e}")
        raise
    
    finally:
        cursor.close()
        conn.close()

def downgrade():
    """删除 hand_actions 表"""
    conn = pymysql.connect(**get_mysql_connect_kwargs())
    cursor = conn.cursor()
    
    try:
        cursor.execute("DROP TABLE IF EXISTS hand_actions")
        conn.commit()
        print("✅ hand_actions 表删除成功")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 删除表失败: {e}")
        raise
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "down":
        downgrade()
    else:
        upgrade()

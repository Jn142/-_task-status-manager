# db_upgrade.py
import sqlite3
import os


def upgrade_database(db_path="task_manager.db"):
    """升级数据库结构，添加新模式相关字段"""
    if not os.path.exists(db_path):
        print(f"数据库文件 {db_path} 不存在")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 检查是否已存在新字段
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]

        # 添加缺失的字段
        if 'link_mode' not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN link_mode INTEGER DEFAULT 0")
            print("✓ 已添加 link_mode 字段")

        if 'link_url' not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN link_url TEXT")
            print("✓ 已添加 link_url 字段")

        conn.commit()
        print("✓ 数据库升级完成！")
        return True

    except Exception as e:
        print(f"✗ 数据库升级失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    upgrade_database()
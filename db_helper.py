import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional


class DBHelper:
    def __init__(self, db_name: str = "task_manager.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_tables()
        self._init_default_properties()  # 初始化默认属性

    def _create_tables(self) -> None:
        # 1. 新增：任务属性表（存储系统预设属性）
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_property (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,  -- 属性名（唯一，避免重复）
                is_default BOOLEAN DEFAULT 0,  -- 是否系统默认属性（1=是，0=自定义）
                create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. 任务项表（新增 property_id 关联属性和模式相关字段）
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                board_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                name TEXT NOT NULL,
                create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL CHECK(status IN ('待启用', '初开启', '已完成')),
                status_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expected_time DATE,
                task_dir TEXT,
                property_id INTEGER NOT NULL DEFAULT 3,  -- 关联属性（默认3=未知）
                link_mode INTEGER DEFAULT 0,             -- 0:目录模式, 1:链接模式
                link_url TEXT,                           -- 链接地址
                FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
                FOREIGN KEY (property_id) REFERENCES task_property(id) ON DELETE SET DEFAULT  -- 删除属性时改默认
            )
        ''')

        # 3. 任务板块表（不变）
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def _init_default_properties(self) -> None:
        """初始化默认属性：编程项目（1）、应用（2）、未知（3）"""
        self.cursor.execute("SELECT COUNT(*) FROM task_property")
        if self.cursor.fetchone()[0] == 0:  # 表为空时初始化
            default_props = [
                ("编程项目", 1),
                ("应用", 1),
                ("未知", 1)  # 未知为默认兜底属性，不可删除
            ]
            self.cursor.executemany('''
                INSERT INTO task_property (name, is_default) VALUES (?, ?)
            ''', default_props)
            self.conn.commit()

    # ------------------------------
    # 新增：任务模式相关方法
    # ------------------------------
    def update_task_link_mode(self, task_id: int, link_mode: int) -> None:
        """更新任务模式"""
        self.cursor.execute('''
            UPDATE tasks SET link_mode = ? WHERE id = ?
        ''', (link_mode, task_id))
        self.conn.commit()

    def update_task_link_url(self, task_id: int, link_url: str) -> None:
        """更新任务链接"""
        self.cursor.execute('''
            UPDATE tasks SET link_url = ? WHERE id = ?
        ''', (link_url, task_id))
        self.conn.commit()

    def get_task_link_url(self, task_id: int) -> Optional[str]:
        """获取任务链接"""
        self.cursor.execute("SELECT link_url FROM tasks WHERE id = ?", (task_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_tasks_by_link_mode(self, link_mode: int) -> List[Tuple]:
        """按模式查询任务"""
        self.cursor.execute('''
            SELECT t.id, t.name, b.name as board_name, t.year, t.month, t.status, 
                   t.status_time, t.expected_time, t.board_id, t.task_dir, t.property_id,
                   p.name as property_name, t.link_mode, t.link_url
            FROM tasks t
            JOIN boards b ON t.board_id = b.id
            JOIN task_property p ON t.property_id = p.id
            WHERE t.link_mode = ?
            ORDER BY t.status_time DESC
        ''', (link_mode,))
        return self.cursor.fetchall()

    # ------------------------------
    # 新增：任务属性相关方法
    # ------------------------------
    def add_custom_property(self, prop_name: str) -> bool:
        """新增自定义属性（返回True=成功，False=已存在）"""
        try:
            self.cursor.execute('''
                INSERT INTO task_property (name, is_default) VALUES (?, 0)
            ''', (prop_name.strip(),))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # 属性名已存在

    def delete_property(self, prop_id: int) -> Tuple[int, bool]:
        """删除属性（仅允许删除自定义属性）
        返回：(受影响的任务数量, 是否删除成功)
        """
        # 1. 检查是否为默认属性（不可删除）
        self.cursor.execute("SELECT is_default FROM task_property WHERE id = ?", (prop_id,))
        is_default = self.cursor.fetchone()[0]
        if is_default == 1:
            return (0, False)  # 默认属性，删除失败

        # 2. 统计关联该属性的任务数量
        self.cursor.execute("SELECT COUNT(*) FROM tasks WHERE property_id = ?", (prop_id,))
        task_count = self.cursor.fetchone()[0]

        # 3. 删除属性（触发外键ON DELETE SET DEFAULT，任务property_id改为3=未知）
        self.cursor.execute("DELETE FROM task_property WHERE id = ?", (prop_id,))
        self.conn.commit()
        return (task_count, True)

    def get_all_properties(self) -> List[Tuple[int, str, int]]:
        """获取所有预设属性：(id, name, is_default)"""
        self.cursor.execute("SELECT id, name, is_default FROM task_property ORDER BY is_default DESC, name ASC")
        return self.cursor.fetchall()

    def get_property_name_by_id(self, prop_id: int) -> str:
        """通过属性ID获取属性名"""
        self.cursor.execute("SELECT name FROM task_property WHERE id = ?", (prop_id,))
        result = self.cursor.fetchone()
        return result[0] if result else "未知"

    # ------------------------------
    # 任务操作（新增property_id参数和模式参数）
    # ------------------------------
    def add_task(self,
                 board_id: int,
                 name: str,
                 status: str,
                 property_id: int = 3,  # 新增：任务属性ID（默认3=未知）
                 expected_time: Optional[str] = None,
                 task_dir: Optional[str] = None,
                 link_mode: int = 0,    # 新增：任务模式（默认0=目录模式）
                 link_url: Optional[str] = None,  # 新增：链接地址
                 year: Optional[int] = None,
                 month: Optional[int] = None) -> None:
        now = datetime.now()
        year = year or now.year
        month = month or now.month
        self.cursor.execute('''
            INSERT INTO tasks 
            (board_id, year, month, name, status, status_time, expected_time, task_dir, property_id, link_mode, link_url)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
        ''', (board_id, year, month, name, status, expected_time, task_dir, property_id, link_mode, link_url))
        self.conn.commit()

    def update_task_property(self, task_id: int, new_prop_id: int) -> None:
        """修改任务属性"""
        self.cursor.execute('''
            UPDATE tasks SET property_id = ? WHERE id = ?
        ''', (new_prop_id, task_id))
        self.conn.commit()

    # ------------------------------
    # 新增：属性查询相关方法
    # ------------------------------
    def get_tasks_by_property(self, prop_id: int) -> List[Tuple]:
        """查询所有具有某一属性的任务"""
        self.cursor.execute('''
            SELECT t.id, t.name, b.name as board_name, t.year, t.month, t.status, 
                   t.status_time, t.expected_time, t.board_id, t.task_dir, t.property_id,
                   p.name as property_name, t.link_mode, t.link_url
            FROM tasks t
            JOIN boards b ON t.board_id = b.id
            JOIN task_property p ON t.property_id = p.id
            WHERE t.property_id = ?
            ORDER BY t.status_time DESC
        ''', (prop_id,))
        return self.cursor.fetchall()

    def get_tasks_by_date_and_property(self, year: int, month: int, prop_id: int) -> List[Tuple]:
        """查询指定日期（年/月）+ 属性的任务"""
        self.cursor.execute('''
            SELECT t.id, t.name, b.name as board_name, t.year, t.month, t.status, 
                   t.status_time, t.expected_time, t.board_id, t.task_dir, t.property_id,
                   p.name as property_name, t.link_mode, t.link_url
            FROM tasks t
            JOIN boards b ON t.board_id = b.id
            JOIN task_property p ON t.property_id = p.id
            WHERE t.year = ? AND t.month = ? AND t.property_id = ?
            ORDER BY t.status_time DESC
        ''', (year, month, prop_id))
        return self.cursor.fetchall()

    # ------------------------------
    # 原有方法（不变，仅适配新字段）
    # ------------------------------
    def add_board(self, name: str) -> bool:
        try:
            self.cursor.execute("INSERT INTO boards (name) VALUES (?)", (name,))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_all_boards(self) -> List[Tuple[int, str]]:
        self.cursor.execute("SELECT id, name FROM boards ORDER BY create_time DESC")
        return self.cursor.fetchall()

    def delete_board(self, board_id: int) -> None:
        self.cursor.execute("DELETE FROM boards WHERE id = ?", (board_id,))
        self.conn.commit()

    def update_board_name(self, board_id: int, new_name: str) -> bool:
        try:
            self.cursor.execute("SELECT id FROM boards WHERE name = ?", (new_name,))
            if self.cursor.fetchone():
                return False
            self.cursor.execute("UPDATE boards SET name = ? WHERE id = ?", (new_name, board_id))
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False

    def update_task_name(self, task_id: int, new_name: str) -> None:
        self.cursor.execute("UPDATE tasks SET name = ? WHERE id = ?", (new_name, task_id))
        self.conn.commit()

    def update_task_dir(self, task_id: int, new_dir: str) -> None:
        self.cursor.execute('''
            UPDATE tasks 
            SET task_dir = ? 
            WHERE id = ?
        ''', (new_dir, task_id))
        self.conn.commit()

    def get_tasks_by_board(self, board_id: int) -> List[Tuple]:
        self.cursor.execute('''
            SELECT t.id, t.year, t.month, t.name, t.status, t.status_time, t.expected_time, 
                   t.task_dir, t.property_id, p.name as property_name, t.link_mode, t.link_url
            FROM tasks t
            JOIN task_property p ON t.property_id = p.id
            WHERE t.board_id = ? 
            ORDER BY t.year DESC, month DESC, status_time DESC
        ''', (board_id,))
        return self.cursor.fetchall()

    def get_tasks_by_time_status(self,
                                 year: Optional[int] = None,
                                 month: Optional[int] = None,
                                 status: Optional[str] = None) -> List[Tuple]:
        query = '''
            SELECT t.id, t.name, b.name as board_name, t.year, t.month, t.status, 
                   t.status_time, t.expected_time, t.board_id, t.task_dir, t.property_id,
                   p.name as property_name, t.link_mode, t.link_url
            FROM tasks t
            JOIN boards b ON t.board_id = b.id
            JOIN task_property p ON t.property_id = p.id
            WHERE 1=1
        '''
        params = []
        if year:
            query += " AND t.year = ?"
            params.append(year)
        if month:
            query += " AND t.month = ?"
            params.append(month)
        if status:
            query += " AND t.status = ?"
            params.append(status)
        query += " ORDER BY t.status_time DESC"

        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_all_tasks_order_by_name(self) -> List[Tuple]:
        self.cursor.execute('''
            SELECT t.id, t.name, b.name as board_name, t.year, t.month, t.status, 
                   t.status_time, t.expected_time, t.board_id, t.task_dir, t.property_id,
                   p.name as property_name, t.link_mode, t.link_url
            FROM tasks t
            JOIN boards b ON t.board_id = b.id
            JOIN task_property p ON t.property_id = p.id
            ORDER BY t.name ASC
        ''')
        return self.cursor.fetchall()

    def search_tasks_by_name(self, task_name: str) -> List[Tuple]:
        self.cursor.execute('''
            SELECT t.id, t.name, b.name as board_name, t.year, t.month, t.status, 
                   t.status_time, t.expected_time, t.board_id, t.task_dir, t.property_id,
                   p.name as property_name, t.link_mode, t.link_url
            FROM tasks t
            JOIN boards b ON t.board_id = b.id
            JOIN task_property p ON t.property_id = p.id
            WHERE t.name LIKE ?
            ORDER BY t.name ASC
        ''', (f'%{task_name}%',))
        return self.cursor.fetchall()

    def update_task_status(self, task_id: int, new_status: str) -> None:
        self.cursor.execute('''
            UPDATE tasks 
            SET status = ?, status_time = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (new_status, task_id))
        self.conn.commit()

    def delete_task(self, task_id: int) -> None:
        self.cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
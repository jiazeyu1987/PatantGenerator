"""
对话数据库管理器
用于存储和查询结构化的专利生成对话数据
"""

import sqlite3
import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class TaskInfo:
    """任务信息数据类"""
    id: str
    title: str
    context: str
    iterations: int
    created_at: str
    status: str = "running"


@dataclass
class ConversationRound:
    """对话轮次数据类"""
    id: int
    task_id: str
    round_number: int
    role: str  # 'writer', 'modifier', or 'reviewer'
    prompt: str
    response: str
    timestamp: str


class ConversationDB:
    """对话数据库管理器"""

    def __init__(self, db_path: str = None):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径，默认为backend/conversations.db
        """
        if db_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(current_dir, "conversations.db")

        self.db_path = db_path
        self._init_database()
        logger.info(f"对话数据库初始化完成: {db_path}")

    def _init_database(self):
        """初始化数据库表结构"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 创建任务表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        context TEXT,
                        iterations INTEGER,
                        created_at TEXT,
                        updated_at TEXT,
                        status TEXT DEFAULT 'running',
                        base_name TEXT
                    )
                ''')

                # 创建对话轮次表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversation_rounds (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT,
                        round_number INTEGER,
                        role TEXT,
                        prompt TEXT,
                        response TEXT,
                        timestamp TEXT,
                        FOREIGN KEY (task_id) REFERENCES tasks(id)
                    )
                ''')

                # 创建索引提高查询性能
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_rounds_task_id
                    ON conversation_rounds(task_id)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_rounds_task_round_role
                    ON conversation_rounds(task_id, round_number, role)
                ''')

                conn.commit()
                logger.info("数据库表结构创建成功")

        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

    def create_task(self, title: str, context: str, iterations: int, base_name: str = None) -> str:
        """
        创建新任务

        Args:
            title: 任务标题
            context: 技术背景上下文
            iterations: 迭代次数
            base_name: 输出文件名前缀

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO tasks (id, title, context, iterations, created_at, updated_at, base_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (task_id, title, context, iterations, now, now, base_name or ""))

                conn.commit()
                logger.info(f"创建任务成功: {task_id}")
                return task_id

        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            raise

    def add_conversation_round(
        self,
        task_id: str,
        round_number: int,
        role: str,
        prompt: str,
        response: str
    ) -> int:
        """
        添加对话轮次

        Args:
            task_id: 任务ID
            round_number: 轮次编号
            role: 角色 ('writer', 'modifier', or 'reviewer')
            prompt: 提示词
            response: LLM响应

        Returns:
            记录ID
        """
        timestamp = datetime.now().isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO conversation_rounds
                    (task_id, round_number, role, prompt, response, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (task_id, round_number, role, prompt, response, timestamp))

                record_id = cursor.lastrowid

                # 更新任务的最后修改时间
                cursor.execute('''
                    UPDATE tasks SET updated_at = ? WHERE id = ?
                ''', (timestamp, task_id))

                conn.commit()
                logger.info(f"添加对话轮次成功: task_id={task_id}, round={round_number}, role={role}")
                return record_id

        except Exception as e:
            logger.error(f"添加对话轮次失败: {e}")
            raise

    def get_all_tasks(self) -> List[TaskInfo]:
        """
        获取所有任务列表

        Returns:
            任务信息列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT id, title, context, iterations, created_at, status, base_name
                    FROM tasks
                    ORDER BY created_at DESC
                ''')

                tasks = []
                for row in cursor.fetchall():
                    task = TaskInfo(
                        id=row['id'],
                        title=row['title'],
                        context=row['context'],
                        iterations=row['iterations'],
                        created_at=row['created_at'],
                        status=row['status']
                    )
                    tasks.append(task)

                return tasks

        except Exception as e:
            logger.error(f"获取任务列表失败: {e}")
            return []

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """
        获取指定任务信息

        Args:
            task_id: 任务ID

        Returns:
            任务信息或None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT id, title, context, iterations, created_at, status, base_name
                    FROM tasks
                    WHERE id = ?
                ''', (task_id,))

                row = cursor.fetchone()
                if row:
                    return TaskInfo(
                        id=row['id'],
                        title=row['title'],
                        context=row['context'],
                        iterations=row['iterations'],
                        created_at=row['created_at'],
                        status=row['status']
                    )

                return None

        except Exception as e:
            logger.error(f"获取任务信息失败: {e}")
            return None

    def get_task_rounds(self, task_id: str) -> List[int]:
        """
        获取任务的所有轮次编号

        Args:
            task_id: 任务ID

        Returns:
            轮次编号列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT DISTINCT round_number
                    FROM conversation_rounds
                    WHERE task_id = ?
                    ORDER BY round_number
                ''', (task_id,))

                rounds = [row[0] for row in cursor.fetchall()]
                return rounds

        except Exception as e:
            logger.error(f"获取任务轮次失败: {e}")
            return []

    def get_conversation_round(
        self,
        task_id: str,
        round_number: int,
        role: str
    ) -> Optional[ConversationRound]:
        """
        获取指定的对话轮次

        Args:
            task_id: 任务ID
            round_number: 轮次编号
            role: 角色

        Returns:
            对话轮次信息或None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT id, task_id, round_number, role, prompt, response, timestamp
                    FROM conversation_rounds
                    WHERE task_id = ? AND round_number = ? AND role = ?
                ''', (task_id, round_number, role))

                row = cursor.fetchone()
                if row:
                    return ConversationRound(
                        id=row['id'],
                        task_id=row['task_id'],
                        round_number=row['round_number'],
                        role=row['role'],
                        prompt=row['prompt'],
                        response=row['response'],
                        timestamp=row['timestamp']
                    )

                return None

        except Exception as e:
            logger.error(f"获取对话轮次失败: {e}")
            return None

    def get_task_conversations(self, task_id: str) -> List[ConversationRound]:
        """
        获取任务的所有对话

        Args:
            task_id: 任务ID

        Returns:
            对话轮次列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT id, task_id, round_number, role, prompt, response, timestamp
                    FROM conversation_rounds
                    WHERE task_id = ?
                    ORDER BY round_number, role
                ''', (task_id,))

                conversations = []
                for row in cursor.fetchall():
                    conversation = ConversationRound(
                        id=row['id'],
                        task_id=row['task_id'],
                        round_number=row['round_number'],
                        role=row['role'],
                        prompt=row['prompt'],
                        response=row['response'],
                        timestamp=row['timestamp']
                    )
                    conversations.append(conversation)

                return conversations

        except Exception as e:
            logger.error(f"获取任务对话失败: {e}")
            return []

    def update_task_status(self, task_id: str, status: str):
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态 ('running', 'completed', 'failed')
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE tasks
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                ''', (status, datetime.now().isoformat(), task_id))

                conn.commit()
                logger.info(f"更新任务状态成功: {task_id} -> {status}")

        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        # SQLite不需要显式关闭连接
        pass


# 全局数据库实例
_conversation_db = None

def get_conversation_db() -> ConversationDB:
    """获取对话数据库实例（单例模式）"""
    global _conversation_db
    if _conversation_db is None:
        _conversation_db = ConversationDB()
    return _conversation_db
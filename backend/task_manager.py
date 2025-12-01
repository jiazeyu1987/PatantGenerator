import asyncio
import uuid
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from enum import Enum
import logging
import json
import os


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    """任务数据类"""

    def __init__(self, task_id: str, func: Callable, *args, **kwargs):
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.status = TaskStatus.PENDING
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.progress = 0  # 进度百分比 0-100
        self.message = "任务等待中..."

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "taskId": self.task_id,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "createdAt": self.created_at.isoformat(),
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result if self.status == TaskStatus.COMPLETED else None,
            "error": self.error if self.status == TaskStatus.FAILED else None,
        }


class TaskManager:
    """异步任务管理器"""

    def __init__(self, max_workers: int = 3, cleanup_interval: int = 3600):
        self.max_workers = max_workers
        self.cleanup_interval = cleanup_interval
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Dict[str, threading.Thread] = {}
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self._running = False
        self.logger = logging.getLogger(__name__)

    def start(self) -> None:
        """启动任务管理器"""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
            self._cleanup_thread.start()
            self.logger.info("任务管理器已启动")

    def stop(self) -> None:
        """停止任务管理器"""
        with self._lock:
            if not self._running:
                return

            self._running = False

            # 取消所有运行中的任务
            for task_id in list(self.running_tasks.keys()):
                self.cancel_task(task_id)

            # 等待清理线程结束
            if self._cleanup_thread:
                self._cleanup_thread.join(timeout=5)

            self.logger.info("任务管理器已停止")

    def submit_task(self, func: Callable, *args, **kwargs) -> str:
        """
        提交新任务

        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        task = Task(task_id, func, *args, **kwargs)

        with self._lock:
            self.tasks[task_id] = task

            # 如果有空闲的工作线程，立即启动任务
            if len(self.running_tasks) < self.max_workers:
                self._start_task(task)
            else:
                self.logger.info(f"任务 {task_id} 已加入队列，当前运行任务数: {len(self.running_tasks)}")

        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态字典，如果任务不存在则返回None
        """
        with self._lock:
            task = self.tasks.get(task_id)
            return task.to_dict() if task else None

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return False

            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                task.message = "任务已取消"
                task.completed_at = datetime.now()
                return True
            elif task.status == TaskStatus.RUNNING:
                # 注意：这里只是标记为取消，实际的线程可能无法立即停止
                task.status = TaskStatus.CANCELLED
                task.message = "任务取消中..."
                return True

            return False

    def _start_task(self, task: Task) -> None:
        """启动任务执行"""
        def task_wrapper():
            try:
                # 更新任务状态
                with self._lock:
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now()
                    task.message = "任务执行中..."
                    task.progress = 10

                # 执行任务函数
                self.logger.info(f"开始执行任务 {task.task_id}")

                # 创建带进度回调的kwargs
                task_kwargs = dict(task.kwargs)
                progress_callback = lambda progress, message: self._update_task_progress(task.task_id, progress, message)
                task_kwargs['progress_callback'] = progress_callback

                result = task.func(*task.args, **task_kwargs)

                # 任务完成
                with self._lock:
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                    task.completed_at = datetime.now()
                    task.progress = 100
                    task.message = "任务完成"

                self.logger.info(f"任务 {task.task_id} 执行成功")

            except Exception as e:
                # 任务失败
                with self._lock:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    task.completed_at = datetime.now()
                    task.message = f"任务失败: {str(e)}"

                self.logger.error(f"任务 {task.task_id} 执行失败: {str(e)}", exc_info=True)

            finally:
                # 从运行任务列表中移除
                with self._lock:
                    self.running_tasks.pop(task.task_id, None)

                    # 检查是否有待执行的任务
                    self._process_pending_tasks()

        # 启动线程
        thread = threading.Thread(target=task_wrapper, daemon=True)
        with self._lock:
            self.running_tasks[task.task_id] = thread

        thread.start()

    def _update_task_progress(self, task_id: str, progress: int, message: str) -> None:
        """更新任务进度"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task and task.status == TaskStatus.RUNNING:
                task.progress = max(0, min(100, progress))
                task.message = message

    def _process_pending_tasks(self) -> None:
        """处理待执行的任务"""
        # 找到最早创建的待执行任务
        pending_tasks = [
            task for task in self.tasks.values()
            if task.status == TaskStatus.PENDING
        ]

        pending_tasks.sort(key=lambda t: t.created_at)

        # 启动可以执行的任务
        while (len(self.running_tasks) < self.max_workers and
               pending_tasks and
               self._running):

            task = pending_tasks.pop(0)
            self._start_task(task)

    def _cleanup_worker(self) -> None:
        """清理过期任务的 worker 线程"""
        while self._running:
            try:
                current_time = datetime.now()
                expired_threshold = current_time - timedelta(hours=24)  # 24小时过期

                with self._lock:
                    expired_tasks = [
                        task_id for task_id, task in self.tasks.items()
                        if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                            task.completed_at and task.completed_at < expired_threshold)
                    ]

                    for task_id in expired_tasks:
                        self.tasks.pop(task_id, None)
                        self.logger.debug(f"清理过期任务: {task_id}")

                # 等待下次清理
                time.sleep(self.cleanup_interval)

            except Exception as e:
                self.logger.error(f"任务清理失败: {str(e)}", exc_info=True)
                time.sleep(60)  # 出错时等待1分钟再重试

    def get_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        with self._lock:
            stats = {
                "total_tasks": len(self.tasks),
                "running_tasks": len(self.running_tasks),
                "max_workers": self.max_workers,
                "status_counts": {}
            }

            for status in TaskStatus:
                count = sum(1 for task in self.tasks.values() if task.status == status)
                stats["status_counts"][status.value] = count

            return stats


# 全局任务管理器实例
task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """获取全局任务管理器实例"""
    return task_manager
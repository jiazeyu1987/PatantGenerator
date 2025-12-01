"""
聊天日志记录器

用于记录所有 LLM 的提示词和回复到带时间戳的日志文件中。
支持按时间分割日志文件，便于管理和查询。
"""

import os
import json
import time
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from config import get_config


class ChatLogger:
    """LLM 聊天日志记录器"""

    def __init__(self):
        self.config = get_config()
        self._lock = threading.Lock()
        self._current_date = None
        self._current_log_file = None
        self._ensure_chat_log_dir()

    def _ensure_chat_log_dir(self):
        """确保聊天日志目录存在"""
        try:
            self.config.ensure_chat_log_dir()
        except Exception as e:
            # 如果目录创建失败，禁用聊天日志
            print(f"警告: 无法创建聊天日志目录，聊天日志功能已禁用: {e}")
            self.config.logging.chat_log_enabled = False

    def _get_current_log_file(self) -> Optional[str]:
        """获取当前日期对应的日志文件路径"""
        if not self.config.logging.chat_log_enabled:
            return None

        current_date = datetime.now().strftime("%Y-%m-%d")

        # 如果日期变化或首次初始化，更新日志文件
        if self._current_date != current_date or self._current_log_file is None:
            with self._lock:
                self._current_date = current_date
                timestamp = datetime.now().strftime("%Y%m%d")
                log_filename = f"chat_prompt_{timestamp}.log"
                self._current_log_file = os.path.join(
                    self.config.logging.chat_log_dir,
                    log_filename
                )

        return self._current_log_file

    def _cleanup_old_logs(self):
        """清理旧的聊天日志文件"""
        if not self.config.logging.chat_log_enabled:
            return

        try:
            chat_log_dir = Path(self.config.logging.chat_log_dir)
            if not chat_log_dir.exists():
                return

            # 获取所有聊天日志文件
            log_files = list(chat_log_dir.glob("chat_prompt_*.log"))

            # 按修改时间排序
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # 保留最新的 N 个文件，删除其余的
            max_files = self.config.logging.chat_log_max_files
            if len(log_files) > max_files:
                for old_file in log_files[max_files:]:
                    try:
                        old_file.unlink()
                        print(f"已删除旧聊天日志: {old_file}")
                    except Exception as e:
                        print(f"删除旧聊天日志失败 {old_file}: {e}")

        except Exception as e:
            print(f"清理旧聊天日志时出错: {e}")

    def _format_timestamp(self) -> str:
        """格式化时间戳"""
        return datetime.now().strftime(self.config.logging.chat_log_format)

    def _sanitize_text(self, text: str, max_length: int = 10000) -> str:
        """清理文本，移除敏感信息并限制长度"""
        if not isinstance(text, str):
            text = str(text)

        # 移除可能的敏感信息模式
        sensitive_patterns = [
            'api_key', 'apikey', 'api-key',
            'secret', 'token', 'password',
            'authorization', 'auth'
        ]

        lower_text = text.lower()
        for pattern in sensitive_patterns:
            if pattern in lower_text:
                # 简单的敏感信息屏蔽
                text = self._mask_sensitive_info(text, pattern)

        # 限制长度
        if len(text) > max_length:
            text = text[:max_length] + "...(truncated)"

        return text

    def _mask_sensitive_info(self, text: str, pattern: str) -> str:
        """屏蔽敏感信息"""
        import re

        # 简单的正则表达式来屏蔽敏感信息
        pattern_re = re.compile(
            r'(' + re.escape(pattern) + r'[\s]*[:=]?[\s]*["\']?)([^\s"\'\n}]+)',
            re.IGNORECASE
        )
        return pattern_re.sub(r'\1***MASKED***', text)

    def log_interaction(self,
                       prompt: str,
                       response: str,
                       metadata: Optional[Dict[str, Any]] = None,
                       mode: str = "unknown") -> bool:
        """
        记录 LLM 交互日志

        Args:
            prompt: 发送给 LLM 的提示词
            response: LLM 的回复
            metadata: 额外的元数据信息
            mode: 调用模式 (sdk/cli)

        Returns:
            bool: 是否成功记录
        """
        if not self.config.logging.chat_log_enabled:
            return True  # 如果禁用了，返回成功但不记录

        try:
            log_file = self._get_current_log_file()
            if not log_file:
                return False

            # 准备日志数据
            timestamp = self._format_timestamp()
            log_entry = {
                "timestamp": timestamp,
                "mode": mode,
                "prompt": self._sanitize_text(prompt),
                "response": self._sanitize_text(response),
                "prompt_length": len(prompt),
                "response_length": len(response),
            }

            # 添加元数据
            if metadata:
                # 清理元数据中的敏感信息
                cleaned_metadata = {}
                for key, value in metadata.items():
                    if any(sensitive in key.lower() for sensitive in ['key', 'secret', 'token', 'password']):
                        cleaned_metadata[key] = "***MASKED***"
                    else:
                        cleaned_metadata[key] = value
                log_entry["metadata"] = cleaned_metadata

            # 添加文件信息
            log_entry["log_file"] = os.path.basename(log_file)

            # 写入日志文件
            with self._lock:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write("=" * 80 + "\n")
                    f.write(f"时间戳: {timestamp}\n")
                    f.write(f"模式: {mode.upper()}\n")
                    f.write(f"提示词长度: {log_entry['prompt_length']} 字符\n")
                    f.write(f"回复长度: {log_entry['response_length']} 字符\n")

                    if metadata:
                        f.write(f"元数据: {json.dumps(cleaned_metadata, ensure_ascii=False, indent=2)}\n")

                    f.write("\n--- 提示词 ---\n")
                    f.write(log_entry["prompt"])
                    f.write("\n\n--- 回复 ---\n")
                    f.write(log_entry["response"])
                    f.write("\n\n")

                # 检查并清理旧日志
                self._cleanup_old_logs()

            return True

        except Exception as e:
            print(f"记录聊天日志时出错: {e}")
            return False

    def log_sdk_interaction(self,
                           prompt: str,
                           response: str,
                           model: str = None,
                           api_success: bool = True,
                           error_message: str = None) -> bool:
        """记录 SDK 模式的交互"""
        metadata = {
            "model": model,
            "api_success": api_success,
            "error_message": error_message
        }
        return self.log_interaction(prompt, response, metadata, "sdk")

    def log_cli_interaction(self,
                           prompt: str,
                           response: str,
                           command: str = None,
                           exit_code: int = None,
                           error_message: str = None) -> bool:
        """记录 CLI 模式的交互"""
        metadata = {
            "command": command,
            "exit_code": exit_code,
            "error_message": error_message
        }
        return self.log_interaction(prompt, response, metadata, "cli")

    def get_log_files(self) -> list:
        """获取所有聊天日志文件列表"""
        if not self.config.logging.chat_log_enabled:
            return []

        try:
            chat_log_dir = Path(self.config.logging.chat_log_dir)
            if not chat_log_dir.exists():
                return []

            log_files = list(chat_log_dir.glob("chat_prompt_*.log"))
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return [str(f) for f in log_files]
        except Exception as e:
            print(f"获取聊天日志文件列表时出错: {e}")
            return []

    def get_log_stats(self) -> Dict[str, Any]:
        """获取聊天日志统计信息"""
        if not self.config.logging.chat_log_enabled:
            return {"enabled": False}

        try:
            log_files = self.get_log_files()
            total_size = 0
            total_interactions = 0

            for log_file in log_files:
                path = Path(log_file)
                if path.exists():
                    total_size += path.stat().st_size

                    # 简单统计交互次数（通过计算分隔符数量）
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 每个交互有 "时间戳:" 开头
                            interactions = content.count("时间戳:")
                            total_interactions += interactions
                    except Exception:
                        pass

            return {
                "enabled": True,
                "log_files_count": len(log_files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "total_interactions": total_interactions,
                "oldest_file": log_files[-1] if log_files else None,
                "newest_file": log_files[0] if log_files else None,
            }
        except Exception as e:
            print(f"获取聊天日志统计时出错: {e}")
            return {"enabled": True, "error": str(e)}


# 全局聊天日志记录器实例
_chat_logger = None


def get_chat_logger() -> ChatLogger:
    """获取全局聊天日志记录器实例"""
    global _chat_logger
    if _chat_logger is None:
        _chat_logger = ChatLogger()
    return _chat_logger


def log_llm_interaction(prompt: str, response: str, mode: str = "unknown", **kwargs) -> bool:
    """
    便捷函数：记录 LLM 交互

    Args:
        prompt: 提示词
        response: 回复
        mode: 调用模式 (sdk/cli)
        **kwargs: 其他元数据

    Returns:
        bool: 是否成功记录
    """
    logger = get_chat_logger()
    return logger.log_interaction(prompt, response, kwargs, mode)
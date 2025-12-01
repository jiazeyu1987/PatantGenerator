"""
用户自定义提示词管理器

负责管理用户自定义的撰写者和审核者提示词，
支持保存、读取、删除和持久化存储功能。
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class UserPromptManager:
    """用户自定义提示词管理器"""

    def __init__(self, data_dir: str = None):
        """
        初始化用户提示词管理器

        Args:
            data_dir: 数据存储目录，默认为 backend/data
        """
        if data_dir is None:
            current_dir = Path(__file__).parent
            self.data_dir = current_dir / "data"
        else:
            self.data_dir = Path(data_dir)

        self.data_file = self.data_dir / "user_prompts.json"

        # 确保数据目录存在
        self._ensure_data_dir()

        # 默认用户ID（单用户系统）
        self.default_user_id = "default"

        logger.info(f"用户提示词管理器初始化完成，数据文件: {self.data_file}")

    def _ensure_data_dir(self):
        """确保数据目录存在"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"数据目录已准备: {self.data_dir}")
        except Exception as e:
            logger.error(f"创建数据目录失败: {e}")
            raise RuntimeError(f"无法创建数据目录: {e}")

    def _load_data(self) -> Dict[str, Any]:
        """加载用户提示词数据"""
        try:
            if not self.data_file.exists():
                return self._create_default_data()

            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 验证数据结构
            if not isinstance(data, dict) or 'prompts' not in data:
                logger.warning("用户提示词数据格式不正确，使用默认数据")
                return self._create_default_data()

            logger.debug(f"成功加载用户提示词数据，包含 {len(data.get('prompts', {}))} 个提示词")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"用户提示词数据JSON解析失败: {e}")
            return self._create_default_data()
        except Exception as e:
            logger.error(f"加载用户提示词数据失败: {e}")
            return self._create_default_data()

    def _create_default_data(self) -> Dict[str, Any]:
        """创建默认数据结构"""
        return {
            "user_id": self.default_user_id,
            "prompts": {
                "writer": "",
                "reviewer": ""
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

    def _save_data(self, data: Dict[str, Any]) -> bool:
        """保存用户提示词数据"""
        try:
            # 更新时间戳
            data['updated_at'] = datetime.now().isoformat()

            # 原子性写入
            temp_file = self.data_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 原子性替换
            temp_file.replace(self.data_file)

            logger.debug("用户提示词数据保存成功")
            return True

        except Exception as e:
            logger.error(f"保存用户提示词数据失败: {e}")
            return False

    def get_user_prompt(self, prompt_type: str, user_id: str = None) -> Optional[str]:
        """
        获取用户自定义提示词

        Args:
            prompt_type: 提示词类型 ('writer' 或 'reviewer')
            user_id: 用户ID，默认使用默认用户

        Returns:
            用户自定义的提示词，如果不存在则返回None
        """
        if user_id is None:
            user_id = self.default_user_id

        if prompt_type not in ['writer', 'reviewer']:
            logger.error(f"无效的提示词类型: {prompt_type}")
            return None

        try:
            data = self._load_data()
            prompts = data.get('prompts', {})

            user_prompt = prompts.get(prompt_type)
            if user_prompt and user_prompt.strip():
                logger.debug(f"获取到用户自定义{prompt_type}提示词，长度: {len(user_prompt)}")
                return user_prompt
            else:
                logger.debug(f"用户未设置{prompt_type}提示词")
                return None

        except Exception as e:
            logger.error(f"获取用户{prompt_type}提示词失败: {e}")
            return None

    def set_user_prompt(self, prompt_type: str, prompt_content: str, user_id: str = None) -> bool:
        """
        设置用户自定义提示词

        Args:
            prompt_type: 提示词类型 ('writer' 或 'reviewer')
            prompt_content: 提示词内容
            user_id: 用户ID，默认使用默认用户

        Returns:
            设置成功返回True，失败返回False
        """
        if user_id is None:
            user_id = self.default_user_id

        if prompt_type not in ['writer', 'reviewer']:
            logger.error(f"无效的提示词类型: {prompt_type}")
            return False

        if not isinstance(prompt_content, str):
            logger.error("提示词内容必须是字符串类型")
            return False

        try:
            # 加载现有数据
            data = self._load_data()

            # 更新提示词
            if 'prompts' not in data:
                data['prompts'] = {}

            data['prompts'][prompt_type] = prompt_content.strip()
            data['user_id'] = user_id

            # 保存数据
            success = self._save_data(data)

            if success:
                logger.info(f"用户{prompt_type}提示词设置成功，长度: {len(prompt_content)}")
            else:
                logger.error(f"用户{prompt_type}提示词设置失败")

            return success

        except Exception as e:
            logger.error(f"设置用户{prompt_type}提示词失败: {e}")
            return False

    def delete_user_prompt(self, prompt_type: str, user_id: str = None) -> bool:
        """
        删除用户自定义提示词

        Args:
            prompt_type: 提示词类型 ('writer' 或 'reviewer')
            user_id: 用户ID，默认使用默认用户

        Returns:
            删除成功返回True，失败返回False
        """
        if user_id is None:
            user_id = self.default_user_id

        if prompt_type not in ['writer', 'reviewer']:
            logger.error(f"无效的提示词类型: {prompt_type}")
            return False

        try:
            data = self._load_data()

            if 'prompts' not in data or prompt_type not in data['prompts']:
                logger.debug(f"用户{prompt_type}提示词不存在，无需删除")
                return True

            # 删除提示词
            del data['prompts'][prompt_type]

            # 保存数据
            success = self._save_data(data)

            if success:
                logger.info(f"用户{prompt_type}提示词删除成功")
            else:
                logger.error(f"用户{prompt_type}提示词删除失败")

            return success

        except Exception as e:
            logger.error(f"删除用户{prompt_type}提示词失败: {e}")
            return False

    def get_all_user_prompts(self, user_id: str = None) -> Dict[str, str]:
        """
        获取用户的所有自定义提示词

        Args:
            user_id: 用户ID，默认使用默认用户

        Returns:
            包含所有用户提示词的字典
        """
        if user_id is None:
            user_id = self.default_user_id

        try:
            data = self._load_data()
            return data.get('prompts', {})

        except Exception as e:
            logger.error(f"获取用户所有提示词失败: {e}")
            return {}

    def has_user_prompt(self, prompt_type: str, user_id: str = None) -> bool:
        """
        检查用户是否设置了指定类型的提示词

        Args:
            prompt_type: 提示词类型 ('writer' 或 'reviewer')
            user_id: 用户ID，默认使用默认用户

        Returns:
            如果用户设置了提示词返回True，否则返回False
        """
        prompt = self.get_user_prompt(prompt_type, user_id)
        return bool(prompt and prompt.strip())

    def get_prompt_stats(self, user_id: str = None) -> Dict[str, Any]:
        """
        获取用户提示词统计信息

        Args:
            user_id: 用户ID，默认使用默认用户

        Returns:
            包含统计信息的字典
        """
        if user_id is None:
            user_id = self.default_user_id

        try:
            data = self._load_data()
            prompts = data.get('prompts', {})

            stats = {
                'user_id': user_id,
                'has_writer_prompt': bool(prompts.get('writer', '').strip()),
                'has_reviewer_prompt': bool(prompts.get('reviewer', '').strip()),
                'writer_prompt_length': len(prompts.get('writer', '')),
                'reviewer_prompt_length': len(prompts.get('reviewer', '')),
                'last_updated': data.get('updated_at'),
                'created_at': data.get('created_at')
            }

            return stats

        except Exception as e:
            logger.error(f"获取用户提示词统计失败: {e}")
            return {}


# 全局用户提示词管理器实例
_user_prompt_manager = None


def get_user_prompt_manager() -> UserPromptManager:
    """获取用户提示词管理器实例（单例模式）"""
    global _user_prompt_manager
    if _user_prompt_manager is None:
        _user_prompt_manager = UserPromptManager()
    return _user_prompt_manager
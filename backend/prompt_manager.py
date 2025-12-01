"""
提示词管理器

统一管理和加载所有提示词配置，支持模板变量替换、版本管理和动态加载。
"""

import os
import yaml
import re
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PromptConfig:
    """提示词配置数据类"""
    name: str
    version: str
    description: str
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    file_path: str
    loaded_at: float


class PromptManager:
    """提示词管理器"""

    def __init__(self, prompts_dir: str = None):
        """
        初始化提示词管理器

        Args:
            prompts_dir: 提示词配置目录路径，默认为项目根目录下的 prompts
        """
        if prompts_dir is None:
            # 默认提示词目录为项目根目录下的 prompts
            current_dir = Path(__file__).parent
            prompts_dir = current_dir.parent / "prompts"

        self.prompts_dir = Path(prompts_dir)
        self._cache: Dict[str, PromptConfig] = {}
        self._template_cache: Dict[str, str] = {}

        logger.info(f"提示词管理器初始化，目录: {self.prompts_dir}")

        # 预加载所有提示词配置
        self._load_all_prompts()

    def _load_all_prompts(self):
        """加载所有提示词配置文件"""
        if not self.prompts_dir.exists():
            logger.warning(f"提示词目录不存在: {self.prompts_dir}")
            return

        # 递归查找所有 YAML 文件
        yaml_files = list(self.prompts_dir.rglob("*.yaml"))
        yaml_files.extend(list(self.prompts_dir.rglob("*.yml")))

        loaded_count = 0
        for yaml_file in yaml_files:
            try:
                config = self._load_prompt_file(yaml_file)
                if config:
                    key = self._get_prompt_key(yaml_file)
                    self._cache[key] = config
                    loaded_count += 1
                    logger.debug(f"加载提示词配置: {key} from {yaml_file}")
            except Exception as e:
                logger.error(f"加载提示词配置失败 {yaml_file}: {e}")

        logger.info(f"提示词配置加载完成，共加载 {loaded_count} 个配置文件")

    def _load_prompt_file(self, file_path: Path) -> Optional[PromptConfig]:
        """加载单个提示词配置文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            # 验证必需的元数据
            metadata = data.get('metadata', {})
            if not all(key in metadata for key in ['name', 'version', 'description']):
                logger.warning(f"提示词配置缺少必需元数据: {file_path}")
                return None

            config = PromptConfig(
                name=metadata['name'],
                version=metadata['version'],
                description=metadata['description'],
                content=data,
                metadata=metadata,
                file_path=str(file_path),
                loaded_at=os.path.getmtime(file_path)
            )

            return config

        except yaml.YAMLError as e:
            logger.error(f"YAML 解析错误 {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"读取文件错误 {file_path}: {e}")
            return None

    def _get_prompt_key(self, file_path: Path) -> str:
        """根据文件路径生成提示词键名"""
        relative_path = file_path.relative_to(self.prompts_dir)
        # 移除扩展名并转换为点分隔的键名
        key_parts = list(relative_path.parts)
        key_parts[-1] = key_parts[-1].replace('.yaml', '').replace('.yml', '')
        return '.'.join(key_parts)

    def get_prompt(self, key: str, **kwargs) -> str:
        """
        获取提示词模板并进行变量替换

        Args:
            key: 提示词键名，如 "patent.writer.base_prompt"
            **kwargs: 模板变量

        Returns:
            替换变量后的提示词字符串

        Raises:
            ValueError: 提示词不存在或变量替换失败
        """
        if key not in self._cache:
            # 尝试重新加载配置
            self._load_all_prompts()
            if key not in self._cache:
                raise ValueError(f"提示词配置不存在: {key}")

        config = self._cache[key]

        try:
            # 生成提示词
            prompt_parts = self._build_prompt_from_config(config.content, **kwargs)
            return '\n'.join(prompt_parts)

        except Exception as e:
            logger.error(f"构建提示词失败 {key}: {e}")
            raise ValueError(f"构建提示词失败: {str(e)}")

    def _build_prompt_from_config(self, config: Dict[str, Any], **kwargs) -> List[str]:
        """根据配置构建提示词"""
        parts = []

        # 获取提示词配置
        prompt_config = config.get('prompt', {})

        # 添加角色设定
        if 'role' in prompt_config:
            parts.append(prompt_config['role'])

        # 添加目标/任务说明
        if 'objective' in prompt_config:
            parts.append(prompt_config['objective'])
        elif 'task' in prompt_config:
            parts.append(prompt_config['task'])

        # 添加要求列表
        if 'requirements' in prompt_config:
            if isinstance(prompt_config['requirements'], list):
                requirements_text = '\n'.join(f"- {req}" for req in prompt_config['requirements'])
                parts.append("整体要求：")
                parts.append(requirements_text)

        # 添加审查重点（评审专用）
        if 'review_focus' in prompt_config:
            if isinstance(prompt_config['review_focus'], list):
                focus_text = '\n'.join(f"- {focus}" for focus in prompt_config['review_focus'])
                parts.append("审查重点包括但不限于：")
                parts.append(focus_text)

        # 处理迭代阶段信息
        iteration = kwargs.get('iteration', 1)
        total_iterations = kwargs.get('total_iterations', 1)
        iteration_info = f"这是第 {iteration}/{total_iterations} 轮"

        if 'iteration_phases' in config:
            iteration_config = config['iteration_phases']
            if iteration == 1 and 'first_iteration' in iteration_config:
                parts.append(iteration_info)
                parts.append(iteration_config['first_iteration']['instruction'])
            elif iteration > 1 and 'subsequent_iteration' in iteration_config:
                parts.append(iteration_info)
                parts.append(iteration_config['subsequent_iteration']['instruction'])
        else:
            # 默认迭代信息
            parts.append(iteration_info)

        parts.append("")  # 空行分隔

        # 添加上下文章节
        context_sections = config.get('context_sections', {})
        for section_key, section_config in context_sections.items():
            section_title = section_config['title']
            placeholder = section_config['placeholder']

            # 检查条件
            condition = section_config.get('condition')
            if condition and condition not in kwargs or not kwargs.get(condition):
                continue

            # 提取变量名
            var_match = re.search(r'\{\{(\w+)\}\}', placeholder)
            if var_match:
                var_name = var_match.group(1)
                if var_name in kwargs and kwargs[var_name]:
                    parts.append(section_title)
                    parts.append(str(kwargs[var_name]))
                    parts.append("")

        # 添加最终指令
        if 'final_instruction' in prompt_config:
            parts.append(prompt_config['final_instruction'])
        elif 'output_format' in prompt_config:
            parts.append(prompt_config['output_format'])

        return parts

    def get_prompt_config(self, key: str) -> Optional[PromptConfig]:
        """
        获取提示词配置对象

        Args:
            key: 提示词键名

        Returns:
            提示词配置对象，如果不存在则返回 None
        """
        return self._cache.get(key)

    def list_prompts(self, category: str = None) -> Dict[str, PromptConfig]:
        """
        列出所有提示词配置

        Args:
            category: 分类过滤，如 "patent" 或 "code"

        Returns:
            提示词配置字典
        """
        if category:
            return {k: v for k, v in self._cache.items() if k.startswith(category)}
        return self._cache.copy()

    def reload_prompts(self):
        """重新加载所有提示词配置"""
        logger.info("重新加载提示词配置")
        self._cache.clear()
        self._template_cache.clear()
        self._load_all_prompts()

    def validate_prompt(self, key: str, **kwargs) -> Dict[str, Any]:
        """
        验证提示词和变量

        Args:
            key: 提示词键名
            **kwargs: 测试变量

        Returns:
            验证结果字典
        """
        result = {
            'valid': False,
            'error': None,
            'missing_vars': [],
            'prompt': None
        }

        try:
            prompt = self.get_prompt(key, **kwargs)
            result['prompt'] = prompt
            result['valid'] = True

        except Exception as e:
            result['error'] = str(e)

        return result

    def get_prompt_stats(self) -> Dict[str, Any]:
        """
        获取提示词统计信息

        Returns:
            统计信息字典
        """
        stats = {
            'total_prompts': len(self._cache),
            'categories': {},
            'versions': {},
            'total_files': 0
        }

        for key, config in self._cache.items():
            # 分类统计
            parts = key.split('.')
            if len(parts) >= 2:
                category = parts[0]
                stats['categories'][category] = stats['categories'].get(category, 0) + 1

            # 版本统计
            version = config.version
            stats['versions'][version] = stats['versions'].get(version, 0) + 1

        # 文件统计
        if self.prompts_dir.exists():
            yaml_files = list(self.prompts_dir.rglob("*.yaml"))
            yaml_files.extend(list(self.prompts_dir.rglob("*.yml")))
            stats['total_files'] = len(yaml_files)

        return stats


# 全局提示词管理器实例
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """获取全局提示词管理器实例"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


def get_prompt(key: str, **kwargs) -> str:
    """
    便捷函数：获取提示词

    Args:
        key: 提示词键名
        **kwargs: 模板变量

    Returns:
        提示词字符串
    """
    manager = get_prompt_manager()
    return manager.get_prompt(key, **kwargs)


# 常用提示词键名常量
class PromptKeys:
    """提示词键名常量"""
    PATENT_WRITER = "patent.writer.base_prompt"
    PATENT_REVIEWER = "patent.reviewer.base_prompt"
    CODE_ANALYZER = "code.analyzer.base_prompt"
"""
简单提示词引擎

核心功能：直接使用用户提示词或提供默认提示词
设计原则：KISS - Keep It Simple, Stupid
"""

import logging
from typing import Optional
from user_prompt_manager import get_user_prompt_manager
from pathlib import Path

logger = logging.getLogger(__name__)


class SimplePromptEngine:
    """
    简单提示词引擎

    核心逻辑：
    1. 检查用户是否设置了自定义提示词
    2. 如果存在，直接返回用户提示词（100%原样，不做任何修改）
    3. 如果不存在，使用简单的系统默认提示词
    """

    def __init__(self):
        self.user_prompt_manager = get_user_prompt_manager()
        self.logger = logger

        # 预加载默认提示词
        self._default_writer_prompt = self._load_default_prompt("writer")
        self._default_reviewer_prompt = self._load_default_prompt("reviewer")

        self.logger.info("SimplePromptEngine 初始化完成")

    def _load_default_prompt(self, prompt_type: str) -> str:
        """加载默认提示词"""
        try:
            prompt_file = Path(__file__).parent / "prompts" / f"simple_{prompt_type}_prompt.txt"
            if prompt_file.exists():
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.logger.info(f"已加载默认{prompt_type}提示词，长度: {len(content)}")
                return content
            else:
                self.logger.warning(f"默认{prompt_type}提示词文件不存在: {prompt_file}")
                return self._get_hardcoded_default_prompt(prompt_type)
        except Exception as e:
            self.logger.error(f"加载默认{prompt_type}提示词失败: {e}")
            return self._get_hardcoded_default_prompt(prompt_type)

    def _get_hardcoded_default_prompt(self, prompt_type: str) -> str:
        """硬编码的默认提示词（作为备用）"""
        if prompt_type == "writer":
            return """你现在扮演一名资深的中国发明专利撰写专家。

任务：基于给定的技术背景和创新点，撰写一份结构完整、符合中国专利法和实务规范的发明专利草案。

要求：
1. 使用 Markdown 编写完整专利文档
2. 包含标题、技术领域、背景技术、发明内容、具体实施方式、权利要求书、摘要等章节
3. 语言客观、严谨，避免营销化和口语化表述
4. 确保权利要求书有独立权利要求和若干从属权利要求

请直接输出完整、可独立阅读的 Markdown 专利文档，不要额外附加解释说明。"""

        elif prompt_type == "reviewer":
            return """你现在扮演一名资深专利代理人 / 合规审查专家。

任务：对下面的专利草案进行严格审查，找出所有可能的合规风险、缺陷和可改进之处，并给出条理清晰的修改建议。

审查重点：
- 是否充分体现并保护核心创新点
- 权利要求书是否具备新颖性、创造性和实用性
- 是否存在模糊、主观或不清楚的表述
- 技术描述是否准确、一致
- 文档结构是否完整、格式是否规范

请以 Markdown 输出评审结果，包含：
1. 概览评语
2. 问题清单（每条包括问题描述和修改建议）
3. 总体风险评估

不要重写专利全文，只给出评审和修改建议。"""

        else:
            return f"默认{prompt_type}提示词"

    def get_writer_prompt(self, context: str, previous_draft: Optional[str] = None,
                         previous_review: Optional[str] = None, iteration: int = 1,
                         total_iterations: int = 1) -> str:
        """
        获取撰写者提示词

        Args:
            context: 技术背景和创新点上下文
            previous_draft: 上一版专利草案
            previous_review: 上一轮评审意见
            iteration: 当前迭代轮次
            total_iterations: 总迭代轮次

        Returns:
            str: 最终使用的撰写者提示词
        """
        self.logger.info("=== 开始获取撰写者提示词 ===")

        # 1. 检查用户自定义提示词
        try:
            user_prompt = self.user_prompt_manager.get_user_prompt('writer')

            self.logger.info(f"用户撰写者提示词检查:")
            self.logger.info(f"  - 提示词存在: {bool(user_prompt)}")

            if user_prompt and user_prompt.strip():
                prompt_length = len(user_prompt)
                is_empty = not user_prompt.strip()

                self.logger.info(f"  - 提示词长度: {prompt_length} 字符")
                self.logger.info(f"  - 提示词为空: {is_empty}")
                self.logger.info(f"  - 提示词开头: {user_prompt[:100]}...")
                self.logger.info(f"  - 提示词结尾: ...{user_prompt[-50:]}")

                if not is_empty:
                    self.logger.info("✅ 决定：使用用户自定义撰写者提示词（100%原样）")
                    self.logger.info(f"最终提示词长度: {prompt_length} 字符")
                    self.logger.info("=== 撰写者提示词获取完成 ===")
                    return user_prompt  # 直接返回，不做任何修改
                else:
                    self.logger.warning("用户提示词存在但为空字符串")
            else:
                self.logger.info("用户未设置撰写者提示词")

        except Exception as e:
            self.logger.error(f"检查用户撰写者提示词时出错: {e}")

        # 2. 使用默认提示词
        self.logger.info("✅ 决定：使用系统默认撰写者提示词")
        final_prompt = self._default_writer_prompt
        self.logger.info(f"默认提示词长度: {len(final_prompt)} 字符")
        self.logger.info("=== 撰写者提示词获取完成 ===")

        return final_prompt

    def get_reviewer_prompt(self, context: str, current_draft: str,
                           iteration: int = 1, total_iterations: int = 1) -> str:
        """
        获取审核者提示词

        Args:
            context: 技术背景和创新点上下文
            current_draft: 当前专利草案
            iteration: 当前迭代轮次
            total_iterations: 总迭代轮次

        Returns:
            str: 最终使用的审核者提示词
        """
        self.logger.info("=== 开始获取审核者提示词 ===")

        # 1. 检查用户自定义提示词
        try:
            user_prompt = self.user_prompt_manager.get_user_prompt('reviewer')

            self.logger.info(f"用户审核者提示词检查:")
            self.logger.info(f"  - 提示词存在: {bool(user_prompt)}")

            if user_prompt and user_prompt.strip():
                prompt_length = len(user_prompt)
                is_empty = not user_prompt.strip()

                self.logger.info(f"  - 提示词长度: {prompt_length} 字符")
                self.logger.info(f"  - 提示词为空: {is_empty}")
                self.logger.info(f"  - 提示词开头: {user_prompt[:100]}...")
                self.logger.info(f"  - 提示词结尾: ...{user_prompt[-50:]}")

                if not is_empty:
                    self.logger.info("✅ 决定：使用用户自定义审核者提示词（100%原样）")
                    self.logger.info(f"最终提示词长度: {prompt_length} 字符")
                    self.logger.info("=== 审核者提示词获取完成 ===")
                    return user_prompt  # 直接返回，不做任何修改
                else:
                    self.logger.warning("用户提示词存在但为空字符串")
            else:
                self.logger.info("用户未设置审核者提示词")

        except Exception as e:
            self.logger.error(f"检查用户审核者提示词时出错: {e}")

        # 2. 使用默认提示词
        self.logger.info("✅ 决定：使用系统默认审核者提示词")
        final_prompt = self._default_reviewer_prompt
        self.logger.info(f"默认提示词长度: {len(final_prompt)} 字符")
        self.logger.info("=== 审核者提示词获取完成 ===")

        return final_prompt


def get_simple_prompt_engine() -> SimplePromptEngine:
    """获取简单提示词引擎实例"""
    return SimplePromptEngine()
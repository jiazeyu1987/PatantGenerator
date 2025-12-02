import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from llm_client import call_llm
from prompt_manager import get_prompt, PromptKeys
from template_manager import get_template_manager
from docx_generator import generate_patent_docx, validate_patent_template
from conversation_db import get_conversation_db
from user_prompt_manager import get_user_prompt_manager

logger = logging.getLogger(__name__)

# 简单提示词逻辑（直接嵌入，避免复杂依赖）
def get_simple_prompt_engine():
    """获取简单提示词引擎实例（内联实现）"""
    try:
        user_prompt_manager = get_user_prompt_manager()

        class SimplePromptEngine:
            def __init__(self):
                self.user_prompt_manager = user_prompt_manager
                self.logger = logger

                # 加载默认提示词
                self._default_writer_prompt = """你现在扮演一名资深的中国发明专利撰写专家。

任务：基于给定的技术背景和创新点，撰写一份结构完整、符合中国专利法和实务规范的发明专利草案。

要求：
1. 使用 Markdown 编写完整专利文档
2. 包含标题、技术领域、背景技术、发明内容、具体实施方式、权利要求书、摘要等章节
3. 语言客观、严谨，避免营销化和口语化表述
4. 确保权利要求书有独立权利要求和若干从属权利要求

请直接输出完整、可独立阅读的 Markdown 专利文档，不要额外附加解释说明。"""

                self._default_reviewer_prompt = """你现在扮演一名资深专利代理人 / 合规审查专家。

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

                self._default_modifier_prompt = """你现在扮演一名资深的中国发明专利修改专家。

任务：基于给定的技术背景、上轮专利草案和评审意见，对专利文档进行针对性的修改和优化。

修改原则：
1. 精准回应：重点解决评审中指出的合规风险和缺陷
2. 保持创新：确保核心技术创新点得到充分保护
3. 结构优化：完善专利文档的逻辑结构和表述清晰度
4. 权利要求强化：根据评审意见优化权利要求的范围和表述
5. 技术准确性：确保技术描述准确、一致，消除模糊表述

请直接输出修改后的完整专利 Markdown 文档，不要额外附加解释说明。

注意：
- 重点关注上一轮评审中发现的问题
- 保持专利文档的完整性和专业性
- 语言客观、严谨，避免营销化表述
- 确保修改后的文档符合中国专利法要求"""

                self._default_template_prompt = """你现在扮演一名专业的专利模板分析师。

任务：对给定的专利模板文件（DOCX格式）进行深入分析，评估其质量、复杂度和实用性。

分析维度：
1. 模板结构完整性：
   - 检查是否包含专利文档的标准章节（标题、技术领域、背景技术、发明内容、附图说明、具体实施方式、权利要求书、摘要）
   - 评估章节顺序和逻辑结构的合理性
   - 识别缺失或冗余的章节

2. 内容质量评估：
   - 分析模板指导语的清晰度和专业性
   - 评估示例内容的准确性和完整性
   - 检查是否符合中国专利法要求

3. 可用性分析：
   - 评估模板对不同技术领域的适应性
   - 分析修改和定制的难易程度
   - 判断模板对新手用户的友好度

4. 技术特征识别：
   - 识别模板中使用的关键技术和术语
   - 分析模板支持的技术创新类型
   - 评估模板对复杂技术的支持能力

5. 改进建议：
   - 提出具体的优化建议
   - 推荐适合的应用场景
   - 建议增强或简化的部分

请基于提供的模板内容，输出一份结构化、专业化的模板分析报告，包含详细的质量评分和实用建议。

注意：
- 分析要客观、专业，基于实际的模板内容
- 重点评估模板的实用性和改进价值
- 提供具体可操作的建议"""

                logger.info("SimplePromptEngine 初始化完成")

            def get_writer_prompt(self, context, previous_draft=None, previous_review=None, iteration=1, total_iterations=1, idea_text=None):
                logger.info("=== 开始获取撰写者提示词 ===")
                logger.info(f"参数检查: iteration={iteration}, total_iterations={total_iterations}")
                logger.info(f"idea_text参数检查: 存在={bool(idea_text)}, 长度={len(idea_text) if idea_text else 0}")
                if idea_text:
                    logger.info(f"idea_text内容预览: {idea_text[:100]}...")

                try:
                    user_prompt = self.user_prompt_manager.get_user_prompt('writer')
                    logger.info(f"用户撰写者提示词检查: 存在={bool(user_prompt)}")

                    if user_prompt and user_prompt.strip():
                        logger.info(f"用户提示词长度: {len(user_prompt)} 字符")
                        logger.info(f"用户提示词开头: {user_prompt[:100]}...")
                        logger.info(f"用户提示词是否包含<idea_text>标记: {'<idea_text>' in user_prompt}")

                        # 检查是否包含 <idea_text> 标记，如果有则进行替换
                        if "<idea_text>" in user_prompt:
                            logger.info("🔍 检测到<idea_text>标记，启用创意文本替换")
                            if idea_text and idea_text.strip():
                                logger.info(f"✅ idea_text内容有效，开始替换")
                                original_prompt = user_prompt
                                user_prompt = user_prompt.replace("<idea_text>", idea_text)
                                logger.info(f"✅ 成功替换<idea_text>标记")
                                logger.info(f"   - 替换前提示词长度: {len(original_prompt)}")
                                logger.info(f"   - 替换后提示词长度: {len(user_prompt)}")
                                logger.info(f"   - 创意文本长度: {len(idea_text)}")
                                logger.info(f"   - 替换后提示词开头: {user_prompt[:200]}...")
                            else:
                                logger.warning("⚠️ 检测到<idea_text>标记但idea_text为空或无效")
                                user_prompt = user_prompt.replace("<idea_text>", "[用户创意内容]")
                                logger.info("已将<idea_text>标记替换为占位文本")
                        else:
                            logger.info("ℹ️ 用户提示词中未检测到<idea_text>标记")

                        logger.info("✅ 使用用户自定义撰写者提示词（支持<idea_text>替换）")
                        return user_prompt
                    else:
                        logger.info("用户未设置撰写者提示词，使用系统默认")

                        # 也检查默认提示词是否包含 <idea_text> 标记
                        default_prompt = self._default_writer_prompt
                        logger.info(f"系统默认提示词长度: {len(default_prompt)} 字符")
                        logger.info(f"系统默认提示词是否包含<idea_text>标记: {'<idea_text>' in default_prompt}")

                        if "<idea_text>" in default_prompt:
                            logger.info("🔍 检测到系统默认提示词中的<idea_text>标记，启用创意文本替换")
                            if idea_text and idea_text.strip():
                                logger.info(f"✅ idea_text内容有效，开始替换默认提示词")
                                original_prompt = default_prompt
                                default_prompt = default_prompt.replace("<idea_text>", idea_text)
                                logger.info(f"✅ 成功替换默认提示词中的<idea_text>标记")
                                logger.info(f"   - 替换前提示词长度: {len(original_prompt)}")
                                logger.info(f"   - 替换后提示词长度: {len(default_prompt)}")
                                logger.info(f"   - 创意文本长度: {len(idea_text)}")
                            else:
                                logger.warning("⚠️ 检测到<idea_text>标记但idea_text为空或无效")
                                default_prompt = default_prompt.replace("<idea_text>", "[用户创意内容]")
                                logger.info("已将默认提示词中的<idea_text>标记替换为占位文本")
                        else:
                            logger.info("ℹ️ 系统默认提示词中未检测到<idea_text>标记")

                        logger.info("✅ 使用系统默认撰写者提示词（支持<idea_text>替换）")
                        return default_prompt

                except Exception as e:
                    logger.error(f"检查用户撰写者提示词失败: {e}")
                    return self._default_writer_prompt

            def get_reviewer_prompt(self, context, current_draft, iteration=1, total_iterations=1):
                logger.info("=== 开始获取审核者提示词 ===")

                try:
                    user_prompt = self.user_prompt_manager.get_user_prompt('reviewer')
                    logger.info(f"用户审核者提示词检查: 存在={bool(user_prompt)}")

                    if user_prompt and user_prompt.strip():
                        logger.info(f"用户提示词长度: {len(user_prompt)} 字符")
                        logger.info(f"用户提示词开头: {user_prompt[:100]}...")

                        # 检查是否包含</text>标记
                        if "</text>" in user_prompt:
                            logger.info("检测到</text>标记，使用动态替换模式")
                            final_prompt = _build_prompt_from_template(
                                user_prompt,
                                context=context,
                                current_draft=current_draft,
                                iteration=iteration,
                                total_iterations=total_iterations,
                                strict_mode=True
                            )
                        else:
                            logger.info("✅ 使用用户自定义审核者提示词（100%原样）")
                            final_prompt = user_prompt

                        return final_prompt
                    else:
                        logger.info("用户未设置审核者提示词，使用系统默认")
                        return self._default_reviewer_prompt

                except Exception as e:
                    logger.error(f"检查用户审核者提示词失败: {e}")
                    return self._default_reviewer_prompt

            def get_modifier_prompt(self, context, previous_draft, previous_review, iteration=1, total_iterations=1, idea_text=None):
                logger.info("=== 开始获取修改者提示词 ===")

                try:
                    user_prompt = self.user_prompt_manager.get_user_prompt('modifier')
                    logger.info(f"用户修改者提示词检查: 存在={bool(user_prompt)}")

                    if user_prompt and user_prompt.strip():
                        logger.info(f"用户提示词长度: {len(user_prompt)} 字符")
                        logger.info(f"用户提示词开头: {user_prompt[:100]}...")

                        # 检查是否包含动态标记（支持新标记和向后兼容）
                        has_markers = ("</text>" in user_prompt or
                                      "<previous_output>" in user_prompt or
                                      "<previous_review>" in user_prompt)

                        if has_markers:
                            logger.info("检测到动态标记，使用动态替换模式")
                            if "</text>" in user_prompt:
                                logger.info("  - 检测到</text>标记（向后兼容）")
                            if "<previous_output>" in user_prompt:
                                logger.info("  - 检测到<previous_output>标记（新功能）")
                            if "<previous_review>" in user_prompt:
                                logger.info("  - 检测到<previous_review>标记（新功能）")

                            final_prompt = _build_prompt_from_template(
                                user_prompt,
                                context=context,
                                previous_draft=previous_draft,
                                previous_review=previous_review,
                                iteration=iteration,
                                total_iterations=total_iterations,
                                strict_mode=True,
                                idea_text=idea_text
                            )
                        else:
                            logger.info("✅ 使用用户自定义修改者提示词（100%原样，无动态标记）")
                            final_prompt = user_prompt

                        return final_prompt
                    else:
                        logger.info("用户未设置修改者提示词，使用系统默认")
                        return self._default_modifier_prompt

                except Exception as e:
                    logger.error(f"检查用户修改者提示词失败: {e}")
                    return self._default_modifier_prompt

            def get_template_prompt(self, template_content=None, **kwargs):
                """获取模板分析提示词"""
                logger.info("=== 开始获取模板分析提示词 ===")

                try:
                    user_prompt = self.user_prompt_manager.get_user_prompt('template')
                    logger.info(f"用户模板分析提示词检查: 存在={bool(user_prompt)}")

                    if user_prompt and user_prompt.strip():
                        logger.info(f"用户提示词长度: {len(user_prompt)} 字符")
                        logger.info("✅ 使用用户自定义模板分析提示词")
                        return user_prompt
                    else:
                        logger.info("用户未设置模板分析提示词，使用系统默认")
                        return self._default_template_prompt

                except Exception as e:
                    logger.error(f"检查用户模板分析提示词失败: {e}")
                    return self._default_template_prompt

        return SimplePromptEngine()

    except Exception as e:
        logger.error(f"创建简单提示词引擎失败: {e}")
        # 返回一个空的引擎对象
        class EmptyPromptEngine:
            def get_writer_prompt(self, *args, **kwargs):
                return "默认撰写者提示词"
            def get_modifier_prompt(self, *args, **kwargs):
                return "默认修改者提示词"
            def get_reviewer_prompt(self, *args, **kwargs):
                return "默认审核者提示词"
            def get_template_prompt(self, *args, **kwargs):
                return "默认模板分析提示词"
        return EmptyPromptEngine()


def build_writer_prompt(
    context: str,
    previous_draft: Optional[str],
    previous_review: Optional[str],
    iteration: int,
    total_iterations: int,
    template_id: Optional[str] = None,
    idea_text: Optional[str] = None,
) -> str:
    """
    使用配置化提示词构建专利撰写提示词

    Args:
        context: 技术背景和创新点上下文
        previous_draft: 上一版专利草案
        previous_review: 上一轮评审意见
        iteration: 当前迭代轮次
        total_iterations: 总迭代轮次
        template_id: 模板ID，用于智能分析
        idea_text: 用户输入的创意文本（用于创意模式下的 <idea_text> 标记替换）

    Returns:
        构建完成的提示词字符串
    """
    try:
        # 添加调试日志记录历史数据
        logger.info(f"构建撰写者提示词 - 第 {iteration}/{total_iterations} 轮")
        logger.debug(f"模板ID: {template_id}")

        if previous_draft:
            logger.debug(f"上一版草案长度: {len(previous_draft)} 字符")
            logger.debug(f"上一版草案前100字符: {previous_draft[:100]}...")
        else:
            logger.debug("没有上一版草案 (首轮撰写)")

        if previous_review:
            logger.debug(f"上一轮评审长度: {len(previous_review)} 字符")
            logger.debug(f"上一轮评审前100字符: {previous_review[:100]}...")
        else:
            logger.debug("没有上一轮评审 (首轮撰写)")

        # 优先检查用户自定义提示词
        user_prompt_manager = get_user_prompt_manager()
        user_custom_prompt = user_prompt_manager.get_user_prompt('writer')

        if user_custom_prompt and user_custom_prompt.strip():
            logger.info("使用用户自定义撰写者提示词")
            logger.debug(f"用户自定义提示词长度: {len(user_custom_prompt)} 字符")

            # 使用用户自定义提示词，启用严格模式
            prompt = _build_prompt_from_template(
                user_custom_prompt,
                context=context,
                previous_draft=previous_draft,
                previous_review=previous_review,
                iteration=iteration,
                total_iterations=total_iterations,
                strict_mode=True,
                idea_text=idea_text
            )
        else:
            logger.debug("用户未设置自定义撰写者提示词，使用系统默认")
            # 使用增强的提示词管理器获取配置化提示词
            prompt = get_prompt(
                PromptKeys.PATENT_WRITER,
                context=context,
                previous_draft=previous_draft,
                previous_review=previous_review,
                iteration=iteration,
                total_iterations=total_iterations,
                template_id=template_id,
                idea_text=idea_text  # 添加创意文本参数
            )

        # 检查提示词是否包含历史内容
        if iteration > 1:
            has_draft_section = "【上一版专利草案】" in prompt
            has_review_section = "【合规评审与问题清单】" in prompt
            logger.info(f"提示词包含历史内容检查:")
            logger.info(f"  包含上一版草案: {has_draft_section}")
            logger.info(f"  包含评审意见: {has_review_section}")
            logger.debug(f"提示词总长度: {len(prompt)} 字符")

        return prompt
    except Exception as e:
        # 如果配置化提示词失败，回退到原始硬编码提示词
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"使用配置化提示词失败，回退到硬编码提示词: {e}")

        return _build_writer_prompt_fallback(
            context, previous_draft, previous_review, iteration, total_iterations
        )


def _build_writer_prompt_fallback(
    context: str,
    previous_draft: Optional[str],
    previous_review: Optional[str],
    iteration: int,
    total_iterations: int,
) -> str:
    """硬编码提示词回退方案"""
    parts = []
    parts.append("你现在扮演一名资深的中国发明专利撰写专家。")
    parts.append("目标：基于给定的技术背景和创新点，撰写一份结构完整、符合中国专利法和实务规范的发明专利草案。")
    parts.append("")
    parts.append("整体要求：")
    parts.append("- 使用 Markdown 编写完整专利文档；")
    parts.append("- 章节建议包括但不限于：标题、技术领域、背景技术、发明内容、附图说明、具体实施方式、权利要求书、摘要；")
    parts.append("- 如需要图表，使用简洁的描述性语言说明图表内容和结构关系；")
    parts.append("- 语言应尽可能客观、严谨、避免营销化和口语化表述；")
    parts.append("- 权利要求书要有独立权利要求和若干从属权利要求，并尽量覆盖主要创新点。")
    parts.append("")
    parts.append(f"这是第 {iteration}/{total_iterations} 轮写作。")

    if iteration == 1:
        parts.append("你需要基于下面的技术背景/创新点，给出首版完整专利草案：")
    else:
        parts.append("你需要在上一版草案基础上，结合评审意见对文档进行整体修订和增强。")

    parts.append("")
    parts.append("【技术背景与创新点上下文】")
    parts.append(context)
    parts.append("")

    if previous_draft:
        parts.append("【上一版专利草案】")
        parts.append(previous_draft)
        parts.append("")

    if previous_review:
        parts.append("【合规评审与问题清单】")
        parts.append(previous_review)
        parts.append("")

    parts.append("请直接输出完整、可独立阅读的 Markdown 专利文档，不要额外附加解释说明。")

    return "\n".join(parts)


def build_reviewer_prompt(
    context: str,
    current_draft: str,
    iteration: int,
    total_iterations: int,
    template_info: Optional[Dict[str, Any]] = None,
    template_id: Optional[str] = None,
) -> str:
    """
    使用配置化提示词构建专利评审提示词

    Args:
        context: 技术背景和创新点上下文
        current_draft: 当前待评审的专利草案
        iteration: 当前评审轮次
        total_iterations: 总评审轮次
        template_info: 模板信息，用于格式一致性检查
        template_id: 模板ID，用于智能分析

    Returns:
        构建完成的提示词字符串
    """
    try:
        # 调试日志：记录评审请求的模板ID
        logger.info(f"构建评审提示词，模板ID: {template_id}")

        # 优先检查用户自定义提示词
        user_prompt_manager = get_user_prompt_manager()
        user_custom_prompt = user_prompt_manager.get_user_prompt('reviewer')

        if user_custom_prompt and user_custom_prompt.strip():
            logger.info("使用用户自定义审核者提示词")
            logger.debug(f"用户自定义提示词长度: {len(user_custom_prompt)} 字符")

            # 使用用户自定义提示词，启用严格模式
            prompt = _build_prompt_from_template(
                user_custom_prompt,
                context=context,
                current_draft=current_draft,
                iteration=iteration,
                total_iterations=total_iterations,
                strict_mode=True
            )
        else:
            logger.debug("用户未设置自定义审核者提示词，使用系统默认")
            # 构建模板信息文本（保持向后兼容）
            template_info_text = ""
            if template_info:
                template_info_text = f"\n【模板信息】\n使用模板: {template_info.get('name', '未知模板')}\n模板ID: {template_info.get('id', '未知')}\n"

            # 使用增强的提示词管理器获取配置化提示词
            prompt = get_prompt(
                PromptKeys.PATENT_REVIEWER,
                context=context + template_info_text,
                current_draft=current_draft,
                iteration=iteration,
                total_iterations=total_iterations,
                template_id=template_id
            )

        # 调试日志：记录提示词生成是否成功
        logger.debug(f"评审提示词生成成功，模板ID: {template_id}")

        return prompt
    except Exception as e:
        # 如果配置化提示词失败，回退到原始硬编码提示词
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"使用配置化提示词失败，回退到硬编码提示词: {e}")

        return _build_reviewer_prompt_fallback(
            context, current_draft, iteration, total_iterations, template_info
        )


def _build_reviewer_prompt_fallback(
    context: str,
    current_draft: str,
    iteration: int,
    total_iterations: int,
    template_info: Optional[Dict[str, Any]] = None,
) -> str:
    """硬编码提示词回退方案"""
    parts = []
    parts.append("你现在扮演一名资深专利代理人 / 合规审查专家。")
    parts.append("任务：对下面的专利草案进行严格审查，找出所有可能的合规风险、缺陷和可改进之处，并给出条理清晰的修改建议。")
    parts.append("")
    parts.append("审查重点包括但不限于：")
    parts.append("- 是否充分体现并保护核心创新点；")
    parts.append("- 权利要求书是否具备新颖性、创造性和实用性，是否存在过窄或过宽的问题；")
    parts.append("- 是否存在模糊、主观或不清楚的表述；")
    parts.append("- 是否有与背景技术、实施例不一致的地方；")
    parts.append("- 图表描述是否清晰，与文字描述是否一致；")
    parts.append("- 是否有明显的专利法或实务上的违反之处；")

    parts.append("- 文档结构是否完整，章节是否清晰；")
    parts.append("")
    parts.append(f"这是第 {iteration}/{total_iterations} 轮审查。")
    parts.append("")
    parts.append("【技术背景与创新点上下文】")
    parts.append(context)
    parts.append("")
    parts.append("【当前专利草案】")
    parts.append(current_draft)
    parts.append("")
    parts.append(
        "请以 Markdown 输出评审结果，包含以下部分：概览评语、问题清单（分条列出，每条包括问题描述和修改建议）、总体风险评估。"
        "不要重写专利全文，只给出评审和修改建议。"
    )

    return "\n".join(parts)


def ensure_output_dir() -> str:
    out_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def build_output_filename(base_name: Optional[str]) -> str:
    out_dir = ensure_output_dir()
    safe_base = (base_name or "patent").strip() or "patent"
    ts = datetime.utcnow().isoformat().replace(":", "-").replace(".", "-")
    return os.path.join(out_dir, f"{safe_base}-{ts}.md")


def run_patent_iteration(
    context: str,
    iterations: int,
    base_name: Optional[str],
    progress_callback: Optional[callable] = None,
    template_id: Optional[str] = None,
    use_template: bool = True,
    idea_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    运行专利生成迭代流程

    Args:
        context: 技术背景上下文
        iterations: 迭代次数
        base_name: 输出文件名前缀
        progress_callback: 进度回调函数 (progress: int, message: str) -> None
        template_id: 模板ID，如果为None则使用默认模板
        idea_text: 用户输入的创意文本（用于创意模式下的 <idea_text> 标记替换）
        use_template: 是否使用模板生成DOCX文档

    Returns:
        包含生成结果的字典
    """
    total = max(1, int(iterations or 1))
    draft: Optional[str] = None
    review: Optional[str] = None

    # 初始化模板相关变量
    selected_template_id: Optional[str] = template_id
    template_info: Optional[Dict[str, Any]] = None
    template_analysis: Optional[Dict[str, Any]] = None

    # 创建数据库记录
    try:
        conversation_db = get_conversation_db()
        task_id = conversation_db.create_task(
            title=f"专利生成任务 - {base_name or '未命名'}",
            context=context,
            iterations=total,
            base_name=base_name
        )
        logger.info(f"创建专利生成任务: {task_id}")
    except Exception as e:
        logger.warning(f"创建数据库任务失败，继续执行: {e}")
        task_id = None

    def update_progress(progress: int, message: str) -> None:
        """更新进度"""
        if progress_callback:
            progress_callback(progress, message)

    update_progress(5, f"开始专利生成流程，共 {total} 轮迭代")

    # 预加载模板信息
    if use_template:
        try:
            template_manager = get_template_manager()

            # 确定使用的模板
            if not selected_template_id:
                default_template = template_manager.get_default_template()
                if default_template:
                    selected_template_id = default_template['id']

            # 获取模板详细信息和分析结果
            if selected_template_id:
                template_info = template_manager.get_template_info(selected_template_id)
                if template_info:
                    update_progress(6, f"已选择模板: {template_info['name']}")

                    # 获取模板分析结果（异步触发分析）
                    try:
                        template_analysis = template_manager.get_template_analysis_summary(selected_template_id)
                        if template_analysis:
                            complexity_score = template_analysis.get('complexity_score', 0)
                            update_progress(7, f"模板复杂度: {complexity_score:.2f}, 质量评分: {template_analysis.get('quality_score', 0):.2f}")
                    except Exception as e:
                        logger.warning(f"模板分析失败: {e}")
                else:
                    update_progress(6, "选定的模板无效或不存在")
                    use_template = False
            else:
                update_progress(6, "未找到可用模板，将不使用模板")
                use_template = False
        except Exception as e:
            logger.warning(f"模板加载失败: {e}")
            update_progress(6, "模板加载失败，将不使用模板")
            use_template = False

    try:
        for i in range(1, total + 1):
            # 计算当前轮次的进度范围
            base_progress = (i - 1) * (90 / total)  # 90% 用于迭代，10% 用于文件保存
            writer_progress = base_progress + (45 / total)  # 每轮中撰写占45%
            reviewer_progress = base_progress + (85 / total)  # 每轮中评审占40%

            update_progress(base_progress, f"第 {i}/{total} 轮：准备撰写阶段")

            # 撰写/修改阶段 - 根据轮次选择不同角色
            logger.info(f"🔧 第 {i}/{total} 轮：开始准备{ '撰写者' if i == 1 else '修改者' }提示词")
            simple_prompt_engine = get_simple_prompt_engine()
            logger.info(f"✅ 已获取SimplePromptEngine实例")

            if i == 1:
                # 第一轮：使用撰写者
                update_progress(base_progress, f"第 {i}/{total} 轮：撰写者创建初始专利草案")
                prompt_method = simple_prompt_engine.get_writer_prompt
                role_name = 'writer'
                role_display = '撰写者'
                logger.info(f"📝 第 {i} 轮：使用撰写者角色")
            else:
                # 第二轮及以后：使用修改者
                update_progress(base_progress, f"第 {i}/{total} 轮：修改者优化专利草案")
                prompt_method = simple_prompt_engine.get_modifier_prompt
                role_name = 'modifier'
                role_display = '修改者'
                logger.info(f"✏️ 第 {i} 轮：使用修改者角色")

            # 获取对应的提示词
            logger.info(f"🚀 开始调用 {role_display} 提示词方法")
            logger.info(f"传递参数检查: context长度={len(context) if context else 0}, idea_text存在={bool(idea_text)}")
            if idea_text:
                logger.info(f"idea_text长度: {len(idea_text)}")

            if role_name == 'writer':
                logger.info(f"📋 调用 get_writer_prompt 方法...")
                current_prompt = prompt_method(
                    context=context,
                    previous_draft=draft,
                    previous_review=review,
                    iteration=i,
                    total_iterations=total,
                    idea_text=idea_text  # 传递创意文本参数
                )
            else:  # modifier
                logger.info(f"📋 调用 get_modifier_prompt 方法...")
                current_prompt = prompt_method(
                    context=context,
                    previous_draft=draft,
                    previous_review=review,
                    iteration=i,
                    total_iterations=total,
                    idea_text=idea_text  # 传递创意文本参数
                )

            logger.info(f"✅ {role_display} 提示词获取完成，长度: {len(current_prompt)} 字符")
            logger.info(f"提示词开头预览: {current_prompt[:200]}...")

            update_progress(writer_progress - 5, f"第 {i}/{total} 轮：调用 LLM ({role_display})")
            draft = call_llm(current_prompt)
            update_progress(writer_progress, f"第 {i}/{total} 轮：{role_display}工作完成")

            # 记录对话到数据库
            if task_id and conversation_db:
                try:
                    conversation_db.add_conversation_round(
                        task_id=task_id,
                        round_number=i,
                        role=role_name,
                        prompt=current_prompt,
                        response=draft
                    )
                except Exception as e:
                    logger.warning(f"记录{role_display}对话失败: {e}")

            # 评审阶段 - 使用新的简单提示词引擎
            reviewer_prompt = simple_prompt_engine.get_reviewer_prompt(
                context=context,
                current_draft=draft,
                iteration=i,
                total_iterations=total
            )
            update_progress(reviewer_progress - 5, f"第 {i}/{total} 轮：调用 LLM 进行评审")
            review = call_llm(reviewer_prompt)
            update_progress(reviewer_progress, f"第 {i}/{total} 轮：评审完成")

            # 记录审批者对话到数据库
            if task_id and conversation_db:
                try:
                    conversation_db.add_conversation_round(
                        task_id=task_id,
                        round_number=i,
                        role='reviewer',
                        prompt=reviewer_prompt,
                        response=review
                    )
                except Exception as e:
                    logger.warning(f"记录审批者对话失败: {e}")

    except Exception as e:
        update_progress(95, f"处理过程中出现错误: {str(e)}")
        raise

    update_progress(95, "正在生成最终文档并保存文件")

    # 生成最终文档
    final_draft = draft or ""
    meta = "\n".join(
        [
            "<!--",
            "  Generated by multi-round patent generator",
            f"  Iterations: {total}",
            f"  Generated at: {datetime.utcnow().isoformat()}",
            "-->",
            "",
        ]
    )
    final_markdown = meta + final_draft

    # 保存文件
    output_path = build_output_filename(base_name)
    docx_path = None

    try:
        # 保存 Markdown 文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_markdown)
        update_progress(95, f"Markdown 文件已保存到: {output_path}")

        # 如果启用模板功能，生成 DOCX 文件
        if use_template:
            try:
                # 获取模板管理器
                template_manager = get_template_manager()

                # 确定使用的模板
                selected_template_id = template_id
                if not selected_template_id:
                    default_template = template_manager.get_default_template()
                    if default_template:
                        selected_template_id = default_template['id']

                if selected_template_id:
                    # 获取模板信息
                    template_info = template_manager.get_template_info(selected_template_id)
                    if template_info and template_info['is_valid']:
                        # 生成 DOCX 文件路径
                        output_dir = os.path.dirname(output_path)
                        base_name_without_ext = os.path.splitext(os.path.basename(output_path))[0]
                        docx_filename = f"{base_name_without_ext}.docx"
                        docx_path = os.path.join(output_dir, docx_filename)

                        update_progress(96, f"正在使用模板生成 DOCX 文档...")

                        # 生成 DOCX 文档
                        success = generate_patent_docx(
                            markdown_content=final_markdown,
                            template_path=template_info['file_path'],
                            output_path=docx_path
                        )

                        if success:
                            update_progress(100, f"专利生成完成，DOCX 文件已保存到: {docx_path}")
                        else:
                            update_progress(100, f"DOCX 生成失败，使用 Markdown 文件: {output_path}")
                    else:
                        update_progress(100, f"选定的模板无效，使用 Markdown 文件: {output_path}")
                else:
                    update_progress(100, f"未找到可用模板，使用 Markdown 文件: {output_path}")

            except Exception as e:
                logger.warning(f"生成 DOCX 文档失败: {e}")
                update_progress(100, f"DOCX 生成失败，使用 Markdown 文件: {output_path}")

    except Exception as e:
        update_progress(95, f"文件保存失败: {str(e)}")
        raise

    # 更新任务状态为完成
    if task_id and conversation_db:
        try:
            conversation_db.update_task_status(task_id, "completed")
        except Exception as e:
            logger.warning(f"更新任务状态失败: {e}")

    result = {
        "output_path": output_path,
        "final_markdown": final_markdown,
        "last_review": review,
        "iterations": total,
    }

    # 添加 DOCX 相关信息
    if docx_path:
        result["docx_path"] = docx_path
        result["template_used"] = True
        result["template_id"] = selected_template_id

    # 添加任务ID用于前端显示对话历史
    if task_id:
        result["task_id"] = task_id

    return result


def _build_prompt_from_template(
    template: str,
    context: str,
    previous_draft: Optional[str] = None,
    previous_review: Optional[str] = None,
    current_draft: Optional[str] = None,
    iteration: int = 1,
    total_iterations: int = 1,
    strict_mode: bool = False,
    idea_text: Optional[str] = None
) -> str:
    """
    从模板构建提示词，支持变量替换

    Args:
        template: 提示词模板
        context: 技术背景和创新点上下文
        previous_draft: 上一版专利草案
        previous_review: 上一轮评审意见
        current_draft: 当前轮次的专利草案（用于动态替换）
        iteration: 当前迭代轮次
        total_iterations: 总迭代轮次
        strict_mode: 严格执行模式，为True时严格按照用户输入执行，不添加任何额外内容
        idea_text: 用户输入的创意文本（用于创意模式下的 <idea_text> 标记替换）

    Returns:
        构建完成的提示词字符串
    """
    try:
        prompt = template

        # 严格模式下的特殊处理：支持动态替换
        if strict_mode:
            has_dynamic_markers = False

            # 支持修改者专用标记 <previous_output>
            if "<previous_output>" in prompt:
                has_dynamic_markers = True
                logger.info("检测到<previous_output>标记，启用动态内容替换")
                if previous_draft:
                    original_length = len(prompt)
                    prompt = prompt.replace("<previous_output>", previous_draft)
                    logger.info(f"成功替换<previous_output>标记，替换内容长度: {len(previous_draft)} 字符")
                    logger.info(f"替换后提示词总长度: {len(prompt)} 字符（原长度: {original_length}）")
                else:
                    logger.warning("检测到<previous_output>标记但没有previous_draft内容，保持原标记")
                    prompt = prompt.replace("<previous_output>", "[上轮专利生成结果]")

            # 支持修改者专用标记 <previous_review>
            if "<previous_review>" in prompt:
                has_dynamic_markers = True
                logger.info("检测到<previous_review>标记，启用动态内容替换")
                if previous_review:
                    original_length = len(prompt)
                    prompt = prompt.replace("<previous_review>", previous_review)
                    logger.info(f"成功替换<previous_review>标记，替换内容长度: {len(previous_review)} 字符")
                    logger.info(f"替换后提示词总长度: {len(prompt)} 字符（原长度: {original_length}）")
                else:
                    logger.warning("检测到<previous_review>标记但没有previous_review内容，保持原标记")
                    prompt = prompt.replace("<previous_review>", "[上轮审批评审意见]")

            # 向后兼容：继续支持 </text> 标记
            if "</text>" in prompt:
                has_dynamic_markers = True
                logger.info("检测到</text>标记，启用动态内容替换")
                if current_draft:
                    original_length = len(prompt)
                    prompt = prompt.replace("</text>", current_draft)
                    logger.info(f"成功替换</text>标记，替换内容长度: {len(current_draft)} 字符")
                    logger.info(f"替换后提示词总长度: {len(prompt)} 字符（原长度: {original_length}）")
                else:
                    logger.warning("检测到</text>标记但没有current_draft内容，保持原标记")
                    prompt = prompt.replace("</text>", "[当前专利草案内容]")
                    logger.info("已将</text>标记替换为提示文本")

            # 支持创意模式专用标记 <idea_text>
            if "<idea_text>" in prompt:
                has_dynamic_markers = True
                logger.info("检测到<idea_text>标记，启用创意文本替换")
                if idea_text:
                    original_length = len(prompt)
                    prompt = prompt.replace("<idea_text>", idea_text)
                    logger.info(f"成功替换<idea_text>标记，替换内容长度: {len(idea_text)} 字符")
                    logger.info(f"替换后提示词总长度: {len(prompt)} 字符（原长度: {original_length}）")
                else:
                    logger.warning("检测到<idea_text>标记但没有创意文本内容")
                    prompt = prompt.replace("<idea_text>", "[用户创意内容]")

            # 如果没有动态标记，直接返回原提示词
            if not has_dynamic_markers:
                logger.info(f"严格模式已启用：直接使用用户输入的提示词（无动态标记）")
                logger.info(f"严格模式提示词长度: {len(prompt)} 字符")
                logger.info(f"严格模式提示词开头: {prompt[:100]}...")
                logger.info(f"严格模式提示词结尾: {prompt[-50:] if len(prompt) > 50 else prompt}")

            # 严格模式处理完成，直接返回结果
            logger.debug(f"严格模式处理完成，提示词总长度: {len(prompt)} 字符")
            return prompt

        # 非严格模式正常处理流程

        # 正常模式：进行变量替换和内容增强
        # 替换基本变量
        replacements = {
            "{{context}}": context or "",
            "{{previous_draft}}": previous_draft or "",
            "{{previous_review}}": previous_review or "",
            "{{iteration}}": str(iteration),
            "{{total_iterations}}": str(total_iterations),
            "{{current_iteration}}": str(iteration),
            "{{total_rounds}}": str(total_iterations)
        }

        # 执行替换
        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, value)

        # 处理 <idea_text> 标记（非严格模式）
        if "<idea_text>" in prompt:
            if idea_text:
                original_length = len(prompt)
                prompt = prompt.replace("<idea_text>", idea_text)
                logger.info(f"非严格模式：成功替换<idea_text>标记，替换内容长度: {len(idea_text)} 字符")
            else:
                logger.warning("非严格模式：检测到<idea_text>标记但没有创意文本内容")
                prompt = prompt.replace("<idea_text>", "[用户创意内容]")

        # 添加历史内容章节（如果需要且用户模板中包含相应占位符）
        if previous_draft and "{{tech_context}}" in prompt:
            # 如果模板中有技术上下文占位符，替换为用户提供的上下文
            prompt = prompt.replace("{{tech_context}}", context or "")

        # 添加迭代信息
        if "这是第" not in prompt and f"第 {iteration}/{total_iterations} 轮" not in prompt:
            prompt += f"\n\n这是第 {iteration}/{total_iterations} 轮"

        logger.debug(f"模板变量替换完成，提示词长度: {len(prompt)} 字符")
        return prompt

    except Exception as e:
        logger.error(f"模板变量替换失败: {e}")
        # 如果替换失败，返回原始模板
        return template


def get_effective_writer_prompt(
    context: str,
    previous_draft: Optional[str],
    previous_review: Optional[str],
    iteration: int,
    total_iterations: int,
    template_id: Optional[str] = None,
    idea_text: Optional[str] = None
) -> str:
    """
    获取有效的撰写者提示词，优先使用用户自定义

    Args:
        context: 技术背景和创新点上下文
        previous_draft: 上一版专利草案
        previous_review: 上一轮评审意见
        iteration: 当前迭代轮次
        total_iterations: 总迭代轮次
        template_id: 模板ID

    Returns:
        有效的撰写者提示词
    """
    try:
        # 优先检查用户自定义提示词
        user_prompt_manager = get_user_prompt_manager()
        user_custom_prompt = user_prompt_manager.get_user_prompt('writer')

        # 添加详细的调试日志
        logger.info(f"检查用户自定义撰写者提示词...")
        logger.info(f"用户提示词存在: {bool(user_custom_prompt)}")
        if user_custom_prompt:
            logger.info(f"用户提示词长度: {len(user_custom_prompt)} 字符")
            logger.info(f"用户提示词开头: {user_custom_prompt[:50]}...")
            logger.info(f"用户提示词是否为空: {not user_custom_prompt.strip()}")

        if user_custom_prompt and user_custom_prompt.strip():
            logger.info("使用用户自定义撰写者提示词（严格模式）")
            return _build_prompt_from_template(
                user_custom_prompt,
                context=context,
                previous_draft=previous_draft,
                previous_review=previous_review,
                iteration=iteration,
                total_iterations=total_iterations,
                strict_mode=True,
                idea_text=idea_text
            )
        else:
            logger.debug("用户未设置自定义撰写者提示词，使用系统默认")
            return get_prompt(
                PromptKeys.PATENT_WRITER,
                context=context,
                previous_draft=previous_draft,
                previous_review=previous_review,
                iteration=iteration,
                total_iterations=total_iterations,
                template_id=template_id,
                idea_text=idea_text
            )

    except Exception as e:
        logger.error(f"获取撰写者提示词失败: {e}")
        # 回退到硬编码提示词
        return _build_writer_prompt_fallback(
            context, previous_draft, previous_review, iteration, total_iterations
        )


def get_effective_reviewer_prompt(
    context: str,
    current_draft: str,
    iteration: int,
    total_iterations: int,
    template_id: Optional[str] = None
) -> str:
    """
    获取有效的审核者提示词，优先使用用户自定义

    Args:
        context: 技术背景和创新点上下文
        current_draft: 当前专利草案
        iteration: 当前迭代轮次
        total_iterations: 总迭代轮次
        template_id: 模板ID

    Returns:
        有效的审核者提示词
    """
    try:
        # 优先检查用户自定义提示词
        user_prompt_manager = get_user_prompt_manager()
        user_custom_prompt = user_prompt_manager.get_user_prompt('reviewer')

        # 添加详细的调试日志
        logger.info(f"检查用户自定义审核者提示词...")
        logger.info(f"用户提示词存在: {bool(user_custom_prompt)}")
        if user_custom_prompt:
            logger.info(f"用户提示词长度: {len(user_custom_prompt)} 字符")
            logger.info(f"用户提示词开头: {user_custom_prompt[:50]}...")
            logger.info(f"用户提示词是否为空: {not user_custom_prompt.strip()}")

        if user_custom_prompt and user_custom_prompt.strip():
            logger.info("使用用户自定义审核者提示词（严格模式）")
            return _build_prompt_from_template(
                user_custom_prompt,
                context=context,
                current_draft=current_draft,
                iteration=iteration,
                total_iterations=total_iterations,
                strict_mode=True
            )
        else:
            logger.debug("用户未设置自定义审核者提示词，使用系统默认")
            return get_prompt(
                PromptKeys.PATENT_REVIEWER,
                context=context,
                current_draft=current_draft,
                iteration=iteration,
                total_iterations=total_iterations,
                template_id=template_id
            )

    except Exception as e:
        logger.error(f"获取审核者提示词失败: {e}")
        # 回退到硬编码提示词
        return _build_reviewer_prompt_fallback(
            context, current_draft, iteration, total_iterations
        )


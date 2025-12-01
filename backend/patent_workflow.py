import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from llm_client import call_llm
from prompt_manager import get_prompt, PromptKeys
from template_manager import get_template_manager
from docx_generator import generate_patent_docx, validate_patent_template
from conversation_db import get_conversation_db

logger = logging.getLogger(__name__)


def build_writer_prompt(
    context: str,
    previous_draft: Optional[str],
    previous_review: Optional[str],
    iteration: int,
    total_iterations: int,
    template_id: Optional[str] = None,
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

        # 使用增强的提示词管理器获取配置化提示词
        prompt = get_prompt(
            PromptKeys.PATENT_WRITER,
            context=context,
            previous_draft=previous_draft,
            previous_review=previous_review,
            iteration=iteration,
            total_iterations=total_iterations,
            template_id=template_id
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
        # 构建模板信息文本（保持向后兼容）
        template_info_text = ""
        if template_info:
            template_info_text = f"\n【模板信息】\n使用模板: {template_info.get('name', '未知模板')}\n模板ID: {template_info.get('id', '未知')}\n"

        # 调试日志：记录评审请求的模板ID
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"构建评审提示词，模板ID: {template_id}")

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
) -> Dict[str, Any]:
    """
    运行专利生成迭代流程

    Args:
        context: 技术背景上下文
        iterations: 迭代次数
        base_name: 输出文件名前缀
        progress_callback: 进度回调函数 (progress: int, message: str) -> None
        template_id: 模板ID，如果为None则使用默认模板
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

            # 撰写阶段
            writer_prompt = build_writer_prompt(
                context=context,
                previous_draft=draft,
                previous_review=review,
                iteration=i,
                total_iterations=total,
                template_id=selected_template_id
            )
            update_progress(writer_progress - 5, f"第 {i}/{total} 轮：调用 LLM 撰写专利")
            draft = call_llm(writer_prompt)
            update_progress(writer_progress, f"第 {i}/{total} 轮：专利撰写完成")

            # 记录撰写者对话到数据库
            if task_id and conversation_db:
                try:
                    conversation_db.add_conversation_round(
                        task_id=task_id,
                        round_number=i,
                        role='writer',
                        prompt=writer_prompt,
                        response=draft
                    )
                except Exception as e:
                    logger.warning(f"记录撰写者对话失败: {e}")

            # 评审阶段
            reviewer_prompt = build_reviewer_prompt(
                context=context,
                current_draft=draft,
                iteration=i,
                total_iterations=total,
                template_info=template_info,
                template_id=selected_template_id
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


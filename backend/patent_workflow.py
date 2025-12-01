import os
from datetime import datetime
from typing import Optional, Dict, Any

from llm_client import call_llm


def build_writer_prompt(
    context: str,
    previous_draft: Optional[str],
    previous_review: Optional[str],
    iteration: int,
    total_iterations: int,
) -> str:
    parts = []
    parts.append("你现在扮演一名资深的中国发明专利撰写专家。")
    parts.append("目标：基于给定的技术背景和创新点，撰写一份结构完整、符合中国专利法和实务规范的发明专利草案。")
    parts.append("")
    parts.append("整体要求：")
    parts.append("- 使用 Markdown 编写完整专利文档；")
    parts.append("- 章节建议包括但不限于：标题、技术领域、背景技术、发明内容、附图说明、具体实施方式、权利要求书、摘要；")
    parts.append("- 所有图示必须使用 mermaid 语法的代码块，例如：")
    parts.append("```mermaid")
    parts.append("graph TD")
    parts.append("  A[模块A] --> B[模块B]")
    parts.append("```")
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
) -> str:
    parts = []
    parts.append("你现在扮演一名资深专利代理人 / 合规审查专家。")
    parts.append("任务：对下面的专利草案进行严格审查，找出所有可能的合规风险、缺陷和可改进之处，并给出条理清晰的修改建议。")
    parts.append("")
    parts.append("审查重点包括但不限于：")
    parts.append("- 是否充分体现并保护核心创新点；")
    parts.append("- 权利要求书是否具备新颖性、创造性和实用性，是否存在过窄或过宽的问题；")
    parts.append("- 是否存在模糊、主观或不清楚的表述；")
    parts.append("- 是否有与背景技术、实施例不一致的地方；")
    parts.append("- mermaid 图是否与文字描述一致，是否存在遗漏或不清晰的环节；")
    parts.append("- 是否有明显的专利法或实务上的违反之处。")
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
) -> Dict[str, Any]:
    """
    运行专利生成迭代流程

    Args:
        context: 技术背景上下文
        iterations: 迭代次数
        base_name: 输出文件名前缀
        progress_callback: 进度回调函数 (progress: int, message: str) -> None

    Returns:
        包含生成结果的字典
    """
    total = max(1, int(iterations or 1))
    draft: Optional[str] = None
    review: Optional[str] = None

    def update_progress(progress: int, message: str) -> None:
        """更新进度"""
        if progress_callback:
            progress_callback(progress, message)

    update_progress(5, f"开始专利生成流程，共 {total} 轮迭代")

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
            )
            update_progress(writer_progress - 5, f"第 {i}/{total} 轮：调用 LLM 撰写专利")
            draft = call_llm(writer_prompt)
            update_progress(writer_progress, f"第 {i}/{total} 轮：专利撰写完成")

            # 评审阶段
            reviewer_prompt = build_reviewer_prompt(
                context=context,
                current_draft=draft,
                iteration=i,
                total_iterations=total,
            )
            update_progress(reviewer_progress - 5, f"第 {i}/{total} 轮：调用 LLM 进行评审")
            review = call_llm(reviewer_prompt)
            update_progress(reviewer_progress, f"第 {i}/{total} 轮：评审完成")

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
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_markdown)
        update_progress(100, f"专利生成完成，文件已保存到: {output_path}")
    except Exception as e:
        update_progress(95, f"文件保存失败: {str(e)}")
        raise

    return {
        "output_path": output_path,
        "final_markdown": final_markdown,
        "last_review": review,
        "iterations": total,
    }


import os
import gc
import logging
from typing import List, Iterator, Generator, Optional
from pathlib import Path
import mmap
from prompt_manager import get_prompt, PromptKeys

# 配置日志
logger = logging.getLogger(__name__)

# 配置常量
DEFAULT_EXTENSIONS = [
    ".js", ".jsx", ".ts", ".tsx", ".py", ".java", ".cs", ".go", ".rs",
    ".cpp", ".c", ".rb", ".php", ".swift", ".kt", ".scala", ".dart",
    ".sh", ".bash", ".zsh", ".ps1", ".bat", ".sql", ".html", ".css",
    ".scss", ".sass", ".less", ".vue", ".svelte"
]

IGNORE_DIRS = {
    "node_modules", ".git", "dist", "build", "out", ".next", ".turbo",
    "coverage", "__pycache__", ".venv", "venv", "env", ".env", ".idea",
    ".vscode", ".eclipse", "target", "bin", "obj", "Debug", "Release",
    "packages", "vendor", "cache", "temp", "tmp", ".tmp"
}

# 性能配置
MAX_FILE_SIZE = 1024 * 1024  # 1MB
MAX_CONTENT_LENGTH = 50 * 1024  # 50KB per file
MAX_FILES = 200
MAX_LINES = 80


class FileAnalysisResult:
    """文件分析结果"""

    def __init__(self, rel_path: str, content: Optional[str], error: Optional[str] = None):
        self.rel_path = rel_path
        self.content = content
        self.error = error
        self.size = len(content) if content else 0


def _extract_technical_concepts(code_content: str, file_path: str) -> str:
    """
    从代码内容中提取技术概念，转换为适合专利申请的描述

    Args:
        code_content: 代码内容
        file_path: 文件路径

    Returns:
        技术概念描述
    """
    try:
        lines = code_content.split('\n')
        concepts = []

        # 分析文件类型
        _, ext = os.path.splitext(file_path)
        file_type = "程序文件"
        if ext == '.py':
            file_type = "Python程序"
        elif ext in ['.js', '.jsx']:
            file_type = "JavaScript程序"
        elif ext in ['.ts', '.tsx']:
            file_type = "TypeScript程序"
        elif ext in ['.java']:
            file_type = "Java程序"
        elif ext in ['.cpp', '.c']:
            file_type = "C/C++程序"
        elif ext in ['.go']:
            file_type = "Go程序"
        elif ext in ['.rs']:
            file_type = "Rust程序"

        concepts.append(f"技术组件类型: {file_type}")

        # 提取类/函数定义（简化版本）
        for line in lines[:20]:  # 只分析前20行，避免过多细节
            line = line.strip()

            # Python类和函数
            if line.startswith('class '):
                class_name = line.replace('class ', '').split('(')[0].split(':')[0].strip()
                if class_name:
                    concepts.append(f"核心组件: {class_name}")
            elif line.startswith('def '):
                func_name = line.replace('def ', '').split('(')[0].strip()
                if func_name and not func_name.startswith('_'):
                    concepts.append(f"功能模块: {func_name}")

            # JavaScript函数和类
            elif 'function ' in line and line.startswith('function'):
                func_name = line.replace('function ', '').split('(')[0].strip()
                if func_name:
                    concepts.append(f"功能模块: {func_name}")
            elif 'class ' in line and 'extends' in line:
                class_name = line.strip().split('class ')[1].split(' ')[0]
                if class_name:
                    concepts.append(f"核心组件: {class_name}")

            # 通用识别 - 检查常见的技术关键词
            elif any(keyword in line.lower() for keyword in ['api', 'interface', 'service', 'controller', 'handler']):
                if 'api' in line.lower():
                    concepts.append("API接口组件")
                elif 'service' in line.lower():
                    concepts.append("服务组件")
                elif 'controller' in line.lower() or 'handler' in line.lower():
                    concepts.append("控制器组件")

        # 如果没有提取到具体概念，提供通用描述
        if len(concepts) <= 1:
            concepts.append(f"技术实现模块")

        return "、".join(concepts[:3]) + "等"

    except Exception as e:
        logger.warning(f"技术概念提取失败: {e}")
        return f"程序化技术实现模块"


def is_code_file(path: str) -> bool:
    """检查是否为代码文件"""
    try:
        _, ext = os.path.splitext(path)
        return ext.lower() in DEFAULT_EXTENSIONS
    except (ValueError, AttributeError):
        return False


def is_safe_file(path: str) -> bool:
    """检查文件是否安全可读"""
    try:
        # 检查文件是否存在
        if not os.path.isfile(path):
            return False

        # 检查文件大小
        file_size = os.path.getsize(path)
        if file_size > MAX_FILE_SIZE:
            logger.debug(f"文件过大，跳过: {path} ({file_size} bytes)")
            return False

        # 检查文件权限
        if not os.access(path, os.R_OK):
            logger.debug(f"文件无读取权限: {path}")
            return False

        return True
    except (OSError, PermissionError) as e:
        logger.debug(f"文件安全检查失败 {path}: {str(e)}")
        return False


def walk_directory_safe(root_dir: str, max_files: int = MAX_FILES) -> Iterator[str]:
    """
    安全地遍历目录，生成文件路径迭代器

    Args:
        root_dir: 根目录
        max_files: 最大文件数

    Yields:
        文件路径
    """
    try:
        root_path = Path(root_dir).resolve()

        if not root_path.exists():
            logger.error(f"目录不存在: {root_dir}")
            return

        if not root_path.is_dir():
            logger.error(f"路径不是目录: {root_dir}")
            return

        file_count = 0

        # 使用 os.walk 进行遍历，但增加安全检查
        for current_root, dirs, files in os.walk(root_dir):
            # 过滤忽略的目录（原地修改dirs列表）
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            # 检查当前目录是否可访问
            try:
                current_path = Path(current_root)
                if not current_path.is_dir() or not os.access(current_root, os.R_OK):
                    continue
            except (OSError, PermissionError):
                continue

            for filename in files:
                if file_count >= max_files:
                    logger.info(f"达到最大文件数限制 {max_files}，停止扫描")
                    return

                file_path = os.path.join(current_root, filename)

                # 安全检查
                if is_safe_file(file_path) and is_code_file(file_path):
                    file_count += 1
                    yield file_path

    except Exception as e:
        logger.error(f"目录遍历失败: {str(e)}")
        return


def read_file_content_safe(file_path: str, max_lines: int = MAX_LINES, max_length: int = MAX_CONTENT_LENGTH) -> Optional[str]:
    """
    安全地读取文件内容，支持内存优化

    Args:
        file_path: 文件路径
        max_lines: 最大行数
        max_length: 最大内容长度

    Returns:
        文件内容或None
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            # 对于大文件使用内存映射
            file_size = os.path.getsize(file_path)

            if file_size > 10240:  # 10KB以上使用缓冲读取
                lines = []
                total_length = 0

                for i, line in enumerate(file):
                    if i >= max_lines or total_length >= max_length:
                        break

                    line_content = line.rstrip('\n\r')
                    if total_length + len(line_content) > max_length:
                        # 截断最后一行以保持在长度限制内
                        remaining = max_length - total_length
                        if remaining > 0:
                            lines.append(line_content[:remaining])
                        break

                    lines.append(line_content)
                    total_length += len(line_content) + 1  # +1 for newline

                return '\n'.join(lines)
            else:
                # 小文件直接读取
                content = file.read(max_length + 1)  # 多读一个字符来检查是否超限
                if len(content) > max_length:
                    content = content[:max_length]

                lines = content.splitlines(True)
                result_lines = [line.rstrip('\n\r') for line in lines[:max_lines]]
                return '\n'.join(result_lines)

    except (OSError, IOError, UnicodeDecodeError, PermissionError) as e:
        logger.debug(f"读取文件失败 {file_path}: {str(e)}")
        return None


def analyze_file(file_path: str, root_dir: str) -> FileAnalysisResult:
    """
    分析单个文件

    Args:
        file_path: 文件路径
        root_dir: 根目录

    Returns:
        文件分析结果
    """
    try:
        rel_path = os.path.relpath(file_path, root_dir)

        # 读取文件内容
        content = read_file_content_safe(file_path)

        if content is None:
            return FileAnalysisResult(rel_path, None, "文件读取失败")

        if not content.strip():
            return FileAnalysisResult(rel_path, None, "文件为空")

        return FileAnalysisResult(rel_path, content)

    except Exception as e:
        logger.error(f"分析文件失败 {file_path}: {str(e)}")
        # 尝试获取相对路径
        try:
            rel_path = os.path.relpath(file_path, root_dir)
        except:
            rel_path = os.path.basename(file_path)

        return FileAnalysisResult(rel_path, None, f"分析失败: {str(e)}")


def build_code_innovation_context_streaming(root_dir: str, progress_callback: Optional[callable] = None) -> Generator[str, None, None]:
    """
    流式构建代码创新上下文，支持大项目分析

    Args:
        root_dir: 根目录
        progress_callback: 进度回调函数

    Yields:
        上下文内容片段
    """
    try:
        abs_root = os.path.abspath(root_dir or ".")
        logger.info(f"开始分析代码目录: {abs_root}")

        if progress_callback:
            progress_callback(0, "开始扫描文件...")

        # 第一阶段：扫描文件
        file_paths = list(walk_directory_safe(abs_root))
        total_files = len(file_paths)

        if total_files == 0:
            yield "# Codebase Overview\n\n未找到可分析的代码文件。\n"
            return

        # 生成头部信息
        header_lines = [
            "# Codebase Overview",
            f"Root directory: {abs_root}",
            f"Total sampled files: {total_files}",
            "",
        ]

        for line in header_lines:
            yield line

        # 第二阶段：分析文件
        processed_files = 0
        successful_files = 0
        total_content_size = 0

        for i, file_path in enumerate(file_paths):
            try:
                # 更新进度
                if progress_callback:
                    progress = 10 + (i * 70 // total_files)  # 10-80% 的进度
                    progress_callback(progress, f"分析文件 {i+1}/{total_files}")

                # 分析文件
                result = analyze_file(file_path, abs_root)
                processed_files += 1

                if result.content:
                    successful_files += 1
                    total_content_size += result.size

                    # 生成文件内容
                    yield "---"
                    yield f"FILE: {result.rel_path}"
                    yield ""
                    yield "TECHNICAL_CONCEPT:"
                    # 将代码内容转换为概念性描述，避免直接输出代码
                    concept_description = _extract_technical_concepts(result.content, result.rel_path)
                    yield concept_description
                    yield ""
                else:
                    # 文件读取失败
                    yield "---"
                    yield f"FILE: {result.rel_path}"
                    yield ""
                    yield f"(无法读取文件: {result.error or '未知错误'})"
                    yield ""

                # 定期进行垃圾回收
                if i % 20 == 0:
                    gc.collect()

            except Exception as e:
                logger.error(f"处理文件时出错 {file_path}: {str(e)}")
                continue

        # 生成总结信息
        try:
            # 尝试使用配置化的分析摘要模板
            summary_template = get_prompt(
                PromptKeys.CODE_ANALYZER,
                processed_files=processed_files,
                successful_files=successful_files,
                total_content_size=total_content_size
            )

            # 解析模板并添加指令
            summary_lines = []
            template_lines = summary_template.split('\n')

            for line in template_lines:
                if "{{processed_files}}" in line:
                    line = line.replace("{{processed_files}}", str(processed_files))
                if "{{successful_files}}" in line:
                    line = line.replace("{{successful_files}}", str(successful_files))
                if "{{total_content_size}}" in line:
                    line = line.replace("{{total_content_size}}", str(total_content_size))
                summary_lines.append(line)

            # 添加提取指令
            summary_lines.extend([
                "",
                "Instruction: Based on the overview above, "
                "extract the core technical ideas and potential innovation points "
                "that would be valuable for a patent.",
                ""
            ])

        except Exception as e:
            # 如果配置化提示词失败，回退到原始硬编码摘要
            logger.warning(f"使用配置化代码分析提示词失败，回退到硬编码: {e}")
            summary_lines = [
                "---",
                f"## Analysis Summary",
                f"- 处理文件数: {processed_files}",
                f"- 成功分析: {successful_files}",
                f"- 内容总量: {total_content_size} 字符",
                "",
                "Instruction: Based on the overview above, "
                "extract the core technical ideas and potential innovation points "
                "that would be valuable for a patent.",
                ""
            ]

        # 最终进度更新
        if progress_callback:
            progress_callback(100, f"分析完成，共处理 {processed_files} 个文件")

        for line in summary_lines:
            yield line

        logger.info(f"代码分析完成: {successful_files}/{total_files} 文件成功分析，总内容大小: {total_content_size}")

    except Exception as e:
        logger.error(f"构建代码上下文失败: {str(e)}")
        yield f"错误: 代码分析失败 - {str(e)}"


def build_code_innovation_context(root_dir: str, progress_callback: Optional[callable] = None) -> str:
    """
    构建代码创新上下文（兼容性接口）

    Args:
        root_dir: 根目录
        progress_callback: 进度回调函数

    Returns:
        完整的上下文字符串
    """
    try:
        # 使用流式接口并收集所有内容
        content_parts = []
        for chunk in build_code_innovation_context_streaming(root_dir, progress_callback):
            content_parts.append(chunk)

        return '\n'.join(content_parts)

    except Exception as e:
        logger.error(f"构建代码上下文失败: {str(e)}")
        return f"错误: 代码分析失败 - {str(e)}"


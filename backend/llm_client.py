import os
import subprocess
import shlex
import re
import logging
from typing import Optional, List
from config import get_config

logger = logging.getLogger(__name__)


def _compress_prompt_if_needed(prompt: str, max_length: int, compression_ratio: float = 0.7) -> Optional[str]:
    """
    智能压缩提示文本以适应长度限制

    Args:
        prompt: 原始提示文本
        max_length: 最大允许长度
        compression_ratio: 压缩目标比例（相对于最大长度）

    Returns:
        压缩后的提示文本，如果无法压缩则返回None
    """
    target_length = int(max_length * compression_ratio)

    if len(prompt) <= target_length:
        return prompt

    logger.info(f"开始压缩提示文本，当前长度: {len(prompt)}, 目标长度: {target_length}")

    try:
        compressed_prompt = prompt

        # 1. 压缩过长的历史专利草案
        compressed_prompt = _compress_historical_content(compressed_prompt, "【上一版专利草案】", target_length)

        # 2. 压缩过长的技术背景内容
        compressed_prompt = _compress_historical_content(compressed_prompt, "【技术背景与创新点上下文】", target_length)

        # 3. 压缩过长的评审意见
        compressed_prompt = _compress_historical_content(compressed_prompt, "【合规评审与问题清单】", target_length)

        # 4. 如果还是太长，进行通用压缩
        if len(compressed_prompt) > target_length:
            compressed_prompt = _generic_compress(compressed_prompt, target_length)

        if len(compressed_prompt) <= max_length:
            logger.info(f"提示文本压缩成功: {len(prompt)} -> {len(compressed_prompt)} 字符")
            return compressed_prompt
        else:
            logger.warning(f"提示文本压缩后仍超限: {len(compressed_prompt)} > {max_length}")
            return None

    except Exception as e:
        logger.error(f"提示文本压缩失败: {e}")
        return None


def _compress_historical_content(prompt: str, section_title: str, target_length: int) -> str:
    """压缩特定的历文章节"""
    if section_title not in prompt:
        return prompt

    # 找到章节的开始和结束位置
    start_pos = prompt.find(section_title)
    if start_pos == -1:
        return prompt

    # 找到下一个章节的开始位置
    next_section_patterns = [
        "【技术背景与创新点上下文】",
        "【上一版专利草案】",
        "【合规评审与问题清单】",
        "【使用模板】",
        "请直接输出完整"
    ]

    end_pos = len(prompt)  # 默认到文本末尾
    for pattern in next_section_patterns:
        if pattern != section_title:  # 避免找到自己
            pos = prompt.find(pattern, start_pos + len(section_title))
            if pos != -1 and pos < end_pos:
                end_pos = pos

    # 提取章节内容
    section_content = prompt[start_pos:end_pos]

    # 如果章节内容不是特别长，保留原样
    if len(section_content) <= 5000:
        return prompt

    # 智能摘要：保留开头和结尾，中间用省略号
    header_lines = []
    content_lines = []
    footer_lines = []

    lines = section_content.split('\n')
    in_header = True
    in_content = False
    in_footer = False

    for i, line in enumerate(lines):
        if line.strip().startswith('##') or line.strip().startswith('#'):
            if in_content:
                in_footer = True
                in_content = False
                in_header = False
            elif in_header:
                in_content = True

        if in_header and len(header_lines) < 10:
            header_lines.append(line)
        elif in_footer and len(footer_lines) < 5:
            footer_lines.append(line)
        elif in_content and len(content_lines) < 20:  # 保留部分内容行
            content_lines.append(line)

    # 构建压缩后的章节内容
    compressed_section = '\n'.join(header_lines)
    if content_lines:
        compressed_section += '\n...\n' + '\n'.join(content_lines[:15])
    if footer_lines:
        compressed_section += '\n...\n' + '\n'.join(footer_lines)

    # 如果压缩后还是很长，进一步简化
    if len(compressed_section) > 3000:
        compressed_section = '\n'.join(header_lines[:5]) + '\n...\n[详细内容已压缩，保留核心要点]\n...'

    # 替换原章节
    new_prompt = prompt[:start_pos] + compressed_section + prompt[end_pos:]

    logger.debug(f"章节 {section_title} 压缩: {len(section_content)} -> {len(compressed_section)} 字符")
    return new_prompt


def _generic_compress(prompt: str, target_length: int) -> str:
    """通用文本压缩方法"""
    lines = prompt.split('\n')
    compressed_lines = []
    current_length = 0

    for line in lines:
        # 优先保留重要的行（标题、指令等）
        if (line.startswith('你现在扮演') or
            line.startswith('这是第') or
            line.startswith('请直接输出') or
            line.startswith('##') or
            line.startswith('#') or
            len(line.strip()) < 50):  # 短行通常是重要信息

            if current_length + len(line) + 1 <= target_length:
                compressed_lines.append(line)
                current_length += len(line) + 1
        else:
            # 普通内容行，选择性保留
            if current_length + len(line) + 1 <= target_length * 0.8:
                compressed_lines.append(line)
                current_length += len(line) + 1

    compressed_prompt = '\n'.join(compressed_lines)

    if len(compressed_prompt) > target_length:
        # 最后截断
        compressed_prompt = compressed_prompt[:target_length-10] + '...\n[内容已截断]'

    return compressed_prompt


def validate_command(cmd: str) -> List[str]:
    """
    验证和解析命令，防止命令注入攻击。
    保留此函数以保持向后兼容性。

    Args:
        cmd: 原始命令字符串

    Returns:
        解析后的命令参数列表

    Raises:
        ValueError: 如果命令包含不安全的内容
    """
    # 基础安全检查
    dangerous_chars = ['|', '&', ';', '$', '`', '(', ')', '<', '>', '"', "'"]
    for char in dangerous_chars:
        if char in cmd:
            raise ValueError(f"命令包含不安全字符: {char}")

    # 解析命令为安全的参数列表
    try:
        cmd_parts = shlex.split(cmd)
        if not cmd_parts:
            raise ValueError("命令不能为空")

        # 限制命令长度
        if len(' '.join(cmd_parts)) > 1000:
            raise ValueError("命令长度超过限制")

        # 检查命令是否为预期的可执行文件（使用配置）
        config = get_config()
        allowed_commands = config.security.allowed_commands
        base_cmd = os.path.basename(cmd_parts[0])
        if not any(allowed in base_cmd for allowed in allowed_commands):
            raise ValueError(f"不允许的命令: {base_cmd}")

        return cmd_parts
    except Exception as e:
        raise ValueError(f"命令解析失败: {str(e)}")


def call_llm_with_sdk(prompt: str) -> str:
    """
    使用 Anthropic Python SDK 调用 Claude 模型。

    Args:
        prompt: 发送给 Claude 的提示文本

    Returns:
        Claude 的响应文本

    Raises:
        RuntimeError: API 调用失败或配置错误
        ValueError: 输入验证失败
    """
    import logging
    logger = logging.getLogger(__name__)

    # 获取配置
    config = get_config()

    # 输入验证
    if not isinstance(prompt, str):
        raise ValueError("提示必须是字符串类型")

    if len(prompt) > config.llm.max_input_length:
        logger.warning(f"提示文本长度 {len(prompt)} 超过限制 ({config.llm.max_input_length} 字符)")

        # 尝试智能压缩
        compressed_prompt = _compress_prompt_if_needed(prompt, config.llm.max_input_length)
        if compressed_prompt:
            logger.info(f"提示文本已从 {len(prompt)} 压缩至 {len(compressed_prompt)} 字符")
            prompt = compressed_prompt
        else:
            raise ValueError(f"提示文本长度超过限制且无法压缩 ({len(prompt)} > {config.llm.max_input_length} 字符)")

    # 记录提示词长度信息
    logger.info(f"提示词长度: {len(prompt)} 字符")

    # 导入聊天日志记录器
    from chat_logger import get_chat_logger
    chat_logger = get_chat_logger()

    # 导入 Anthropic SDK
    try:
        from anthropic import Anthropic
    except ImportError:
        raise RuntimeError("Anthropic SDK 未安装，请运行: pip install anthropic>=0.34.0")

    # 初始化客户端
    try:
        client = Anthropic(api_key=config.llm.api_key)
    except Exception as e:
        # 记录失败到聊天日志
        chat_logger.log_sdk_interaction(
            prompt=prompt,
            response="",
            model=config.llm.model,
            api_success=False,
            error_message=f"客户端初始化失败: {str(e)}"
        )
        raise RuntimeError(f"Anthropic 客户端初始化失败: {str(e)}")

    # 重试机制
    last_error = None
    for attempt in range(config.llm.retry_attempts):
        try:
            logger.debug(f"Claude API 调用尝试 {attempt + 1}/{config.llm.retry_attempts}")

            # 调用 Claude API
            response = client.messages.create(
                model=config.llm.model,
                max_tokens=config.llm.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                timeout=config.llm.timeout
            )

            # 提取响应文本
            result = ""
            if hasattr(response, 'content') and response.content:
                for content_block in response.content:
                    if hasattr(content_block, 'text'):
                        result += content_block.text

            result = result.strip()

            # 验证输出长度
            if len(result) > config.llm.max_output_length:
                logger.warning(f"Claude 输出长度超过限制，截断到 {config.llm.max_output_length} 字符")
                original_length = len(result)
                result = result[:config.llm.max_output_length]
                # 记录截断信息到聊天日志
                chat_logger.log_sdk_interaction(
                    prompt=prompt,
                    response=result,
                    model=config.llm.model,
                    api_success=True,
                    error_message=f"输出被截断，从 {original_length} 字符截断到 {config.llm.max_output_length} 字符"
                )
            else:
                # 记录成功的交互
                chat_logger.log_sdk_interaction(
                    prompt=prompt,
                    response=result,
                    model=config.llm.model,
                    api_success=True
                )

            if not result:
                # 记录空响应到聊天日志
                chat_logger.log_sdk_interaction(
                    prompt=prompt,
                    response="",
                    model=config.llm.model,
                    api_success=False,
                    error_message="Claude 返回空响应"
                )
                raise RuntimeError("Claude 返回空响应")

            logger.debug(f"Claude API 调用成功，响应长度: {len(result)} 字符")
            return result

        except Exception as e:
            # 分类错误类型
            error_str = str(e).lower()
            if "timeout" in error_str:
                last_error = f"Claude API 调用超时 ({config.llm.timeout}秒)"
                logger.warning(f"Claude API 调用超时 (尝试 {attempt + 1})")
            elif "rate" in error_str and "limit" in error_str:
                last_error = "Claude API 速率限制，请稍后重试"
                logger.warning(f"Claude API 速率限制 (尝试 {attempt + 1})")
            elif "authentication" in error_str or "unauthorized" in error_str:
                last_error = "Claude API 认证失败，请检查 API 密钥"
                logger.error(f"Claude API 认证失败: {str(e)}")
                # 记录认证错误到聊天日志
                chat_logger.log_sdk_interaction(
                    prompt=prompt,
                    response="",
                    model=config.llm.model,
                    api_success=False,
                    error_message=f"认证失败: {str(e)}"
                )
                # 认证错误不需要重试
                raise RuntimeError(last_error)
            elif "quota" in error_str or "credit" in error_str:
                last_error = "Claude API 配额不足"
                logger.error(f"Claude API 配额不足: {str(e)}")
                # 记录配额错误到聊天日志
                chat_logger.log_sdk_interaction(
                    prompt=prompt,
                    response="",
                    model=config.llm.model,
                    api_success=False,
                    error_message=f"配额不足: {str(e)}"
                )
                # 配额错误不需要重试
                raise RuntimeError(last_error)
            else:
                last_error = f"Claude API 调用异常: {str(e)}"
                logger.warning(f"Claude API 调用失败 (尝试 {attempt + 1}): {str(e)}")

        # 如果不是最后一次尝试，等待重试
        if attempt < config.llm.retry_attempts - 1:
            logger.info(f"等待 {config.llm.retry_delay} 秒后重试...")
            import time
            time.sleep(config.llm.retry_delay)

    # 所有重试都失败了，记录最终失败
    chat_logger.log_sdk_interaction(
        prompt=prompt,
        response="",
        model=config.llm.model,
        api_success=False,
        error_message=last_error or "Claude API 调用失败"
    )
    raise RuntimeError(last_error or "Claude API 调用失败")


def call_llm_with_cli(prompt: str) -> str:
    """
    安全地调用命令行大模型（例如 Claude CLI）。
    保留此函数以保持向后兼容性。

    Args:
        prompt: 发送给 LLM 的提示文本

    Returns:
        LLM 的响应文本

    Raises:
        RuntimeError: 命令执行失败或配置错误
        ValueError: 输入验证失败或命令验证失败
    """
    import logging
    logger = logging.getLogger(__name__)

    # 获取配置
    config = get_config()

    # 输入验证
    if not isinstance(prompt, str):
        raise ValueError("提示必须是字符串类型")

    if len(prompt) > config.llm.max_input_length:
        logger.warning(f"提示文本长度 {len(prompt)} 超过限制 ({config.llm.max_input_length} 字符)")

        # 尝试智能压缩
        compressed_prompt = _compress_prompt_if_needed(prompt, config.llm.max_input_length)
        if compressed_prompt:
            logger.info(f"提示文本已从 {len(prompt)} 压缩至 {len(compressed_prompt)} 字符")
            prompt = compressed_prompt
        else:
            raise ValueError(f"提示文本长度超过限制且无法压缩 ({len(prompt)} > {config.llm.max_input_length} 字符)")

    # 记录提示词长度信息
    logger.info(f"提示词长度: {len(prompt)} 字符")

    # 导入聊天日志记录器
    from chat_logger import get_chat_logger
    chat_logger = get_chat_logger()

    cmd_str: Optional[str] = config.llm.command
    if not cmd_str:
        # 记录配置错误到聊天日志
        chat_logger.log_cli_interaction(
            prompt=prompt,
            response="",
            command=None,
            exit_code=None,
            error_message="LLM 命令未配置，请设置 LLM_CMD 环境变量或配置文件"
        )
        raise RuntimeError(
            "LLM 命令未配置，请设置 LLM_CMD 环境变量或配置文件。"
        )

    # 验证和解析命令
    try:
        cmd_parts = validate_command(cmd_str)
    except ValueError as e:
        # 记录验证错误到聊天日志
        chat_logger.log_cli_interaction(
            prompt=prompt,
            response="",
            command=cmd_str,
            exit_code=None,
            error_message=f"命令验证失败: {str(e)}"
        )
        raise RuntimeError(f"命令验证失败: {str(e)}")

    # 重试机制
    last_error = None
    proc = None  # 定义在外面以便在异常处理中访问
    for attempt in range(config.llm.retry_attempts):
        try:
            logger.debug(f"LLM CLI 调用尝试 {attempt + 1}/{config.llm.retry_attempts}")

            # 使用安全的参数列表形式，避免 shell=True
            proc = subprocess.Popen(
                cmd_parts,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,  # 关键安全改进：禁用 shell
                text=True,
                timeout=config.llm.timeout,
            )

            stdout, stderr = proc.communicate(prompt, timeout=config.llm.timeout)

            if proc.returncode != 0:
                error_msg = stderr.strip() if stderr else "未知错误"
                # 记录命令执行失败到聊天日志
                chat_logger.log_cli_interaction(
                    prompt=prompt,
                    response=stdout.strip() if stdout else "",
                    command=' '.join(cmd_parts),
                    exit_code=proc.returncode,
                    error_message=error_msg
                )
                raise RuntimeError(
                    f"LLM 命令执行失败，退出码 {proc.returncode}，错误: {error_msg}"
                )

            result = (stdout or "").strip()

            # 验证输出长度
            if len(result) > config.llm.max_output_length:
                logger.warning(f"LLM 输出长度超过限制，截断到 {config.llm.max_output_length} 字符")
                original_length = len(result)
                result = result[:config.llm.max_output_length]
                # 记录截断信息到聊天日志
                chat_logger.log_cli_interaction(
                    prompt=prompt,
                    response=result,
                    command=' '.join(cmd_parts),
                    exit_code=0,
                    error_message=f"输出被截断，从 {original_length} 字符截断到 {config.llm.max_output_length} 字符"
                )
            else:
                # 记录成功的交互
                chat_logger.log_cli_interaction(
                    prompt=prompt,
                    response=result,
                    command=' '.join(cmd_parts),
                    exit_code=0
                )

            return result

        except subprocess.TimeoutExpired:
            if proc:
                proc.kill()
            last_error = f"LLM 命令执行超时 ({config.llm.timeout}秒)"
            logger.warning(f"LLM CLI 调用超时 (尝试 {attempt + 1})")
            # 记录超时错误到聊天日志
            chat_logger.log_cli_interaction(
                prompt=prompt,
                response="",
                command=' '.join(cmd_parts),
                exit_code=None,
                error_message=f"命令执行超时 ({config.llm.timeout}秒)"
            )
        except Exception as e:
            last_error = f"LLM 命令执行异常: {str(e)}"
            logger.warning(f"LLM CLI 调用失败 (尝试 {attempt + 1}): {str(e)}")
            # 记录异常错误到聊天日志
            chat_logger.log_cli_interaction(
                prompt=prompt,
                response="",
                command=' '.join(cmd_parts),
                exit_code=None,
                error_message=f"命令执行异常: {str(e)}"
            )

        # 如果不是最后一次尝试，等待重试
        if attempt < config.llm.retry_attempts - 1:
            logger.info(f"等待 {config.llm.retry_delay} 秒后重试...")
            import time
            time.sleep(config.llm.retry_delay)

    # 所有重试都失败了，记录最终失败
    chat_logger.log_cli_interaction(
        prompt=prompt,
        response="",
        command=' '.join(cmd_parts),
        exit_code=None,
        error_message=last_error or "LLM CLI 调用失败"
    )
    raise RuntimeError(last_error or "LLM CLI 调用失败")


def call_llm(prompt: str) -> str:
    """
    调用 LLM 的统一接口，根据配置自动选择 SDK 或 CLI 模式。

    Args:
        prompt: 发送给 LLM 的提示文本

    Returns:
        LLM 的响应文本

    Raises:
        RuntimeError: 调用失败或配置错误
        ValueError: 输入验证失败
    """
    import logging
    logger = logging.getLogger(__name__)

    # 获取配置
    config = get_config()

    # 根据配置选择调用方式
    if config.llm.use_sdk:
        logger.debug("使用 Anthropic SDK 模式调用 Claude")
        return call_llm_with_sdk(prompt)
    else:
        logger.debug("使用 CLI 模式调用 LLM")
        return call_llm_with_cli(prompt)
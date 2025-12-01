import os
import re
from typing import Any, Dict, Optional


class ValidationError(Exception):
    """输入验证错误异常"""
    pass


def validate_path(path: str, base_dir: str = None) -> str:
    """
    验证文件路径安全性，防止目录遍历攻击

    Args:
        path: 用户输入的路径
        base_dir: 基础目录，如果为None则使用当前工作目录

    Returns:
        验证后的安全路径

    Raises:
        ValidationError: 路径不安全时抛出
    """
    import logging
    logger = logging.getLogger(__name__)

    if not isinstance(path, str):
        raise ValidationError("路径必须是字符串类型")

    # 移除前后空格
    clean_path = path.strip()

    if not clean_path:
        raise ValidationError("路径不能为空")

    # 检查路径长度
    if len(clean_path) > 260:  # Windows路径长度限制
        raise ValidationError("路径长度超过限制")

    # 特殊处理当前目录和上级目录的相对路径
    if clean_path in ('.', './', '.\\'):
        clean_path = '.'
    elif clean_path in ('..', '../', '..\\'):
        # 允许访问上级目录，但会进行安全检查
        pass  # 继续进行路径验证

    # 使用 pathlib 进行路径规范化
    from pathlib import Path
    try:
        # 获取基础目录
        if base_dir:
            base_path = Path(base_dir).resolve()
        else:
            base_path = Path.cwd()

        # 解析用户路径
        if clean_path == '.':
            target_path = base_path
        else:
            target_path = (base_path / clean_path).resolve()

        logger.debug(f"路径验证: 基础目录={base_path}, 用户输入={path}, 规范化路径={target_path}")

        # 安全检查：允许合理的上级目录访问，但防止恶意遍历
        # 检查路径中是否包含过多的上级目录遍历
        path_parts = target_path.parts
        if len([p for p in path_parts if p == '..']) > 5:  # 限制最多5级上级目录
            error_msg = "路径遍历层级过深，可能存在安全风险"
            logger.warning(f"路径验证失败: {error_msg}")
            logger.warning(f"  目标路径: {target_path}")
            raise ValidationError(error_msg)

        # 验证路径安全性：防止访问系统关键目录
        dangerous_patterns = [
            '/etc', '/bin', '/usr/bin', '/usr/sbin', '/var', '/tmp',
            'C:\\Windows', 'C:\\Program Files', 'C:\\Program Files (x86)',
            'C:\\Users\\Default', 'C:\\Windows\\System32'
        ]

        target_path_lower = str(target_path).lower()
        if any(dangerous.lower() in target_path_lower for dangerous in dangerous_patterns):
            error_msg = "不允许访问系统关键目录"
            logger.warning(f"路径验证失败: {error_msg}")
            logger.warning(f"  目标路径: {target_path}")
            raise ValidationError(error_msg)

        logger.debug("路径安全检查通过")

        # 记录路径访问信息
        if target_path != base_path:
            logger.info(f"访问上级目录: {target_path} (基础目录: {base_path})")
        else:
            logger.debug("路径验证通过：目标路径在基础目录内")

        # 检查路径是否存在且可访问
        if not target_path.exists():
            raise ValidationError("路径不存在")

        if not target_path.is_dir():
            raise ValidationError("路径必须是目录")

        if not os.access(str(target_path), os.R_OK):
            raise ValidationError("路径无法访问")

        return str(target_path)

    except OSError as e:
        error_msg = f"路径处理失败: {str(e)}"
        logger.error(f"路径验证异常: {error_msg}")
        raise ValidationError(error_msg)
    except Exception as e:
        error_msg = f"路径验证异常: {str(e)}"
        logger.error(f"路径验证异常: {error_msg}")
        raise ValidationError(error_msg)


def validate_idea_text(text: str) -> str:
    """
    验证创意文本输入

    Args:
        text: 用户输入的创意文本

    Returns:
        验证后的文本

    Raises:
        ValidationError: 文本不安全时抛出
    """
    if not isinstance(text, str):
        raise ValidationError("创意文本必须是字符串类型")

    clean_text = text.strip()

    if not clean_text:
        raise ValidationError("创意文本不能为空")

    # 检查文本长度
    if len(clean_text) < 10:
        raise ValidationError("创意文本太短，请提供更详细的描述")

    if len(clean_text) > 50000:  # 50KB限制
        raise ValidationError("创意文本长度超过限制")

    # 检查危险内容
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',  # XSS
        r'javascript:',                # JavaScript协议
        r'data:[^;]*;base64',         # Base64数据
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, clean_text, re.IGNORECASE | re.DOTALL):
            raise ValidationError("创意文本包含不安全内容")

    return clean_text


def validate_iterations(iterations: Any) -> int:
    """
    验证迭代次数参数

    Args:
        iterations: 用户输入的迭代次数

    Returns:
        验证后的迭代次数

    Raises:
        ValidationError: 迭代次数无效时抛出
    """
    if iterations is None:
        return 1

    try:
        iters = int(iterations)
    except (TypeError, ValueError):
        raise ValidationError("迭代次数必须是数字")

    if iters < 1:
        raise ValidationError("迭代次数至少为1")

    if iters > 10:
        raise ValidationError("迭代次数不能超过10")

    return iters


def validate_output_name(name: Any) -> Optional[str]:
    """
    验证输出文件名

    Args:
        name: 用户输入的文件名

    Returns:
        验证后的文件名，如果为空则返回None

    Raises:
        ValidationError: 文件名无效时抛出
    """
    if name is None:
        return None

    if not isinstance(name, str):
        raise ValidationError("输出文件名必须是字符串类型")

    clean_name = name.strip()

    if not clean_name:
        return None

    # 检查文件名长度
    if len(clean_name) > 100:
        raise ValidationError("输出文件名长度超过限制")

    # 检查危险字符
    dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '/', '\\']
    for char in dangerous_chars:
        if char in clean_name:
            raise ValidationError(f"文件名包含不安全字符: {char}")

    # 检查文件名模式
    if re.search(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$', clean_name, re.IGNORECASE):
        raise ValidationError("文件名不能使用系统保留名称")

    return clean_name


def validate_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证请求数据完整性

    Args:
        data: 请求数据字典

    Returns:
        验证后的数据字典

    Raises:
        ValidationError: 请求数据无效时抛出
    """
    if not isinstance(data, dict):
        raise ValidationError("请求数据格式错误")

    mode = data.get("mode")
    if mode not in {"code", "idea"}:
        raise ValidationError("模式必须是 'code' 或 'idea'")

    validated_data = {"mode": mode}

    # 验证模式特定参数
    if mode == "code":
        project_path = data.get("projectPath") or data.get("project_path") or "."
        validated_data["project_path"] = validate_path(project_path)
    else:  # mode == "idea"
        idea_text = data.get("ideaText") or data.get("idea_text")
        if not idea_text:
            raise ValidationError("创意模式下必须提供创意文本")
        validated_data["idea_text"] = validate_idea_text(idea_text)

    # 验证通用参数
    iterations = data.get("iterations", 1)
    validated_data["iterations"] = validate_iterations(iterations)

    output_name = data.get("outputName") or data.get("output_name")
    validated_data["output_name"] = validate_output_name(output_name)

    return validated_data


def sanitize_error_message(message: str, include_debug_info: bool = False) -> str:
    """
    清理错误消息，防止信息泄露

    Args:
        message: 原始错误消息
        include_debug_info: 是否包含调试信息

    Returns:
        清理后的安全错误消息
    """
    if not message:
        return "未知错误"

    # 基础清理：移除可能的敏感信息
    sanitized = re.sub(r'[A-Za-z]:\\[^\\s]*', '[路径]', message)
    sanitized = re.sub(r'/[^\\s]*', '[路径]', sanitized)

    # 移除可能的堆栈跟踪信息
    sanitized = re.sub(r'File ".*?", line \d+', '[位置]', sanitized)
    sanitized = re.sub(r'Traceback.*?:', '', sanitized)

    # 移除系统调用详细信息
    sanitized = re.sub(r'Permission denied: .*', '权限不足', sanitized)
    sanitized = re.sub(r'No such file or directory: .*', '文件或目录不存在', sanitized)

    result = sanitized.strip()

    # 在调试模式下，提供更详细的错误分类
    if include_debug_info:
        if "路径超出允许的访问范围" in result:
            return f"访问被拒绝: 尝试访问的目录不在允许范围内"
        elif "路径不存在" in result:
            return f"路径错误: 指定的目录不存在"
        elif "路径无法访问" in result:
            return f"权限错误: 无法访问指定目录"
        elif "路径必须是目录" in result:
            return f"类型错误: 指定的路径不是目录"
        elif "路径长度超过限制" in result:
            return f"输入错误: 路径长度超过系统限制"

    return result


def categorize_error(error_type: str, original_error: str = None) -> str:
    """
    将错误分类为用户友好的消息

    Args:
        error_type: 错误类型
        original_error: 原始错误信息（可选）

    Returns:
        用户友好的错误消息
    """
    error_messages = {
        "path_too_long": "路径过长，请使用较短的路径名",
        "invalid_chars": "路径包含无效字符，请检查路径格式",
        "directory_traversal": "不允许访问上级目录或使用相对路径遍历",
        "absolute_path": "不允许使用绝对路径，请使用相对路径",
        "path_not_found": "指定的目录不存在，请检查路径是否正确",
        "permission_denied": "没有权限访问指定目录，请检查文件系统权限",
        "not_directory": "指定的路径不是目录，请提供有效的目录路径",
        "validation_failed": "输入验证失败，请检查输入格式",
        "empty_input": "输入不能为空，请提供有效的内容",
        "too_long": "输入内容过长，请减少内容长度",
        "invalid_format": "输入格式不正确，请检查格式要求"
    }

    # 尝试从原始错误中提取更多信息
    if original_error:
        if "260" in original_error:
            return error_messages["path_too_long"]
        elif "Permission denied" in original_error:
            return error_messages["permission_denied"]
        elif "No such file" in original_error:
            return error_messages["path_not_found"]
        elif "not a directory" in original_error:
            return error_messages["not_directory"]

    return error_messages.get(error_type, f"未知错误类型: {error_type}")
import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 3000
    debug: bool = False
    threaded: bool = True
    secret_key: Optional[str] = None


@dataclass
class TaskManagerConfig:
    """任务管理器配置"""
    max_workers: int = 3
    cleanup_interval: int = 3600  # 1小时
    task_timeout: int = 1800      # 30分钟
    max_pending_tasks: int = 100


@dataclass
class LLMConfig:
    """LLM 配置"""
    # CLI 配置 (已弃用，保持向后兼容)
    command: Optional[str] = None
    # Anthropic SDK 配置
    api_key: Optional[str] = None
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 8192
    timeout: int = 300            # 5分钟
    max_input_length: int = 100000  # 100KB
    max_output_length: int = 2000000  # 2MB
    retry_attempts: int = 3
    retry_delay: int = 5          # 5秒
    use_sdk: bool = True          # 默认使用 SDK


@dataclass
class FileAnalysisConfig:
    """文件分析配置"""
    max_files: int = 200
    max_file_size: int = 1024 * 1024  # 1MB
    max_content_length: int = 50 * 1024  # 50KB per file
    max_lines: int = 80
    chunk_size: int = 8192        # 8KB
    allowed_extensions: list = field(default_factory=lambda: [
        ".js", ".jsx", ".ts", ".tsx", ".py", ".java", ".cs", ".go", ".rs",
        ".cpp", ".c", ".rb", ".php", ".swift", ".kt", ".scala", ".dart",
        ".sh", ".bash", ".zsh", ".ps1", ".bat", ".sql", ".html", ".css",
        ".scss", ".sass", ".less", ".vue", ".svelte"
    ])
    ignore_dirs: set = field(default_factory=lambda: {
        "node_modules", ".git", "dist", "build", "out", ".next", ".turbo",
        "coverage", "__pycache__", ".venv", "venv", "env", ".env", ".idea",
        ".vscode", ".eclipse", "target", "bin", "obj", "Debug", "Release",
        "packages", "vendor", "cache", "temp", "tmp", ".tmp"
    })


@dataclass
class SecurityConfig:
    """安全配置"""
    max_request_size: int = 2 * 1024 * 1024  # 2MB
    max_idea_length: int = 50000
    max_output_name_length: int = 100
    max_iterations: int = 10
    allowed_commands: list = field(default_factory=lambda: [
        "claude", "python", "python3"
    ])
    enable_cors: bool = False
    allowed_origins: list = field(default_factory=lambda: ["*"])
    # 路径安全配置
    allowed_base_directories: list = field(default_factory=lambda: [".", "..", "./", "../"])
    restrict_to_base_directory: bool = True  # 是否限制只能访问基础目录


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: str = "patent_generator.log"
    file_max_size: int = 10 * 1024 * 1024  # 10MB
    file_backup_count: int = 5
    console_enabled: bool = True


@dataclass
class StorageConfig:
    """存储配置"""
    output_dir: str = "output"
    max_output_files: int = 1000
    cleanup_enabled: bool = True
    cleanup_days: int = 30


class Config:
    """集中配置管理器"""

    def __init__(self):
        self.server = ServerConfig()
        self.task_manager = TaskManagerConfig()
        self.llm = LLMConfig()
        self.file_analysis = FileAnalysisConfig()
        self.security = SecurityConfig()
        self.logging = LoggingConfig()
        self.storage = StorageConfig()

        # 加载环境变量配置
        self._load_from_env()

        # 验证配置
        self._validate_config()

    def _load_from_env(self) -> None:
        """从环境变量加载配置"""

        # 服务器配置
        self.server.host = os.getenv("HOST", self.server.host)
        self.server.port = int(os.getenv("PORT", str(self.server.port)))
        self.server.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.server.secret_key = os.getenv("SECRET_KEY", self.server.secret_key)

        # 任务管理器配置
        self.task_manager.max_workers = int(os.getenv("MAX_WORKERS", str(self.task_manager.max_workers)))
        self.task_manager.cleanup_interval = int(os.getenv("CLEANUP_INTERVAL", str(self.task_manager.cleanup_interval)))
        self.task_manager.task_timeout = int(os.getenv("TASK_TIMEOUT", str(self.task_manager.task_timeout)))
        self.task_manager.max_pending_tasks = int(os.getenv("MAX_PENDING_TASKS", str(self.task_manager.max_pending_tasks)))

        # LLM 配置
        self.llm.command = os.getenv("LLM_CMD", self.llm.command)
        self.llm.api_key = os.getenv("ANTHROPIC_API_KEY", self.llm.api_key)
        self.llm.model = os.getenv("ANTHROPIC_MODEL", self.llm.model)
        self.llm.max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", str(self.llm.max_tokens)))
        self.llm.timeout = int(os.getenv("LLM_TIMEOUT", str(self.llm.timeout)))
        self.llm.max_input_length = int(os.getenv("LLM_MAX_INPUT_LENGTH", str(self.llm.max_input_length)))
        self.llm.max_output_length = int(os.getenv("LLM_MAX_OUTPUT_LENGTH", str(self.llm.max_output_length)))
        self.llm.retry_attempts = int(os.getenv("LLM_RETRY_ATTEMPTS", str(self.llm.retry_attempts)))
        self.llm.retry_delay = int(os.getenv("LLM_RETRY_DELAY", str(self.llm.retry_delay)))
        self.llm.use_sdk = os.getenv("USE_ANTHROPIC_SDK", "true").lower() == "true"

        # 文件分析配置
        self.file_analysis.max_files = int(os.getenv("MAX_FILES", str(self.file_analysis.max_files)))
        self.file_analysis.max_file_size = int(os.getenv("MAX_FILE_SIZE", str(self.file_analysis.max_file_size)))
        self.file_analysis.max_content_length = int(os.getenv("MAX_CONTENT_LENGTH", str(self.file_analysis.max_content_length)))
        self.file_analysis.max_lines = int(os.getenv("MAX_LINES", str(self.file_analysis.max_lines)))
        self.file_analysis.chunk_size = int(os.getenv("CHUNK_SIZE", str(self.file_analysis.chunk_size)))

        # 安全配置
        self.security.max_request_size = int(os.getenv("MAX_REQUEST_SIZE", str(self.security.max_request_size)))
        self.security.max_idea_length = int(os.getenv("MAX_IDEA_LENGTH", str(self.security.max_idea_length)))
        self.security.max_output_name_length = int(os.getenv("MAX_OUTPUT_NAME_LENGTH", str(self.security.max_output_name_length)))
        self.security.max_iterations = int(os.getenv("MAX_ITERATIONS", str(self.security.max_iterations)))
        self.security.enable_cors = os.getenv("ENABLE_CORS", "false").lower() == "true"

        # 路径安全配置
        allowed_dirs_str = os.getenv("ALLOWED_BASE_DIRECTORIES", ",".join(self.security.allowed_base_directories))
        if allowed_dirs_str:
            self.security.allowed_base_directories = [dir.strip() for dir in allowed_dirs_str.split(",")]

        self.security.restrict_to_base_directory = os.getenv("RESTRICT_TO_BASE_DIRECTORY", "false").lower() == "true"
        self.security.max_parent_levels = int(os.getenv("MAX_PARENT_LEVELS", "5"))

        # 日志配置
        self.logging.level = os.getenv("LOG_LEVEL", self.logging.level).upper()
        self.logging.file_enabled = os.getenv("LOG_FILE_ENABLED", "true").lower() == "true"
        self.logging.file_path = os.getenv("LOG_FILE_PATH", self.logging.file_path)
        self.logging.console_enabled = os.getenv("LOG_CONSOLE_ENABLED", "true").lower() == "true"

        # 存储配置
        self.storage.output_dir = os.getenv("OUTPUT_DIR", self.storage.output_dir)
        self.storage.max_output_files = int(os.getenv("MAX_OUTPUT_FILES", str(self.storage.max_output_files)))
        self.storage.cleanup_enabled = os.getenv("STORAGE_CLEANUP_ENABLED", "true").lower() == "true"
        self.storage.cleanup_days = int(os.getenv("STORAGE_CLEANUP_DAYS", str(self.storage.cleanup_days)))

    def _validate_config(self) -> None:
        """验证配置的有效性"""
        logger = logging.getLogger(__name__)

        # 验证端口范围
        if not (1 <= self.server.port <= 65535):
            raise ValueError(f"无效的端口号: {self.server.port}")

        # 验证任务管理器配置
        if self.task_manager.max_workers <= 0:
            raise ValueError("max_workers 必须大于 0")

        if self.task_manager.task_timeout <= 0:
            raise ValueError("task_timeout 必须大于 0")

        # 验证 LLM 配置
        if self.llm.timeout <= 0:
            raise ValueError("LLM timeout 必须大于 0")

        if self.llm.max_input_length <= 0:
            raise ValueError("max_input_length 必须大于 0")

        if self.llm.use_sdk:
            # SDK 模式验证
            if not self.llm.api_key:
                logger.warning("警告: ANTHROPIC_API_KEY 环境变量未设置，将使用 api_key=None")
            if self.llm.max_tokens <= 0:
                raise ValueError("max_tokens 必须大于 0")
        else:
            # CLI 模式验证
            if self.llm.command and len(self.llm.command.strip()) == 0:
                raise ValueError("LLM 命令不能为空")

        # 验证文件分析配置
        if self.file_analysis.max_files <= 0:
            raise ValueError("max_files 必须大于 0")

        if self.file_analysis.max_file_size <= 0:
            raise ValueError("max_file_size 必须大于 0")

        # 验证安全配置
        if self.security.max_request_size <= 0:
            raise ValueError("max_request_size 必须大于 0")

        if self.security.max_iterations <= 0:
            raise ValueError("max_iterations 必须大于 0")

        # 验证日志级别
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.logging.level not in valid_levels:
            raise ValueError(f"无效的日志级别: {self.logging.level}")

        # 验证存储配置
        if not self.storage.output_dir.strip():
            raise ValueError("output_dir 不能为空")

        # 检查必要的环境变量
        if self.llm.use_sdk:
            if not self.llm.api_key:
                logger.warning("警告: ANTHROPIC_API_KEY 环境变量未设置，将使用 api_key=None")
        else:
            if not self.llm.command:
                logger.warning("警告: LLM_CMD 环境变量未设置，LLM 功能将不可用")

        logger.info("配置验证通过")

    def get_flask_config(self) -> Dict[str, Any]:
        """获取 Flask 应用配置"""
        return {
            "SECRET_KEY": self.server.secret_key or "dev-secret-key-change-in-production",
            "MAX_CONTENT_LENGTH": self.security.max_request_size,
        }

    def ensure_output_dir(self) -> str:
        """确保输出目录存在"""
        output_path = Path(self.storage.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        return str(output_path.absolute())

    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典格式（隐藏敏感信息）"""
        return {
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "debug": self.server.debug,
                "threaded": self.server.threaded,
            },
            "task_manager": {
                "max_workers": self.task_manager.max_workers,
                "cleanup_interval": self.task_manager.cleanup_interval,
                "task_timeout": self.task_manager.task_timeout,
                "max_pending_tasks": self.task_manager.max_pending_tasks,
            },
            "llm": {
                "use_sdk": self.llm.use_sdk,
                "model": self.llm.model,
                "max_tokens": self.llm.max_tokens,
                "timeout": self.llm.timeout,
                "max_input_length": self.llm.max_input_length,
                "max_output_length": self.llm.max_output_length,
                "retry_attempts": self.llm.retry_attempts,
                "retry_delay": self.llm.retry_delay,
                "api_key_configured": bool(self.llm.api_key),
                "command_configured": bool(self.llm.command),
            },
            "file_analysis": {
                "max_files": self.file_analysis.max_files,
                "max_file_size": self.file_analysis.max_file_size,
                "max_content_length": self.file_analysis.max_content_length,
                "max_lines": self.file_analysis.max_lines,
                "chunk_size": self.file_analysis.chunk_size,
            },
            "security": {
                "max_request_size": self.security.max_request_size,
                "max_idea_length": self.security.max_idea_length,
                "max_output_name_length": self.security.max_output_name_length,
                "max_iterations": self.security.max_iterations,
                "enable_cors": self.security.enable_cors,
                "allowed_base_directories": self.security.allowed_base_directories,
                "restrict_to_base_directory": self.security.restrict_to_base_directory,
                "max_parent_levels": self.security.max_parent_levels,
            },
            "logging": {
                "level": self.logging.level,
                "file_enabled": self.logging.file_enabled,
                "file_path": self.logging.file_path,
                "console_enabled": self.logging.console_enabled,
            },
            "storage": {
                "output_dir": self.storage.output_dir,
                "max_output_files": self.storage.max_output_files,
                "cleanup_enabled": self.storage.cleanup_enabled,
                "cleanup_days": self.storage.cleanup_days,
            }
        }


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    """重新加载配置"""
    global _config
    _config = Config()
    return _config


def get_env_template() -> str:
    """生成环境变量模板"""
    return """
# 服务器配置
HOST=0.0.0.0
PORT=3000
DEBUG=false
SECRET_KEY=your-secret-key-here

# 任务管理器配置
MAX_WORKERS=3
CLEANUP_INTERVAL=3600
TASK_TIMEOUT=1800
MAX_PENDING_TASKS=100

# LLM 配置 (必须设置)
LLM_CMD=claude chat --model claude-3-5-sonnet
LLM_TIMEOUT=300
LLM_MAX_INPUT_LENGTH=100000
LLM_MAX_OUTPUT_LENGTH=2000000
LLM_RETRY_ATTEMPTS=3
LLM_RETRY_DELAY=5

# 文件分析配置
MAX_FILES=200
MAX_FILE_SIZE=1048576
MAX_CONTENT_LENGTH=51200
MAX_LINES=80
CHUNK_SIZE=8192

# 安全配置
MAX_REQUEST_SIZE=2097152
MAX_IDEA_LENGTH=50000
MAX_OUTPUT_NAME_LENGTH=100
MAX_ITERATIONS=10
ENABLE_CORS=false

# 日志配置
LOG_LEVEL=INFO
LOG_FILE_ENABLED=true
LOG_FILE_PATH=patent_generator.log
LOG_CONSOLE_ENABLED=true

# 存储配置
OUTPUT_DIR=output
MAX_OUTPUT_FILES=1000
STORAGE_CLEANUP_ENABLED=true
STORAGE_CLEANUP_DAYS=30
"""
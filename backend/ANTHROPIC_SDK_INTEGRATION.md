# Anthropic Python SDK 集成指南

本文档描述了专利生成系统从 CLI 模式迁移到 Anthropic Python SDK 的完整实现。

## 概述

系统现在支持两种 LLM 调用模式：
- **SDK 模式（推荐）**: 使用 Anthropic Python SDK 直接调用 Claude API
- **CLI 模式（兼容）**: 使用命令行工具调用 Claude（保持向后兼容）

## 主要改进

### 1. 安全性提升
- 移除了命令注入风险（不再使用 `shell=True`）
- 直接使用 Anthropic 官方 SDK，避免中间层安全问题
- 改进的错误处理和输入验证

### 2. 性能优化
- 减少了子进程开销
- 更快的 API 调用响应时间
- 更好的重试机制和错误分类

### 3. 可靠性增强
- 官方 SDK 支持，更稳定
- 详细的错误分类和处理
- 自动重试机制，包含指数退避

### 4. 配置灵活性
- 支持多种 Claude 模型
- 可配置的最大令牌数
- 灵活的 API 密钥管理

## 安装和配置

### 1. 安装依赖

```bash
pip install anthropic>=0.34.0,<1.0.0
```

或使用 requirements.txt：
```bash
pip install -r requirements.txt
```

### 2. 环境变量配置

创建 `.env` 文件（从 `.env.example` 复制）：

```env
# Anthropic SDK 配置（推荐）
USE_ANTHROPIC_SDK=true
ANTHROPIC_API_KEY=your-api-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_MAX_TOKENS=8192

# 其他配置
LLM_TIMEOUT=300
LLM_MAX_INPUT_LENGTH=100000
LLM_MAX_OUTPUT_LENGTH=2000000
LLM_RETRY_ATTEMPTS=3
LLM_RETRY_DELAY=5
```

### 3. 可用模型

- `claude-3-5-sonnet-20241022` (推荐)
- `claude-3-5-haiku-20241022`
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`
- `claude-3-haiku-20240307`

## 代码结构

### 配置系统 (`config.py`)

```python
@dataclass
class LLMConfig:
    # CLI 配置（已弃用，保持向后兼容）
    command: Optional[str] = None
    # Anthropic SDK 配置
    api_key: Optional[str] = None
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 8192
    use_sdk: bool = True  # 默认使用 SDK
```

### LLM 客户端 (`llm_client.py`)

主要函数：
- `call_llm(prompt)`: 统一接口，自动选择 SDK 或 CLI 模式
- `call_llm_with_sdk(prompt)`: 使用 Anthropic SDK 调用 Claude
- `call_llm_with_cli(prompt)`: 使用 CLI 工具调用（兼容模式）

### 错误处理

SDK 模式支持详细的错误分类：
- **超时错误**: 自动重试
- **速率限制**: 等待后重试
- **认证错误**: 立即失败，提示检查 API 密钥
- **配额错误**: 立即失败，提示检查账户配额
- **其他错误**: 通用重试机制

## 使用示例

### 基本使用

```python
from llm_client import call_llm
from config import get_config

# 获取配置
config = get_config()

# 调用 Claude（自动选择 SDK 或 CLI 模式）
response = call_llm("请帮我写一段专利描述")
print(response)
```

### 手动选择模式

```python
from llm_client import call_llm_with_sdk, call_llm_with_cli

# 强制使用 SDK
response = call_llm_with_sdk("请帮我写一段专利描述")

# 强制使用 CLI（需要配置 LLM_CMD）
response = call_llm_with_cli("请帮我写一段专利描述")
```

### 配置检查

```python
from config import get_config

config = get_config()
print(f"使用 SDK: {config.llm.use_sdk}")
print(f"模型: {config.llm.model}")
print(f"最大令牌: {config.llm.max_tokens}")
print(f"API 密钥已配置: {bool(config.llm.api_key)}")
```

## 测试

运行集成测试：

```bash
python test_sdk_integration.py
```

测试包括：
1. SDK 导入测试
2. 配置加载测试
3. 客户端初始化测试
4. 统一接口测试
5. API 调用测试（需要有效的 API 密钥）

## 迁移指南

### 从 CLI 模式迁移

1. **安装 SDK**:
   ```bash
   pip install anthropic>=0.34.0
   ```

2. **更新配置**:
   ```env
   USE_ANTHROPIC_SDK=true
   ANTHROPIC_API_KEY=your-api-key-here
   ```

3. **移除 CLI 配置**（可选）:
   ```env
   # LLM_CMD=claude chat --model claude-3-5-sonnet  # 可以注释掉
   ```

### 回退到 CLI 模式

如果需要回退到 CLI 模式：

```env
USE_ANTHROPIC_SDK=false
LLM_CMD=claude chat --model claude-3-5-sonnet
```

## 故障排除

### 常见问题

1. **导入错误**:
   ```
   ImportError: No module named 'anthropic'
   ```
   解决：运行 `pip install anthropic>=0.34.0`

2. **认证错误**:
   ```
   Claude API 认证失败，请检查 API 密钥
   ```
   解决：检查 `ANTHROPIC_API_KEY` 环境变量

3. **配额错误**:
   ```
   Claude API 配额不足
   ```
   解决：检查 Anthropic 账户余额和使用限制

4. **速率限制**:
   ```
   Claude API 速率限制，请稍后重试
   ```
   解决：等待一段时间后重试，或升级 API 计划

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 性能对比

| 指标 | CLI 模式 | SDK 模式 |
|------|----------|----------|
| 响应时间 | 较慢（子进程开销） | 快速（直接 API 调用） |
| 内存使用 | 较高（子进程） | 较低（同进程） |
| 稳定性 | 中等 | 高（官方 SDK） |
| 安全性 | 中等（命令注入风险） | 高（无 shell 调用） |
| 错误处理 | 基础 | 详细（错误分类） |

## 最佳实践

1. **使用 SDK 模式**：除非特殊需求，建议使用 SDK 模式
2. **配置 API 密钥**：使用环境变量，不要硬编码在代码中
3. **设置合理的超时**：根据网络环境调整 `LLM_TIMEOUT`
4. **监控使用量**：注意 API 配额和成本控制
5. **错误处理**：在生产环境中实现完整的错误处理和重试逻辑

## 版本兼容性

- **Python**: 3.7+
- **Anthropic SDK**: 0.34.0+
- **Flask**: 3.0.0+

## 更新日志

- **v1.0.0**: 初始 SDK 集成实现
- 支持 Claude 3.5 模型系列
- 完整的错误处理和重试机制
- 向后兼容 CLI 模式
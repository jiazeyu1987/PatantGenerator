# 聊天日志功能指南

本指南详细介绍了专利生成系统的聊天日志功能，该功能可以自动记录所有 LLM（大语言模型）的提示词和回复。

## 功能概述

聊天日志功能会自动：
- 记录所有发送给 Claude 的提示词
- 记录 Claude 的所有回复
- 按日期分割日志文件
- 支持敏感信息自动屏蔽
- 提供完整的 API 接口进行管理
- 自动清理过期日志文件

## 文件结构

```
chat_logs/
├── chat_prompt_20241201.log    # 2024年12月1日的聊天日志
├── chat_prompt_20241202.log    # 2024年12月2日的聊天日志
└── ...
```

### 日志文件格式

每个日志文件包含以下信息：
```
================================================================================
时间戳: 2024-12-01 15:30:45
模式: SDK
提示词长度: 1250 字符
回复长度: 3200 字符
元数据: {
  "model": "claude-3-5-sonnet-20241022",
  "api_success": true
}

--- 提示词 ---
请帮我分析以下代码的创新点...

--- 回复 ---
根据您提供的代码，我分析了以下几个创新点...

```

## 配置选项

### 环境变量配置

在 `.env` 文件中添加以下配置：

```env
# LLM 聊天日志配置
CHAT_LOG_ENABLED=true          # 启用聊天日志
CHAT_LOG_DIR=chat_logs         # 日志存储目录
CHAT_LOG_MAX_FILES=1000        # 最大保留文件数量
```

### 配置说明

- **CHAT_LOG_ENABLED**: 是否启用聊天日志功能（默认: true）
- **CHAT_LOG_DIR**: 聊天日志存储目录（默认: chat_logs）
- **CHAT_LOG_MAX_FILES**: 最大保留的日志文件数量（默认: 1000）

## API 接口

### 1. 获取统计信息

```http
GET /api/chat-logs/stats
```

**响应示例:**
```json
{
  "ok": true,
  "stats": {
    "enabled": true,
    "log_files_count": 5,
    "total_size_mb": 12.5,
    "total_interactions": 150,
    "oldest_file": "chat_prompt_20241127.log",
    "newest_file": "chat_prompt_20241201.log"
  }
}
```

### 2. 获取文件列表

```http
GET /api/chat-logs/files
```

**响应示例:**
```json
{
  "ok": true,
  "files": [
    {
      "name": "chat_prompt_20241201.log",
      "path": "/path/to/chat_logs/chat_prompt_20241201.log",
      "size": 25600,
      "size_human": "25.0KB",
      "modified": "2024-12-01 15:30:45",
      "modified_timestamp": 1701425445
    }
  ],
  "count": 1
}
```

### 3. 预览文件内容

```http
GET /api/chat-logs/files/{filename}/preview?lines=100&offset=0
```

**参数:**
- `lines`: 返回的行数（最大1000）
- `offset`: 起始行偏移量

**响应示例:**
```json
{
  "ok": true,
  "filename": "chat_prompt_20241201.log",
  "total_lines": 500,
  "offset": 0,
  "lines_returned": 100,
  "content": "日志内容...",
  "has_more": true
}
```

### 4. 下载文件

```http
GET /api/chat-logs/files/{filename}/download
```

### 5. 删除文件

```http
DELETE /api/chat-logs/files/{filename}
```

**响应示例:**
```json
{
  "ok": true,
  "message": "文件 chat_prompt_20241201.log 已删除"
}
```

### 6. 搜索日志内容

```http
POST /api/chat-logs/search
```

**请求体:**
```json
{
  "query": "专利创新点",
  "max_results": 50,
  "date_filter": "2024-12-01"
}
```

**响应示例:**
```json
{
  "ok": true,
  "query": "专利创新点",
  "results": [
    {
      "file": "chat_prompt_20241201.log",
      "line_number": 125,
      "match_line": "请分析这个代码的专利创新点",
      "context": [
        "时间戳: 2024-12-01 15:30:45",
        "模式: SDK",
        "请分析这个代码的专利创新点",
        "--- 回复 ---"
      ],
      "timestamp": "2024-12-01 15:30:45"
    }
  ],
  "total_results": 1,
  "files_searched": 1,
  "date_filter": "2024-12-01"
}
```

## 安全特性

### 敏感信息屏蔽

聊天日志会自动检测和屏蔽以下敏感信息：
- API 密钥 (api_key, apikey, api-key)
- 密码 (password)
- 令牌 (token)
- 认证信息 (authorization, auth)

**示例:**
```
原始: api_key=sk-ant-1234567890abcdef
处理后: api_key=***MASKED***
```

### 文本长度限制

- 提示词和回复会被截断到最大10000字符
- 元数据中的敏感信息会被屏蔽
- 长文本会添加截断标记

## 使用示例

### 基本使用

聊天日志会自动记录所有通过 `llm_client.py` 的 LLM 调用：

```python
from llm_client import call_llm

# 这会自动记录到聊天日志
response = call_llm("请帮我写一段专利描述")
```

### 手动记录

```python
from chat_logger import get_chat_logger

logger = get_chat_logger()
logger.log_interaction(
    prompt="自定义提示词",
    response="自定义回复",
    metadata={"user": "admin", "session": "12345"},
    mode="manual"
)
```

### 查看统计信息

```python
from chat_logger import get_chat_logger

logger = get_chat_logger()
stats = logger.get_log_stats()

print(f"总交互次数: {stats['total_interactions']}")
print(f"日志文件数量: {stats['log_files_count']}")
```

## 故障排除

### 常见问题

1. **日志文件未创建**
   - 检查 `CHAT_LOG_ENABLED` 是否为 `true`
   - 确认目录权限是否正确
   - 检查磁盘空间是否充足

2. **日志记录不完整**
   - 检查是否有异常导致记录中断
   - 确认 LLM 调用是否通过 `llm_client.py`

3. **API 访问失败**
   - 确认服务器是否正在运行
   - 检查网络连接
   - 验证 API 端点路径

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 测试聊天日志
from test_chat_logging import main
main()
```

## 性能考虑

### 文件大小管理

- 单个日志文件没有大小限制，但会按日期分割
- 自动清理旧文件，保留最新的1000个文件
- 可以通过 `CHAT_LOG_MAX_FILES` 调整保留数量

### 并发安全

- 使用线程锁确保并发写入安全
- 文件操作使用原子操作
- 支持多进程并发访问

### 存储空间估算

- 平均每次交互约记录5KB数据
- 每天100次交互约产生500KB日志
- 1000个文件约占500MB空间

## 最佳实践

1. **定期检查**: 定期查看日志统计和文件大小
2. **备份重要日志**: 将重要的日志文件备份到其他位置
3. **监控存储空间**: 确保有足够的磁盘空间
4. **隐私保护**: 避免在提示词中包含敏感个人信息
5. **合理配置**: 根据使用频率调整文件保留数量

## 版本历史

- **v1.0.0**: 初始版本，支持基本的聊天日志记录
- 支持 SDK 和 CLI 模式的完整日志记录
- 提供 REST API 接口进行日志管理
- 自动敏感信息屏蔽
- 按日期分割日志文件
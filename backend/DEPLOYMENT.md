# 专利生成系统后端部署指南

## 快速开始

### 1. 环境要求

- Python 3.8+
- pip 包管理器
- Claude CLI 或其他 LLM 命令行工具

### 2. 安装依赖

```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，设置必要的配置
# 最重要的是设置 LLM_CMD
```

**必需配置:**
```bash
# 设置你的 LLM 命令
LLM_CMD=claude chat --model claude-3-5-sonnet
```

### 4. 启动服务器

#### 方法1: 使用启动脚本 (推荐)
```bash
python start_server.py
```

#### 方法2: 直接运行
```bash
python app.py
```

#### 方法3: Flask 开发模式
```bash
export FLASK_APP=app
flask run --host=0.0.0.0 --port=3000
```

### 5. 验证安装

访问以下端点验证服务器运行状态:

- **主页**: http://localhost:3000/
- **健康检查**: http://localhost:3000/api/health
- **任务统计**: http://localhost:3000/api/tasks/statistics

## 详细配置

### 环境变量配置

所有配置都可以通过环境变量设置。详见 `.env.example` 文件。

#### 关键配置项

```bash
# 服务器配置
HOST=0.0.0.0          # 监听地址
PORT=3000              # 监听端口
DEBUG=false            # 调试模式

# LLM 配置 (必需)
LLM_CMD=claude chat --model claude-3-5-sonnet  # LLM 命令
LLM_TIMEOUT=300        # LLM 超时时间 (秒)

# 任务管理
MAX_WORKERS=3          # 最大并发任务数
TASK_TIMEOUT=1800      # 任务超时时间 (秒)

# 安全配置
MAX_REQUEST_SIZE=2097152    # 最大请求大小 (2MB)
MAX_ITERATIONS=10          # 最大迭代次数
```

### LLM 工具配置

支持多种 LLM 工具:

#### Claude CLI
```bash
LLM_CMD=claude chat --model claude-3-5-sonnet
```

#### OpenAI CLI
```bash
LLM_CMD=openai api chat.completions.create --model gpt-4
```

#### Ollama
```bash
LLM_CMD=ollama run llama2
```

#### 自定义脚本
```bash
LLM_CMD=python your_llm_wrapper.py
```

## 生产部署

### 1. 使用 Gunicorn

```bash
# 安装 Gunicorn
pip install gunicorn gevent

# 启动服务器
gunicorn --bind 0.0.0.0:3000 --workers 4 --worker-class gevent app:app
```

### 2. 使用 Docker

创建 `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装 Python 依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制应用代码
COPY . .

# 创建输出目录
RUN mkdir -p output

# 暴露端口
EXPOSE 3000

# 设置环境变量
ENV HOST=0.0.0.0
ENV PORT=3000
ENV DEBUG=false

# 启动应用
CMD ["gunicorn", "--bind", "0.0.0.0:3000", "--workers", "4", "--worker-class", "gevent", "app:app"]
```

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  patent-backend:
    build: .
    ports:
      - "3000:3000"
    environment:
      - LLM_CMD=claude chat --model claude-3-5-sonnet
      - DEBUG=false
      - MAX_WORKERS=4
    volumes:
      - ./output:/app/output
      - ./logs:/app/logs
    restart: unless-stopped
```

### 3. 使用 systemd 服务

创建服务文件 `/etc/systemd/system/patent-generator.service`:

```ini
[Unit]
Description=Patent Generator Backend
After=network.target

[Service]
Type=exec
User=patent
Group=patent
WorkingDirectory=/opt/patent-generator/backend
Environment=HOST=0.0.0.0
Environment=PORT=3000
Environment=LLM_CMD=claude chat --model claude-3-5-sonnet
ExecStart=/opt/patent-generator/venv/bin/gunicorn --bind 0.0.0.0:3000 --workers 4 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务:

```bash
sudo systemctl enable patent-generator
sudo systemctl start patent-generator
sudo systemctl status patent-generator
```

## 监控和维护

### 1. 日志管理

日志文件位置:
- 应用日志: `patent_generator.log`
- 错误日志: 包含在应用日志中
- 访问日志: 控制台输出

### 2. 健康检查

定期检查服务状态:

```bash
# 检查服务健康状态
curl http://localhost:3000/api/health

# 检查任务统计
curl http://localhost:3000/api/tasks/statistics
```

### 3. 性能监控

监控指标:
- CPU 使用率
- 内存使用量
- 任务队列长度
- LLM 调用延迟
- 错误率

### 4. 备份策略

重要数据备份:
- 输出的专利文档
- 配置文件
- 日志文件

## 故障排除

### 常见问题

#### 1. LLM 命令未找到
```
错误: LLM 命令未配置
解决: 设置 LLM_CMD 环境变量
```

#### 2. 端口被占用
```
错误: Address already in use
解决: 更改 PORT 环境变量或停止占用端口的进程
```

#### 3. 权限问题
```
错误: Permission denied
解决: 检查文件和目录权限
```

#### 4. 内存不足
```
错误: MemoryError
解决: 减少 MAX_WORKERS 或增加系统内存
```

### 调试模式

启用调试模式获取详细错误信息:

```bash
export DEBUG=true
python app.py
```

## 安全注意事项

1. **生产环境安全**
   - 设置强密码的 SECRET_KEY
   - 禁用调试模式 (DEBUG=false)
   - 使用 HTTPS
   - 配置防火墙

2. **LLM 安全**
   - 验证 LLM 命令的安全性
   - 限制 LLM 访问权限
   - 监控 LLM 调用日志

3. **文件系统安全**
   - 限制输出目录访问权限
   - 定期清理临时文件
   - 监控磁盘空间

## API 文档

详细的 API 文档请参考:
- 在线文档: http://localhost:3000/docs (如果启用)
- API 示例: `examples/` 目录

## 支持

如需帮助，请:
1. 查看日志文件获取错误详情
2. 检查配置是否正确
3. 参考 GitHub Issues
4. 联系开发团队
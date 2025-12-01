# 提示词配置化管理指南

本指南详细介绍了专利生成系统的提示词配置化功能，该功能将硬编码的提示词移至外部配置文件，便于管理和维护。

## 功能概述

提示词配置化系统提供以下功能：
- **外部配置文件管理**：将提示词存储在 YAML 配置文件中
- **统一管理接口**：通过 PromptManager 统一加载和管理所有提示词
- **模板变量替换**：支持动态变量替换和条件逻辑
- **向后兼容**：保持与现有硬编码提示词的完全兼容
- **版本管理**：支持提示词版本控制和元数据管理

## 目录结构

```
prompts/
├── patent/
│   ├── writer/
│   │   └── base_prompt.yaml          # 专利撰写提示词
│   └── reviewer/
│       └── base_prompt.yaml          # 专利评审提示词
└── code/
    └── analyzer/
        └── base_prompt.yaml          # 代码分析提示词
```

## 配置文件格式

### 基本结构

每个提示词配置文件都包含以下部分：

```yaml
# 元数据
metadata:
  name: "提示词名称"
  version: "1.0.0"
  description: "提示词描述"
  author: "作者"
  created_date: "2024-12-01"
  tags: ["tag1", "tag2"]

# 提示词内容
prompt:
  role: "角色设定"
  objective: "目标说明"
  requirements: ["要求1", "要求2"]
  final_instruction: "最终指令"

# 上下文章节配置
context_sections:
  section_key:
    title: "章节标题"
    placeholder: "{{variable_name}}"
    condition: "variable_name"  # 可选：条件变量

# 迭代阶段配置
iteration_phases:
  first_iteration:
    instruction: "首次迭代指令"
  subsequent_iteration:
    instruction: "后续迭代指令"

# 变量说明
variables:
  variable_name:
    type: "string|int|bool"
    description: "变量描述"
    required: true|false
    example: "示例值"
```

### 专利撰写提示词示例

```yaml
# prompts/patent/writer/base_prompt.yaml
metadata:
  name: "专利撰写基础提示词"
  version: "1.0.0"
  description: "用于生成中国发明专利申请文档的基础提示词模板"

prompt:
  role: "你现在扮演一名资深的中国发明专利撰写专家。"
  objective: "目标：基于给定的技术背景和创新点，撰写一份结构完整、符合中国专利法和实务规范的发明专利草案。"
  requirements:
    - "使用 Markdown 编写完整专利文档；"
    - "章节建议包括但不限于：标题、技术领域、背景技术、发明内容、附图说明、具体实施方式、权利要求书、摘要；"
    - "所有图示必须使用 mermaid 语法的代码块"
  final_instruction: "请直接输出完整、可独立阅读的 Markdown 专利文档，不要额外附加解释说明。"

context_sections:
  tech_context:
    title: "【技术背景与创新点上下文】"
    placeholder: "{{context}}"
  previous_draft:
    title: "【上一版专利草案】"
    placeholder: "{{previous_draft}}"
    condition: "previous_draft"
  previous_review:
    title: "【合规评审与问题清单】"
    placeholder: "{{previous_review}}"
    condition: "previous_review"
```

## 使用方式

### 1. 基本使用

```python
from prompt_manager import get_prompt, PromptKeys

# 获取专利撰写提示词
writer_prompt = get_prompt(
    PromptKeys.PATENT_WRITER,
    context="技术背景和创新点内容",
    previous_draft="上一版草案（可选）",
    previous_review="评审意见（可选）",
    iteration=1,
    total_iterations=3
)

# 获取专利评审提示词
reviewer_prompt = get_prompt(
    PromptKeys.PATENT_REVIEWER,
    context="技术背景和创新点内容",
    current_draft="当前专利草案",
    iteration=1,
    total_iterations=3
)
```

### 2. 直接使用 PromptManager

```python
from prompt_manager import get_prompt_manager

manager = get_prompt_manager()

# 获取所有提示词列表
prompts = manager.list_prompts()
print(f"共加载 {len(prompts)} 个提示词")

# 获取特定提示词
prompt = manager.get_prompt("patent.writer.base_prompt", context="测试上下文")

# 验证提示词
validation = manager.validate_prompt("patent.writer.base_prompt", context="测试")
if validation['valid']:
    print("提示词验证通过")
else:
    print(f"验证失败: {validation['error']}")

# 重新加载配置
manager.reload_prompts()
```

### 3. 在现有代码中使用

现有的 `patent_workflow.py` 和 `code_analyzer.py` 已经更新为使用配置化提示词，同时保持向后兼容：

```python
# patent_workflow.py
def build_writer_prompt(context, previous_draft, previous_review, iteration, total_iterations):
    try:
        # 使用配置化提示词
        return get_prompt(PromptKeys.PATENT_WRITER, ...)
    except Exception:
        # 回退到硬编码提示词
        return _build_writer_prompt_fallback(...)
```

## 配置选项

### 环境变量配置

在 `.env` 文件中添加以下配置：

```env
# 提示词配置
PROMPTS_DIR=prompts              # 提示词目录
PROMPT_AUTO_RELOAD=true         # 自动重新加载
PROMPT_CACHE_ENABLED=true       # 启用缓存
PROMPT_VALIDATE_ON_LOAD=true    # 加载时验证
PROMPT_STRICT_MODE=false        # 严格模式
```

### 配置说明

- **PROMPTS_DIR**: 提示词配置文件目录（默认: prompts）
- **PROMPT_AUTO_RELOAD**: 是否自动重新加载配置（默认: true）
- **PROMPT_CACHE_ENABLED**: 是否启用提示词缓存（默认: true）
- **PROMPT_VALIDATE_ON_LOAD**: 加载时是否验证提示词（默认: true）
- **PROMPT_STRICT_MODE**: 严格模式，验证失败时抛出异常（默认: false）

## 模板变量

### 支持的变量类型

- **字符串变量**: `{{variable_name}}`
- **条件变量**: 根据变量是否存在决定是否包含章节
- **内置变量**: `iteration`, `total_iterations`

### 常用变量

| 变量名 | 类型 | 必需 | 描述 | 示例 |
|--------|------|------|------|------|
| context | string | 是 | 技术背景和创新点 | "这是一个创新的技术方案..." |
| previous_draft | string | 否 | 上一版专利草案 | "上一版本的专利内容..." |
| previous_review | string | 否 | 上一轮评审意见 | "需要改进以下几点..." |
| current_draft | string | 否 | 当前待评审草案 | "当前的专利草案..." |
| iteration | int | 是 | 当前迭代轮次 | 1 |
| total_iterations | int | 是 | 总迭代轮次 | 3 |

### 条件逻辑

```yaml
context_sections:
  previous_draft:
    title: "【上一版专利草案】"
    placeholder: "{{previous_draft}}"
    condition: "previous_draft"  # 只有当 previous_draft 存在时才包含
```

## 提示词键名

系统定义了以下标准提示词键名：

```python
class PromptKeys:
    PATENT_WRITER = "patent.writer.base_prompt"
    PATENT_REVIEWER = "patent.reviewer.base_prompt"
    CODE_ANALYZER = "code.analyzer.base_prompt"
```

## 向后兼容

系统完全向后兼容，当配置化提示词加载失败时，会自动回退到硬编码提示词：

```python
try:
    # 尝试使用配置化提示词
    prompt = get_prompt(key, **variables)
except Exception as e:
    logger.warning(f"使用配置化提示词失败，回退到硬编码提示词: {e}")
    prompt = _fallback_prompt(**variables)
```

## 错误处理

### 常见错误

1. **配置文件不存在**
   - 系统会自动回退到硬编码提示词
   - 记录警告日志

2. **YAML 格式错误**
   - 检查 YAML 语法和缩进
   - 使用 YAML 验证工具

3. **变量缺失**
   - 检查必需的变量是否提供
   - 使用验证功能检查变量

4. **权限问题**
   - 确保提示词目录可读
   - 检查文件权限设置

### 调试技巧

1. **启用详细日志**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **使用测试脚本**
   ```bash
   python test_prompt_config.py
   ```

3. **检查配置加载**
   ```python
   manager = get_prompt_manager()
   stats = manager.get_prompt_stats()
   print(stats)
   ```

## 最佳实践

### 1. 提示词设计

- 保持提示词简洁明了
- 使用清晰的变量占位符
- 提供详细的元数据信息
- 包含版本信息和更新日期

### 2. 变量管理

- 为变量提供清晰的描述和示例
- 区分必需和可选变量
- 使用一致的变量命名规范

### 3. 版本控制

- 更新提示词时递增版本号
- 在描述中记录变更内容
- 保留旧版本以备回退

### 4. 测试验证

- 使用测试脚本验证提示词加载
- 定期检查变量替换结果
- 测试错误回退机制

## 故障排除

### 问题诊断

1. **检查提示词目录**
   ```bash
   ls -la prompts/
   ```

2. **验证 YAML 格式**
   ```bash
   python -c "import yaml; yaml.safe_load(open('prompts/patent/writer/base_prompt.yaml'))"
   ```

3. **运行测试脚本**
   ```bash
   python test_prompt_config.py
   ```

4. **检查日志输出**
   查看系统日志中的提示词加载信息

### 性能优化

- 启用提示词缓存减少文件 I/O
- 合理设置提示词目录结构
- 避免过于复杂的条件逻辑

## 扩展开发

### 添加新提示词

1. 创建新的 YAML 配置文件
2. 在 `PromptKeys` 类中添加键名常量
3. 更新相应的业务代码
4. 添加测试用例

### 自定义模板引擎

可以扩展 `PromptManager` 以支持更复杂的模板引擎，如 Jinja2：

```python
from jinja2 import Template

def render_with_jinja2(template_str, **kwargs):
    template = Template(template_str)
    return template.render(**kwargs)
```

## 版本历史

- **v1.0.0**: 初始版本，支持基本的配置化提示词管理
- 支持专利撰写、评审和代码分析提示词
- 提供完整的向后兼容机制
- 包含详细的文档和测试工具
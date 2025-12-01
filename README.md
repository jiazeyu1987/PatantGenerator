# 自动专利生成系统（基于 Claude CLI 可集成）

本项目基于你的需求，在 `D:\ProjectPackage\PatantGenerator` 下提供了一个可扩展的专利生成系统骨架，支持：

- 两种输入方式：
  - 代码模式：自动递归分析指定目录下的代码文件，构造“代码概览 + 片段”上下文供大模型提取创新点；
  - 创意模式：直接基于用户输入的 idea / 需求文本生成专利；
- 两个角色、可配置多轮迭代：
  - 角色 A：专利撰写专家（Writer）；
  - 角色 B：合规 / 挑毛病专家（Reviewer）；
  - 前端可以配置迭代轮数，每轮包含一次撰写 + 一次评审；
- 输出一个 Markdown 专利文档，其中的图示通过 `mermaid` 代码块表示。

目前未直接访问 `doc` 目录中的中文说明文件（Windows + CLI 编码限制），但整体设计已经按照你在描述中提出的功能要求进行抽象和实现，你可以根据那些文档再做微调。

## 目录结构

- `backend/`
  - `package.json`：后端依赖与启动脚本（Node.js + Express）。
  - `server.js`：HTTP API + 静态前端托管。
  - `codeAnalyzer.js`：代码模式下的代码扫描与上下文构造。
  - `llmClient.js`：通过命令行调用 Claude Code CLI / Claude CLI 的简单封装。
  - `patentWorkflow.js`：双角色多轮迭代流程与 Markdown 输出。
- `frontend/`
  - `index.html`：前端页面，提供模式选择、轮数配置、输出前缀等。
  - `main.js`：调用后端 `/api/generate` 接口，展示结果。
  - `style.css`：简单的深色 UI 样式。
- `output/`
  - 运行后自动创建，用于存放生成的 `.md` 专利文档。

## 后端运行方式

1. 进入后端目录并安装依赖（需本机 Node.js 环境）：

   ```bash
   cd backend
   npm install
   ```

2. 配置环境变量 `LLM_CMD`，用于通过命令行调用 Claude Code CLI / Claude CLI。要求：

   - 该命令从 **标准输入读取 prompt**；
   - 将模型回答输出到 **标准输出**；
   - 命令退出码为 0 表示成功。

   示例（根据你本机的 CLI 实际命令修改）：

   ```bash
   # 假设你的 CLI 支持：echo "prompt" | claude chat --model xxx
   # 则这里只需要给出不含 prompt 的那部分命令：
   set LLM_CMD=claude chat --model claude-3-5-sonnet
   ```

   然后在同一个终端里启动后端：

   ```bash
   npm start
   ```

3. 后端默认监听：`http://localhost:3000`，并自动托管 `frontend` 目录为静态页面。

## 前端使用方式

1. 在浏览器中打开：`http://localhost:3000`。
2. 在“输入模式”中选择：
   - **代码自动分析**：
     - `代码根目录` 默认是 `.`（即后端进程所在目录），你也可以填写相对路径；
   - **创意 / idea 文本**：
     - 在文本框中详细描述你的技术方案、业务流程、架构等。
3. 设置“迭代轮数”（例如 3），每轮会执行一次“撰写 + 评审”。
4. 可选填写“输出文件前缀”，例如 `code-patent` 或 `idea-patent`。
5. 点击“开始生成”，等待返回结果：
   - 页面会展示：
     - 迭代轮数；
     - 最终 Markdown 文件的路径（相对于项目根目录）；
     - 最后一轮合规评审的前 2000 字预览。
   - 实际完整专利文档会保存在 `output/` 目录下，如：
     - `output/patent-2025-12-01T00-30-00-000Z.md`

## 双角色多轮迭代设计说明

- 在 `backend/patentWorkflow.js` 中实现：
  - `buildWriterPrompt(...)`：
    - 将代码/创意上下文、上一轮草案、上一轮评审意见等信息组织成一个系统 prompt；
    - 要求模型输出完整的中文发明专利 Markdown 文档，并在“附图说明”等部分使用 `mermaid` 代码块绘制架构/流程图；
  - `buildReviewerPrompt(...)`：
    - 将当前草案 + 技术上下文传入，要求模型从合规/风险/清晰度等角度“挑毛病”，并给出结构化的问题清单和修改建议；
  - `runPatentIteration(context, iterations, baseName)`：
    - 循环 `iterations` 轮：
      - 先调用 Writer 生成/修订草案；
      - 再调用 Reviewer 给出评审意见；
    - 最终将最后一版草案作为成品 Markdown，写入 `output` 目录。

## 代码模式下的自动分析逻辑

- 由 `backend/codeAnalyzer.js` 提供：
  - 递归遍历给定根目录；
  - 忽略目录：`node_modules`、`.git`、`dist`、`build`、`out`、`.next` 等；
  - 只采样常见代码后缀：`.js`、`.ts`、`.py`、`.java`、`.go`、`.rs`、`.cpp` 等；
  - 对每个采样文件读取前若干行（默认 80 行），构造一个包含路径 + 片段的 Markdown 文本；
  - 在末尾附加一段说明，提示大模型“根据上述代码概览提取核心技术要点和创新点”。

模型在 Writer 角色中收到的上下文中，会包含这些片段，从而可以自动归纳创新点并撰写专利。

## 如何与 Claude Code CLI 更紧密集成

当前项目只做了一个最小的 CLI 封装（`llmClient.js`），你可以根据自己的 Claude Code CLI 实际用法进行替换或扩展，例如：

- 如果你的 CLI 支持类似：

  ```bash
  claude code --mode chat --model claude-3-5-sonnet
  ```

  并从 stdin 读 prompt，那么只需要把上面的命令配置到 `LLM_CMD` 即可。

- 如果 CLI 需要传入额外参数（比如温度、系统提示等），可以：
  - 在 `LLM_CMD` 中一并写入；
  - 或者修改 `backend/llmClient.js`，在调用时动态拼接这些参数。

你也可以把当前项目当成“前后端壳子”，在 Claude Code CLI 里打开整个文件夹，让 Claude 帮你继续细化 prompt、补充字段或接入你现有的 workflow。

## 后续可以扩展的方向

- 把 `doc` 目录中的接口/前端设计文档逐步映射为更细致的 API（例如任务队列、生成进度轮询等）；
- 在前端增加：
  - 阅读 / 预览最终 Markdown 的界面；
  - 内嵌 mermaid 渲染（用于直观查看系统结构图/流程图）；
- 增加任务记录（如写入一个 JSON 日志，记录每一轮 writer / reviewer 的输出，方便回溯）；
- 增加多模型支持、温度/长度/风格等高级参数配置。

如果你希望，我也可以在下一步帮你把某一部分（例如：更细的 API 设计、任务队列或 mermaid 预览前端）继续实现下去。


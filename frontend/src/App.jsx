import React, { useState } from "react";

function App() {
  const [mode, setMode] = useState("code");
  const [projectPath, setProjectPath] = useState(".");
  const [ideaText, setIdeaText] = useState("");
  const [iterations, setIterations] = useState(3);
  const [outputName, setOutputName] = useState("");
  const [status, setStatus] = useState("");
  const [resultText, setResultText] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (mode === "idea" && !ideaText.trim()) {
      // eslint-disable-next-line no-alert
      alert("请先填写创意 / 需求描述。");
      return;
    }

    setStatus("正在提交任务，请稍候...");
    setLoading(true);
    setResultText("");

    try {
      const response = await fetch("/api/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          mode,
          projectPath,
          ideaText,
          iterations: Number(iterations) || 1,
          outputName
        })
      });

      const data = await response.json();

      if (!response.ok || !data.ok) {
        throw new Error(data.message || data.error || "生成失败");
      }

      setStatus("生成完成。");

      const lines = [];
      lines.push(`迭代轮数：${data.iterations}`);
      lines.push(`输出文件：${data.outputPath}`);
      if (data.lastReviewPreview) {
        lines.push("");
        lines.push("最后一轮合规评审预览（前 2000 字）：");
        lines.push(data.lastReviewPreview);
      }

      setResultText(lines.join("\n"));
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error(error);
      setStatus("生成出错。");
      setResultText(`错误：${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header>
        <h1>自动专利生成系统</h1>
        <p>基于代码/创意 + 双角色多轮迭代 + Claude CLI</p>
      </header>

      <main>
        <section className="card">
          <form onSubmit={handleSubmit}>
            <div className="field">
              <label>输入模式</label>
              <div className="inline-options">
                <label>
                  <input
                    type="radio"
                    name="mode"
                    value="code"
                    checked={mode === "code"}
                    onChange={() => setMode("code")}
                  />
                  代码自动分析
                </label>
                <label>
                  <input
                    type="radio"
                    name="mode"
                    value="idea"
                    checked={mode === "idea"}
                    onChange={() => setMode("idea")}
                  />
                  创意 / idea 文本
                </label>
              </div>
            </div>

            {mode === "code" ? (
              <div className="field">
                <label htmlFor="projectPath">代码根目录（相对路径）</label>
                <input
                  id="projectPath"
                  type="text"
                  value={projectPath}
                  onChange={(event) => setProjectPath(event.target.value)}
                />
                <small>默认当前项目目录，会自动递归分析常见代码文件。</small>
              </div>
            ) : (
              <div className="field">
                <label htmlFor="ideaText">创意 / 需求描述</label>
                <textarea
                  id="ideaText"
                  rows={6}
                  placeholder="在这里详细描述你的技术方案、业务流程、系统架构等信息，系统会自动提取创新点并撰写专利。"
                  value={ideaText}
                  onChange={(event) => setIdeaText(event.target.value)}
                />
              </div>
            )}

            <div className="field">
              <label htmlFor="iterations">迭代轮数（写作 + 合规评审）</label>
              <input
                id="iterations"
                type="number"
                min={1}
                max={10}
                value={iterations}
                onChange={(event) => setIterations(event.target.value)}
              />
              <small>每一轮包含一次“专利撰写” + 一次“合规挑毛病/评审”。</small>
            </div>

            <div className="field">
              <label htmlFor="outputName">输出文件前缀（可选）</label>
              <input
                id="outputName"
                type="text"
                placeholder="如：code-patent 或 idea-patent"
                value={outputName}
                onChange={(event) => setOutputName(event.target.value)}
              />
            </div>

            <div className="actions">
              <button type="submit" disabled={loading}>
                {loading ? "生成中..." : "开始生成"}
              </button>
              <span id="status-text">{status}</span>
            </div>
          </form>
        </section>

        <section className="card">
          <h2>运行结果</h2>
          <div id="result">
            {resultText ? (
              <pre>{resultText}</pre>
            ) : (
              <p>提交任务后，这里会显示生成状态和输出文件路径。</p>
            )}
          </div>
        </section>
      </main>

      <footer>
        <small>
          请先在环境变量中配置 <code>LLM_CMD</code>，指向 Claude Code CLI / Claude
          CLI 的命令。
        </small>
      </footer>
    </div>
  );
}

export default App;


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

  // 设置相关状态
  const [showSettings, setShowSettings] = useState(false);
  const [activeTab, setActiveTab] = useState("writer");
  const [userPrompts, setUserPrompts] = useState({
    writer: "",
    reviewer: ""
  });

  // 加载用户提示词
  const loadUserPrompts = async () => {
    try {
      const response = await fetch("/api/user/prompts");
      const data = await response.json();

      if (data.success) {
        setUserPrompts(data.data.prompts);
      }
    } catch (error) {
      console.error("加载用户提示词失败:", error);
    }
  };

  // 保存用户提示词
  const saveUserPrompts = async (prompts) => {
    try {
      const response = await fetch("/api/user/prompts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(prompts)
      });

      const data = await response.json();

      if (data.success) {
        setUserPrompts(prompts);
        return true;
      } else {
        console.error("保存用户提示词失败:", data.error);
        return false;
      }
    } catch (error) {
      console.error("保存用户提示词失败:", error);
      return false;
    }
  };

  // 组件加载时获取用户提示词
  React.useEffect(() => {
    loadUserPrompts();
  }, []);

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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h1>自动专利生成系统</h1>
            <p>基于代码/创意 + 双角色多轮迭代 + Claude CLI</p>
          </div>
          <button
            type="button"
            onClick={() => setShowSettings(true)}
            style={{
              padding: "8px 16px",
              backgroundColor: "#3b82f6",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "14px"
            }}
          >
            ⚙️ 提示词设置
          </button>
        </div>
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

      {/* 设置弹窗 */}
      {showSettings && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            backgroundColor: "rgba(0, 0, 0, 0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowSettings(false);
            }
          }}
        >
          <div
            style={{
              backgroundColor: "#020617",
              border: "1px solid #1f2937",
              borderRadius: "12px",
              padding: "24px",
              width: "90%",
              maxWidth: "800px",
              maxHeight: "80vh",
              overflow: "auto"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
              <h2 style={{ margin: 0, color: "#e5e7eb" }}>提示词设置</h2>
              <button
                onClick={() => setShowSettings(false)}
                style={{
                  background: "none",
                  border: "none",
                  color: "#9ca3af",
                  fontSize: "24px",
                  cursor: "pointer"
                }}
              >
                ×
              </button>
            </div>

            {/* 标签页 */}
            <div style={{ marginBottom: "20px" }}>
              <button
                onClick={() => setActiveTab("writer")}
                style={{
                  padding: "8px 16px",
                  backgroundColor: activeTab === "writer" ? "#3b82f6" : "#1f2937",
                  color: "#e5e7eb",
                  border: "none",
                  borderRadius: "6px 0 0 6px",
                  cursor: "pointer",
                  marginRight: "2px"
                }}
              >
                撰写者提示词
              </button>
              <button
                onClick={() => setActiveTab("reviewer")}
                style={{
                  padding: "8px 16px",
                  backgroundColor: activeTab === "reviewer" ? "#3b82f6" : "#1f2937",
                  color: "#e5e7eb",
                  border: "none",
                  borderRadius: "0 6px 6px 0",
                  cursor: "pointer"
                }}
              >
                审核者提示词
              </button>
            </div>

            {/* 编辑器 */}
            <div style={{ marginBottom: "20px" }}>
              <div style={{ marginBottom: "10px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <label style={{ color: "#9ca3af", fontSize: "14px" }}>
                  {activeTab === "writer" ? "撰写者提示词" : "审核者提示词"}
                </label>
                <span style={{ color: "#6b7280", fontSize: "12px" }}>
                  {userPrompts[activeTab].length} 字符
                </span>
              </div>
              <textarea
                value={userPrompts[activeTab]}
                onChange={(e) => setUserPrompts(prev => ({
                  ...prev,
                  [activeTab]: e.target.value
                }))}
                placeholder={`请输入${activeTab === "writer" ? "撰写者" : "审核者"}提示词...`}
                style={{
                  width: "100%",
                  height: "300px",
                  backgroundColor: "#020617",
                  color: "#e5e7eb",
                  border: "1px solid #374151",
                  borderRadius: "6px",
                  padding: "12px",
                  fontFamily: "monospace",
                  fontSize: "14px",
                  resize: "vertical"
                }}
              />
            </div>

            {/* 操作按钮 */}
            <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
              <button
                onClick={() => {
                  if (confirm("确定要重置为默认提示词吗？")) {
                    setUserPrompts(prev => ({
                      ...prev,
                      [activeTab]: ""
                    }));
                  }
                }}
                style={{
                  padding: "8px 16px",
                  backgroundColor: "#374151",
                  color: "#e5e7eb",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer"
                }}
              >
                重置为默认
              </button>
              <button
                onClick={async () => {
                  const success = await saveUserPrompts(userPrompts);
                  if (success) {
                    alert("提示词保存成功！");
                    setShowSettings(false);
                  } else {
                    alert("提示词保存失败，请重试。");
                  }
                }}
                style={{
                  padding: "8px 16px",
                  backgroundColor: "#3b82f6",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer"
                }}
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;


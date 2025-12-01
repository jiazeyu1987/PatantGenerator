import React, { useState, useEffect } from "react";
import TemplateSelector from "./TemplateSelector";
import ConversationViewer from "./ConversationViewer";

function PatentApp() {
  const [mode, setMode] = useState("code");
  const [projectPath, setProjectPath] = useState("..");
  const [ideaText, setIdeaText] = useState("");
  const [iterations, setIterations] = useState(3);
  const [outputName, setOutputName] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [status, setStatus] = useState("");
  const [resultText, setResultText] = useState("");
  const [loading, setLoading] = useState(false);
  const [useAsync, setUseAsync] = useState(true); // 默认使用异步模式
  const [currentTask, setCurrentTask] = useState(null);
  const [progress, setProgress] = useState(0);
  const [currentTaskId, setCurrentTaskId] = useState(null); // 用于对话查看器
  const [showConversation, setShowConversation] = useState(false); // 控制对话查看器显示

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
  useEffect(() => {
    loadUserPrompts();
  }, []);

  // 轮询任务状态
  const pollTaskStatus = async (taskId) => {
    const maxAttempts = 600; // 最多轮询10分钟
    let attempts = 0;

    const poll = async () => {
      try {
        let response;
        try {
          response = await fetch(`/api/tasks/${taskId}`);
        } catch (networkError) {
          throw new Error(`无法连接到服务器: ${networkError.message}`);
        }

        // 检查响应状态
        if (!response.ok) {
          let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
          try {
            const errorText = await response.text();
            if (errorText) {
              errorMessage = `查询任务状态失败: ${errorText}`;
            }
          } catch (e) {
            // 无法读取响应体
          }
          throw new Error(errorMessage);
        }

        // 解析JSON响应
        let data;
        try {
          const responseText = await response.text();
          if (!responseText.trim()) {
            throw new Error("服务器返回空响应");
          }
          data = JSON.parse(responseText);
        } catch (parseError) {
          throw new Error(`任务状态响应解析失败: ${parseError.message}`);
        }

        setCurrentTask(data);
        setProgress(data.progress || 0);
        setStatus(data.message || `任务进行中... (${data.progress || 0}%)`);

        if (data.status === "completed") {
          let resultText = `任务完成！\n\n输出文件：${data.result.outputPath}\n迭代轮数：${data.result.iterations}`;

          // 如果使用了模板，添加 DOCX 文件信息
          if (data.result.docx_path) {
            resultText += `\nDOCX 文件：${data.result.docx_path}`;
            if (data.result.template_used) {
              resultText += `\n使用模板：${data.result.template_id || '未知'}`;
            }
          }

          resultText += `\n\n最后一轮评审预览：\n${data.result.lastReview ? data.result.lastReview.substring(0, 1000) + "..." : "无"}`;

          setResultText(resultText);
          setLoading(false);

          // 保存task_id并显示对话查看器
          if (data.result && data.result.task_id) {
            setCurrentTaskId(data.result.task_id);
            setShowConversation(true);
          }

          return true;
        } else if (data.status === "failed") {
          throw new Error(data.error || "任务执行失败");
        } else if (data.status === "cancelled") {
          setStatus("任务已取消");
          setLoading(false);
          return true;
        }

        return false;
      } catch (error) {
        console.error("轮询任务状态失败:", error);
        throw error;
      }
    };

    while (attempts < maxAttempts) {
      const isComplete = await poll();
      if (isComplete) break;

      attempts++;
      await new Promise(resolve => setTimeout(resolve, 2000)); // 每2秒轮询一次
    }

    if (attempts >= maxAttempts) {
      throw new Error("任务执行超时");
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (mode === "idea" && !ideaText.trim()) {
      // eslint-disable-next-line no-alert
      alert("请先填写创意 / 需求描述。");
      return;
    }

    setLoading(true);
    setResultText("");
    setProgress(0);
    setCurrentTask(null);

    try {
      if (useAsync) {
        // 使用异步 API
        setStatus("正在提交异步任务...");

        let response;
        try {
          response = await fetch("/api/generate/async", {
            method: "POST",
            headers: {
              "Content-Type": "application/json"
            },
            body: JSON.stringify({
              mode,
              projectPath,
              ideaText,
              iterations: Number(iterations) || 1,
              outputName,
              templateId: selectedTemplateId || null
            })
          });
        } catch (networkError) {
          throw new Error(`网络连接失败: ${networkError.message}. 请检查后端服务器是否正在运行。`);
        }

        // 检查响应状态
        if (!response.ok) {
          // 尝试获取错误信息
          let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
          try {
            const errorText = await response.text();
            if (errorText) {
              // 尝试解析JSON错误响应
              try {
                const errorJson = JSON.parse(errorText);
                if (errorJson.message) {
                  errorMessage = errorJson.message;
                } else {
                  errorMessage = `服务器错误: ${errorText}`;
                }
              } catch {
                // 如果不是JSON，直接使用原始文本
                errorMessage = `服务器错误: ${errorText}`;
              }
            }
          } catch (e) {
            // 无法读取响应体
          }
          throw new Error(errorMessage);
        }

        // 解析JSON响应
        let data;
        try {
          const responseText = await response.text();
          if (!responseText.trim()) {
            throw new Error("服务器返回空响应");
          }
          data = JSON.parse(responseText);
        } catch (parseError) {
          throw new Error(`响应解析失败: ${parseError.message}. 服务器可能返回了非JSON格式的响应。`);
        }

        if (!data.ok) {
          throw new Error(data.message || data.error || "任务提交失败");
        }

        setStatus(`任务已提交，任务ID: ${data.taskId}`);

        // 开始轮询任务状态
        await pollTaskStatus(data.taskId);

      } else {
        // 使用同步 API（兼容旧版本）
        setStatus("正在处理请求，请稍候...");

        let response;
        try {
          response = await fetch("/api/generate", {
            method: "POST",
            headers: {
              "Content-Type": "application/json"
            },
            body: JSON.stringify({
              mode,
              projectPath,
              ideaText,
              iterations: Number(iterations) || 1,
              outputName,
              templateId: selectedTemplateId || null
            })
          });
        } catch (networkError) {
          throw new Error(`网络连接失败: ${networkError.message}. 请检查后端服务器是否正在运行。`);
        }

        // 检查响应状态
        if (!response.ok) {
          // 尝试获取错误信息
          let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
          try {
            const errorText = await response.text();
            if (errorText) {
              // 尝试解析JSON错误响应
              try {
                const errorJson = JSON.parse(errorText);
                if (errorJson.message) {
                  errorMessage = errorJson.message;
                } else {
                  errorMessage = `服务器错误: ${errorText}`;
                }
              } catch {
                // 如果不是JSON，直接使用原始文本
                errorMessage = `服务器错误: ${errorText}`;
              }
            }
          } catch (e) {
            // 无法读取响应体
          }
          throw new Error(errorMessage);
        }

        // 解析JSON响应
        let data;
        try {
          const responseText = await response.text();
          if (!responseText.trim()) {
            throw new Error("服务器返回空响应");
          }
          data = JSON.parse(responseText);
        } catch (parseError) {
          throw new Error(`响应解析失败: ${parseError.message}. 服务器可能返回了非JSON格式的响应。`);
        }

        if (!data.ok) {
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
      }
    } catch (error) {
      console.error(error);
      setStatus("生成出错。");
      setResultText(`错误：${error.message}`);
    } finally {
      setLoading(false);
      setProgress(0);
      setCurrentTask(null);
    }
  };

  const handleCancel = async () => {
    if (!currentTask || !currentTask.taskId) return;

    try {
      let response;
      try {
        response = await fetch(`/api/tasks/${currentTask.taskId}/cancel`, {
          method: "POST"
        });
      } catch (networkError) {
        throw new Error(`网络连接失败: ${networkError.message}`);
      }

      // 检查响应状态
      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorText = await response.text();
          if (errorText) {
            errorMessage = `取消任务失败: ${errorText}`;
          }
        } catch (e) {
          // 无法读取响应体
        }
        throw new Error(errorMessage);
      }

      // 解析JSON响应
      let data;
      try {
        const responseText = await response.text();
        if (!responseText.trim()) {
          throw new Error("服务器返回空响应");
        }
        data = JSON.parse(responseText);
      } catch (parseError) {
        throw new Error(`取消任务响应解析失败: ${parseError.message}`);
      }

      if (!data.ok) {
        throw new Error(data.message || data.error || "取消任务失败");
      }

      setStatus("任务已取消");
      setLoading(false);
      setProgress(0);
      setCurrentTask(null);
    } catch (error) {
      console.error("取消任务失败:", error);
      setStatus(`取消任务失败: ${error.message}`);
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

            <div className="field">
              <label>处理模式</label>
              <div className="inline-options">
                <label>
                  <input
                    type="radio"
                    name="processMode"
                    value="async"
                    checked={useAsync}
                    onChange={() => setUseAsync(true)}
                  />
                  异步处理 (推荐)
                </label>
                <label>
                  <input
                    type="radio"
                    name="processMode"
                    value="sync"
                    checked={!useAsync}
                    onChange={() => setUseAsync(false)}
                  />
                  同步处理
                </label>
              </div>
              <small>
                {useAsync
                  ? "异步模式：提交任务后可实时查看进度，支持取消操作"
                  : "同步模式：等待任务完成后返回结果"}
              </small>
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

            <TemplateSelector
              selectedTemplateId={selectedTemplateId}
              onTemplateChange={setSelectedTemplateId}
              disabled={loading}
            />

            <div className="actions">
              <button type="submit" disabled={loading}>
                {loading ? "处理中..." : "开始生成"}
              </button>
              {loading && useAsync && currentTask && (
                <button type="button" onClick={handleCancel} className="cancel-btn">
                  取消任务
                </button>
              )}
            </div>

            {/* 进度条 */}
            {loading && useAsync && (
              <div className="progress-container">
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                <div className="progress-text">
                  {status} ({progress}%)
                </div>
                {currentTask && (
                  <div className="task-info">
                    <small>任务ID: {currentTask.taskId}</small>
                    {currentTask.createdAt && (
                      <small>创建时间: {new Date(currentTask.createdAt).toLocaleTimeString()}</small>
                    )}
                  </div>
                )}
              </div>
            )}

            {!loading && status && (
              <div className="status-message">{status}</div>
            )}
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

        {/* 对话查看器 */}
        <ConversationViewer
          taskId={currentTaskId}
          visible={showConversation}
        />
      </main>

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

      <footer>
        <small>
          请先在环境变量中配置 <code>LLM_CMD</code>，指向 Claude Code CLI / Claude CLI
          的命令。
        </small>
      </footer>
    </div>
  );
}

export default PatentApp;


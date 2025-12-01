function $(selector) {
  return document.querySelector(selector);
}

function updateModeVisibility(mode) {
  const codeField = $("#code-path-field");
  const ideaField = $("#idea-field");

  if (mode === "code") {
    codeField.classList.remove("hidden");
    ideaField.classList.add("hidden");
  } else {
    codeField.classList.add("hidden");
    ideaField.classList.remove("hidden");
  }
}

window.addEventListener("DOMContentLoaded", () => {
  const form = $("#generator-form");
  const statusText = $("#status-text");
  const resultBox = $("#result");
  const submitBtn = $("#submit-btn");

  const modeRadios = document.querySelectorAll('input[name="mode"]');
  modeRadios.forEach((radio) => {
    radio.addEventListener("change", () => {
      updateModeVisibility(radio.value);
    });
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const mode = document.querySelector('input[name="mode"]:checked').value;
    const projectPath = $("#projectPath").value.trim();
    const ideaText = $("#ideaText").value.trim();
    const iterations = parseInt($("#iterations").value, 10) || 1;
    const outputName = $("#outputName").value.trim();

    if (mode === "idea" && !ideaText) {
      alert("请先填写创意 / 需求描述。");
      return;
    }

    statusText.textContent = "正在提交任务，请稍候...";
    submitBtn.disabled = true;
    resultBox.textContent = "";

    try {
      const resp = await fetch("/api/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          mode,
          projectPath,
          ideaText,
          iterations,
          outputName
        })
      });

      const data = await resp.json();

      if (!resp.ok || !data.ok) {
        throw new Error(data.message || data.error || "生成失败");
      }

      statusText.textContent = "生成完成。";

      const lines = [];
      lines.push(`迭代轮数：${data.iterations}`);
      lines.push(`输出文件：${data.outputPath}`);
      if (data.lastReviewPreview) {
        lines.push("");
        lines.push("最后一轮合规评审预览（前 2000 字）：");
        lines.push(data.lastReviewPreview);
      }

      resultBox.textContent = lines.join("\n");
    } catch (err) {
      console.error(err);
      statusText.textContent = "生成出错。";
      resultBox.textContent = `错误：${err.message}`;
    } finally {
      submitBtn.disabled = false;
    }
  });
});


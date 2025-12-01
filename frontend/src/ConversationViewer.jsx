import React, { useState, useEffect } from "react";
import { Select, Card, Typography, Spin, Alert, Divider, Space } from "antd";

const { Option } = Select;
const { Text, Paragraph } = Typography;

function ConversationViewer({ taskId, visible }) {
  const [rounds, setRounds] = useState([]);
  const [selectedRound, setSelectedRound] = useState(null);
  const [selectedRole, setSelectedRole] = useState("writer");
  const [conversation, setConversation] = useState(null);
  const [roundConversations, setRoundConversations] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // 角色选项
  const roleOptions = [
    { value: "writer", label: "撰写者" },
    { value: "modifier", label: "修改者" },
    { value: "reviewer", label: "审批者" }
  ];

  // 当taskId变化时，加载轮次数据
  useEffect(() => {
    if (taskId && visible) {
      loadTaskRounds();
    } else {
      // 重置状态
      setRounds([]);
      setSelectedRound(null);
      setConversation(null);
      setRoundConversations(null);
      setError("");
    }
  }, [taskId, visible]);

  // 当选择的轮次或角色变化时，加载对话数据
  useEffect(() => {
    if (selectedRound !== null) {
      // 根据轮次自动调整角色选择
      if (selectedRound === 1) {
        // 第一轮：默认选择撰写者
        if (selectedRole === "modifier") {
          setSelectedRole("writer");
        }
      } else {
        // 第二轮及以后：默认选择修改者
        if (selectedRole === "writer") {
          setSelectedRole("modifier");
        }
      }
      loadConversation();
    }
  }, [selectedRound, selectedRole, taskId]);

  // 加载任务的所有轮次
  const loadTaskRounds = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`/api/conversations/tasks/${taskId}/rounds`);
      const data = await response.json();

      if (data.success) {
        setRounds(data.data);
        if (data.data.length > 0) {
          setSelectedRound(data.data[0]); // 默认选择第一轮
        } else {
          setError("该任务暂无对话数据");
        }
      } else {
        setError(data.error || "加载轮次失败");
      }
    } catch (err) {
      console.error("加载轮次失败:", err);
      setError("网络错误，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  // 加载指定轮次和角色的对话
  const loadConversation = async () => {
    if (!taskId || selectedRound === null) return;

    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `/api/conversations/tasks/${taskId}/rounds/${selectedRound}`
      );
      const data = await response.json();

      if (data.success) {
        setRoundConversations(data.data);
        // 如果有当前角色的对话，显示它
        if (data.data[selectedRole]) {
          setConversation(data.data[selectedRole]);
        } else {
          setConversation(null);
        }
      } else {
        setError(data.error || "加载对话失败");
      }
    } catch (err) {
      console.error("加载对话失败:", err);
      setError("网络错误，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  // 格式化时间
  const formatTime = (timestamp) => {
    if (!timestamp) return "";
    try {
      return new Date(timestamp).toLocaleString("zh-CN");
    } catch {
      return timestamp;
    }
  };

  // 如果taskId不存在或不可见，不渲染内容
  if (!taskId || !visible) {
    return null;
  }

  return (
    <div className="conversation-viewer" style={{ marginTop: 24 }}>
      <Card
        title="多轮对话查看器"
        size="small"
        extra={
          <Space>
            <Select
              value={selectedRound}
              onChange={setSelectedRound}
              placeholder="选择轮次"
              style={{ width: 120 }}
              disabled={rounds.length === 0}
            >
              {rounds.map((round) => (
                <Option key={round} value={round}>
                  第 {round} 轮
                </Option>
              ))}
            </Select>

            <Select
              value={selectedRole}
              onChange={setSelectedRole}
              style={{ width: 100 }}
              disabled={!conversation}
            >
              {roleOptions.map((option) => (
                <Option key={option.value} value={option.value}>
                  {option.label}
                </Option>
              ))}
            </Select>
          </Space>
        }
      >
        {error && (
          <Alert
            message="错误"
            description={error}
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {loading ? (
          <div style={{ textAlign: "center", padding: 40 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>加载中...</div>
          </div>
        ) : conversation ? (
          <div>
            {/* 显示时间信息 */}
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {formatTime(conversation.timestamp)}
              </Text>
            </div>

            {/* 提示词部分 */}
            <div style={{ marginBottom: 24 }}>
              <Text strong style={{ fontSize: 14, color: "#1890ff" }}>
                提示词 ({selectedRole === "writer" ? "撰写者" : selectedRole === "modifier" ? "修改者" : "审批者"}):
              </Text>
              <div
                style={{
                  marginTop: 8,
                  padding: 12,
                  backgroundColor: "#f6f8fa",
                  borderRadius: 6,
                  border: "1px solid #e1e4e8",
                  fontFamily: "monospace",
                  fontSize: 12,
                  whiteSpace: "pre-wrap",
                  maxHeight: 200,
                  overflow: "auto"
                }}
              >
                {conversation.prompt}
              </div>
            </div>

            <Divider style={{ margin: "16px 0" }} />

            {/* LLM响应部分 */}
            <div>
              <Text strong style={{ fontSize: 14, color: "#52c41a" }}>
                LLM 返回:
              </Text>
              <div
                style={{
                  marginTop: 8,
                  padding: 12,
                  backgroundColor: "#f6ffed",
                  borderRadius: 6,
                  border: "1px solid #b7eb8f",
                  maxHeight: 400,
                  overflow: "auto"
                }}
              >
                <Paragraph
                  style={{
                    marginBottom: 0,
                    fontSize: 13,
                    lineHeight: 1.6,
                    whiteSpace: "pre-wrap"
                  }}
                >
                  {conversation.response}
                </Paragraph>
              </div>
            </div>
          </div>
        ) : !error && rounds.length === 0 ? (
          <div style={{ textAlign: "center", padding: 40, color: "#999" }}>
            <div>暂无对话数据</div>
            <div style={{ fontSize: 12, marginTop: 8 }}>
              生成专利后将显示详细的对话过程
            </div>
          </div>
        ) : !error && !conversation ? (
          <div style={{ textAlign: "center", padding: 40, color: "#999" }}>
            <div>该轮次暂无 {selectedRole === "writer" ? "撰写者" : selectedRole === "modifier" ? "修改者" : "审批者"} 对话</div>
          </div>
        ) : null}
      </Card>
    </div>
  );
}

export default ConversationViewer;
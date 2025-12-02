import React, { useState, useEffect } from 'react';

/**
 * 模板选择组件
 * 允许用户选择专利生成使用的模板
 */
function TemplateSelector({ selectedTemplateId, onTemplateChange, disabled = false }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [analysisResults, setAnalysisResults] = useState({});
  const [analyzingTemplates, setAnalyzingTemplates] = useState(new Set());

  // 加载模板列表
  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        setLoading(true);
        setError('');

        const response = await fetch('/api/templates/');

        if (!response.ok) {
          throw new Error(`获取模板列表失败: ${response.status}`);
        }

        const data = await response.json();

        if (!data.ok) {
          throw new Error(data.error || '获取模板列表失败');
        }

        setTemplates(data.templates || []);

        // 如果没有选择模板但有默认模板，自动选择默认模板
        if (!selectedTemplateId && data.default_template_id) {
          onTemplateChange(data.default_template_id);
        }

        // 自动加载已分析模板的分析结果
        const analysisPromises = data.templates
          .filter(template => template.has_analysis)
          .map(template => loadTemplateAnalysis(template.id));

        // 并行加载分析结果
        await Promise.allSettled(analysisPromises);
      } catch (err) {
        console.error('加载模板列表失败:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchTemplates();
  }, [selectedTemplateId, onTemplateChange]);

  // 处理模板选择变化
  const handleTemplateChange = (event) => {
    const templateId = event.target.value;
    onTemplateChange(templateId);

    // 自动加载分析结果（如果还没有的话）
    if (templateId && !analysisResults[templateId]) {
      loadTemplateAnalysis(templateId);
    }
  };

  // 加载模板分析结果
  const loadTemplateAnalysis = async (templateId) => {
    try {
      const response = await fetch(`/api/templates/${templateId}/analysis`);
      if (!response.ok) {
        return; // 忽略分析结果不存在的错误
      }

      const data = await response.json();
      if (data.ok && data.analysis) {
        setAnalysisResults(prev => ({
          ...prev,
          [templateId]: data.analysis
        }));
      }
    } catch (err) {
      console.warn(`加载模板分析结果失败 ${templateId}:`, err);
    }
  };

  // 分析指定模板
  const analyzeTemplate = async (templateId, event) => {
    // 防止事件冒泡和表单提交
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    console.log('🔍 [调试] 分析模板按钮被点击');
    console.log('🔍 [调试] 模板ID:', templateId);

    if (analyzingTemplates.has(templateId)) {
      console.log('⚠️ [调试] 模板正在分析中，跳过重复请求');
      return;
    }

    setAnalyzingTemplates(prev => new Set(prev).add(templateId));

    try {
      // 获取用户的模板分析提示词
      let customPrompt = null;
      try {
        console.log('🔍 [调试] 开始获取用户自定义提示词...');
        const promptsResponse = await fetch('/api/user/prompts');
        const promptsData = await promptsResponse.json();
        console.log('🔍 [调试] 用户提示词API响应:', promptsData);

        if (promptsData.success && promptsData.data && promptsData.data.prompts && promptsData.data.prompts.template) {
          customPrompt = promptsData.data.prompts.template;
          console.log('✅ [调试] 使用用户自定义模板分析提示词:', customPrompt);
        } else {
          console.log('ℹ️ [调试] 未找到用户自定义模板分析提示词，将使用默认提示词');
        }
      } catch (err) {
        console.warn('⚠️ [调试] 获取用户提示词失败，使用默认提示词:', err);
      }

      const requestBody = {
        template_id: templateId
      };

      // 如果提供了自定义提示词，添加到请求中
      if (customPrompt && customPrompt.trim()) {
        requestBody.custom_prompt = customPrompt;
      }

      console.log('📤 [调试] 发送模板分析请求:', JSON.stringify(requestBody, null, 2));

      const response = await fetch('/api/templates/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        console.error('❌ [调试] 模板分析请求失败，状态码:', response.status);
        throw new Error(`分析模板失败: ${response.status}`);
      }

      const data = await response.json();
      console.log('📥 [调试] 模板分析API响应:', JSON.stringify(data, null, 2));

      if (data.ok && data.analysis) {
        console.log('✅ [调试] 模板分析成功，更新分析结果');
        console.log('📊 [调试] 分析结果详情:', data.analysis);
        setAnalysisResults(prev => ({
          ...prev,
          [templateId]: data.analysis
        }));
      } else {
        console.warn('⚠️ [调试] 模板分析返回空结果或失败状态');
      }
    } catch (err) {
      console.error('❌ [调试] 分析模板失败:', err);
      console.error('❌ [调试] 错误详情:', err.message);
      console.error('❌ [调试] 错误堆栈:', err.stack);
      setError(`分析模板失败: ${err.message}`);
    } finally {
      setAnalyzingTemplates(prev => {
        const newSet = new Set(prev);
        newSet.delete(templateId);
        return newSet;
      });
    }
  };

  // 刷新模板列表
  const refreshTemplates = async () => {
    try {
      const response = await fetch('/api/templates/reload', { method: 'POST' });

      if (!response.ok) {
        throw new Error(`刷新模板列表失败: ${response.status}`);
      }

      const data = await response.json();

      if (!data.ok) {
        throw new Error(data.error || '刷新模板列表失败');
      }

      // 重新加载模板列表
      const templatesResponse = await fetch('/api/templates/');
      const templatesData = await templatesResponse.json();

      if (templatesData.ok) {
        setTemplates(templatesData.templates || []);
      }
    } catch (err) {
      console.error('刷新模板列表失败:', err);
      setError(err.message);
    }
  };

  if (loading) {
    return (
      <div className="field">
        <label>专利模板</label>
        <div className="template-loading">
          <span>正在加载模板列表...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="field">
        <label>专利模板</label>
        <div className="template-error">
          <span>加载失败: {error}</span>
          <button
            type="button"
            onClick={refreshTemplates}
            className="refresh-btn"
            disabled={disabled}
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  if (templates.length === 0) {
    return (
      <div className="field">
        <label>专利模板</label>
        <div className="template-empty">
          <span>暂无可用模板文件</span>
          <small>
            请将 .docx 模板文件放置在 <code>backend/templates_store</code> 目录下，
            然后点击刷新按钮重新加载。
          </small>
          <button
            type="button"
            onClick={refreshTemplates}
            className="refresh-btn"
            disabled={disabled}
          >
            刷新
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="field">
      <label htmlFor="templateSelect">专利模板</label>
      <div className="template-selector">
        <select
          id="templateSelect"
          value={selectedTemplateId || ''}
          onChange={handleTemplateChange}
          disabled={disabled}
        >
          <option value="">选择模板（可选）</option>
          {templates.map((template) => (
            <option key={template.id} value={template.id}>
              {template.name}
              {template.is_default && ' (默认)'}
              {!template.is_valid && ' [无效]'}
            </option>
          ))}
        </select>

        <button
          type="button"
          onClick={refreshTemplates}
          className="refresh-btn"
          title="刷新模板列表"
          disabled={disabled}
        >
          🔄
        </button>
      </div>

      {selectedTemplateId && (
        <div className="template-info">
          {(() => {
            const selectedTemplate = templates.find(t => t.id === selectedTemplateId);
            if (!selectedTemplate) return null;

            const analysis = analysisResults[selectedTemplateId];

            return (
              <div className="template-details">
                <div className="template-description">
                  {selectedTemplate.description || '无描述'}
                </div>
                <div className="template-meta">
                  <small>
                    状态: {selectedTemplate.is_valid ? '✅ 有效' : '❌ 无效'} |
                    占位符: {selectedTemplate.placeholder_count || 0} 个 |
                    章节数: {selectedTemplate.sections || 0} 个
                  </small>
                </div>

                {/* 分析结果展示 */}
                {analysis && (
                  <div className="template-analysis">
                    <div className="analysis-header">
                      <strong>模板分析结果</strong>
                      {analyzingTemplates.has(selectedTemplateId) && (
                        <span className="analyzing-indicator">分析中...</span>
                      )}
                    </div>

                    <div className="analysis-metrics">
                      {analysis.complexity_score !== undefined && (
                        <div className="metric">
                          <span className="metric-label">复杂度:</span>
                          <span className={`metric-value complexity-${analysis.complexity_score > 0.7 ? 'high' : analysis.complexity_score > 0.4 ? 'medium' : 'low'}`}>
                            {(analysis.complexity_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      )}
                      {analysis.quality_score !== undefined && (
                        <div className="metric">
                          <span className="metric-label">质量评分:</span>
                          <span className={`metric-value quality-${analysis.quality_score > 0.7 ? 'high' : analysis.quality_score > 0.4 ? 'medium' : 'low'}`}>
                            {(analysis.quality_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      )}
                      {analysis.placeholder_count !== undefined && (
                        <div className="metric">
                          <span className="metric-label">占位符数量:</span>
                          <span className="metric-value">{analysis.placeholder_count} 个</span>
                        </div>
                      )}
                      {analysis.file_size && (
                        <div className="metric">
                          <span className="metric-label">文件大小:</span>
                          <span className="metric-value">{(analysis.file_size / 1024).toFixed(1)} KB</span>
                        </div>
                      )}
                    </div>

                    {/* 详细分析结果 */}
                    {analysis.detailed_analysis && (
                      <div className="detailed-analysis">
                        <div className="analysis-content">
                          <div className="analysis-toggle">
                            <button
                              onClick={() => {
                                const content = document.querySelector('.analysis-content-text');
                                if (content.style.display === 'none') {
                                  content.style.display = 'block';
                                  event.target.textContent = '隐藏详细分析';
                                } else {
                                  content.style.display = 'none';
                                  event.target.textContent = '显示详细分析';
                                }
                              }}
                              className="toggle-btn"
                            >
                              显示详细分析
                            </button>
                          </div>
                          <pre className="analysis-content-text" style={{ display: 'none' }}>
                            {analysis.detailed_analysis}
                          </pre>
                        </div>
                      </div>
                    )}

                    <div className="analysis-actions">
                      <button
                        type="button"
                        onClick={(event) => analyzeTemplate(selectedTemplateId, event)}
                        className="analyze-btn"
                        disabled={analyzingTemplates.has(selectedTemplateId)}
                      >
                        {analyzingTemplates.has(selectedTemplateId) ? '分析中...' : '重新分析'}
                      </button>
                    </div>

                    {analysis.suggestions && analysis.suggestions.length > 0 && (
                      <div className="analysis-suggestions">
                        <strong>改进建议:</strong>
                        <ul>
                          {analysis.suggestions.slice(0, 2).map((suggestion, index) => (
                            <li key={index}>{suggestion}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* 如果没有分析结果，显示分析按钮 */}
                {!analysis && (
                  <div className="template-analysis-actions">
                    <button
                      type="button"
                      onClick={(event) => analyzeTemplate(selectedTemplateId, event)}
                      className="analyze-btn"
                      disabled={analyzingTemplates.has(selectedTemplateId)}
                    >
                      {analyzingTemplates.has(selectedTemplateId) ? '分析中...' : '分析模板'}
                    </button>
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      )}

      <small>
        选择模板后，生成的专利文档将按照选定模板的格式生成 DOCX 文件。
        如果不选择模板，将只生成 Markdown 格式文件。
      </small>
    </div>
  );
}

export default TemplateSelector;
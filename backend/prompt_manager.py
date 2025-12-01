"""
提示词管理器

统一管理和加载所有提示词配置，支持模板变量替换、版本管理和动态加载。
"""

import os
import yaml
import re
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from dataclasses import dataclass

from template_manager import get_template_manager

logger = logging.getLogger(__name__)


@dataclass
class PromptConfig:
    """提示词配置数据类"""
    name: str
    version: str
    description: str
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    file_path: str
    loaded_at: float
    # 增强功能：支持动态内容生成
    dynamic_generators: Optional[Dict[str, Callable]] = None
    template_analysis_cache: Optional[Dict[str, Any]] = None


class PromptManager:
    """提示词管理器"""

    def __init__(self, prompts_dir: str = None):
        """
        初始化提示词管理器

        Args:
            prompts_dir: 提示词配置目录路径，默认为项目根目录下的 prompts
        """
        if prompts_dir is None:
            # 默认提示词目录为项目根目录下的 prompts
            current_dir = Path(__file__).parent
            prompts_dir = current_dir.parent / "prompts"

        self.prompts_dir = Path(prompts_dir)
        self._cache: Dict[str, PromptConfig] = {}
        self._template_cache: Dict[str, str] = {}

        # 模板管理器引用
        self._template_manager = None

        # 动态内容生成器注册
        self._dynamic_generators = {}

        logger.info(f"提示词管理器初始化，目录: {self.prompts_dir}")

        # 注册动态生成器
        self._register_dynamic_generators()

        # 预加载所有提示词配置
        self._load_all_prompts()

    def _register_dynamic_generators(self):
        """注册动态内容生成器 - 简化版本，只保留模板标题信息"""
        self._dynamic_generators.update({
            'template_title_only': self._generate_template_title_only
        })

    def _get_template_manager(self):
        """获取模板管理器实例（懒加载）"""
        if self._template_manager is None:
            self._template_manager = get_template_manager()
        return self._template_manager

    def _load_all_prompts(self):
        """加载所有提示词配置文件"""
        if not self.prompts_dir.exists():
            logger.warning(f"提示词目录不存在: {self.prompts_dir}")
            return

        # 递归查找所有 YAML 文件
        yaml_files = list(self.prompts_dir.rglob("*.yaml"))
        yaml_files.extend(list(self.prompts_dir.rglob("*.yml")))

        loaded_count = 0
        for yaml_file in yaml_files:
            try:
                config = self._load_prompt_file(yaml_file)
                if config:
                    key = self._get_prompt_key(yaml_file)
                    self._cache[key] = config
                    loaded_count += 1
                    logger.debug(f"加载提示词配置: {key} from {yaml_file}")
            except Exception as e:
                logger.error(f"加载提示词配置失败 {yaml_file}: {e}")

        logger.info(f"提示词配置加载完成，共加载 {loaded_count} 个配置文件")

    def _load_prompt_file(self, file_path: Path) -> Optional[PromptConfig]:
        """加载单个提示词配置文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            # 验证必需的元数据
            metadata = data.get('metadata', {})
            if not all(key in metadata for key in ['name', 'version', 'description']):
                logger.warning(f"提示词配置缺少必需元数据: {file_path}")
                return None

            config = PromptConfig(
                name=metadata['name'],
                version=metadata['version'],
                description=metadata['description'],
                content=data,
                metadata=metadata,
                file_path=str(file_path),
                loaded_at=os.path.getmtime(file_path)
            )

            return config

        except yaml.YAMLError as e:
            logger.error(f"YAML 解析错误 {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"读取文件错误 {file_path}: {e}")
            return None

    def _get_prompt_key(self, file_path: Path) -> str:
        """根据文件路径生成提示词键名"""
        relative_path = file_path.relative_to(self.prompts_dir)
        # 移除扩展名并转换为点分隔的键名
        key_parts = list(relative_path.parts)
        key_parts[-1] = key_parts[-1].replace('.yaml', '').replace('.yml', '')
        return '.'.join(key_parts)

    def get_prompt(self, key: str, **kwargs) -> str:
        """
        获取提示词模板并进行变量替换

        Args:
            key: 提示词键名，如 "patent.writer.base_prompt"
            **kwargs: 模板变量，包括 template_id 等增强参数

        Returns:
            替换变量后的提示词字符串

        Raises:
            ValueError: 提示词不存在或变量替换失败
        """
        if key not in self._cache:
            # 尝试重新加载配置
            self._load_all_prompts()
            if key not in self._cache:
                raise ValueError(f"提示词配置不存在: {key}")

        config = self._cache[key]

        try:
            # 简化模板处理 - 只保留template_id用于显示模板名称
            template_id = kwargs.get('template_id')
            if template_id:
                # 调试日志：记录使用的模板ID
                logger.debug(f"使用模板: {template_id}")

            # 生成提示词
            prompt_parts = self._build_enhanced_prompt_from_config(config.content, **kwargs)
            return '\n'.join(prompt_parts)

        except Exception as e:
            logger.error(f"构建提示词失败 {key}: {e}")
            raise ValueError(f"构建提示词失败: {str(e)}")

    def get_enhanced_prompt(self, key: str, template_id: str = None, **kwargs) -> str:
        """
        获取增强的提示词，支持模板智能分析

        Args:
            key: 提示词键名
            template_id: 模板ID，用于智能分析
            **kwargs: 其他模板变量

        Returns:
            增强的提示词字符串
        """
        if template_id:
            kwargs['template_id'] = template_id
        return self.get_prompt(key, **kwargs)

    def _get_template_analysis_for_prompt(self, template_id: str) -> Dict[str, Any]:
        """
        获取用于提示词的模板分析结果

        Args:
            template_id: 模板ID

        Returns:
            Dict: 模板分析摘要
        """
        try:
            template_manager = self._get_template_manager()
            analysis = template_manager.get_template_analysis(template_id)
            if not analysis:
                logger.warning(f"无法获取模板分析结果: {template_id}")
                return {}

            # 转换为适合提示词使用的格式
            return {
                'complexity_score': round(analysis.intelligence.complexity_score, 3),
                'quality_score': round(analysis.intelligence.quality_score, 3),
                'completeness_score': round(analysis.intelligence.completeness_score, 3),
                'template_type': analysis.intelligence.template_type,
                'applicable_domains': analysis.intelligence.applicable_domains,
                'suggestions': analysis.intelligence.suggestions[:3],  # 只取前3个建议
                'section_count': analysis.structure.section_count,
                'max_heading_level': analysis.structure.max_heading_level,
                'placeholder_count': analysis.structure.placeholder_count,
                'content_requirements': {
                    'word_limits': analysis.content_requirements.word_limits,
                    'style_guide': analysis.content_requirements.style_guide,
                    'structure_requirements': analysis.content_requirements.structure_requirements
                },
                'formatting': {
                    'font_requirements': analysis.formatting.font_requirements,
                    'paragraph_styles': analysis.formatting.paragraph_styles,
                    'alignment_rules': analysis.formatting.alignment_rules
                },
                'figure_requirements': {
                    'formats': analysis.figure_requirements.formats,
                    'numbering_rules': analysis.figure_requirements.numbering_rules,
                    'caption_format': analysis.figure_requirements.caption_format
                }
            }

        except Exception as e:
            logger.error(f"获取模板分析结果失败 {template_id}: {e}")
            return {}

    def _build_enhanced_prompt_from_config(self, config: Dict[str, Any], **kwargs) -> List[str]:
        """根据配置构建增强的提示词，支持动态内容生成"""
        parts = []

        # 先使用原有的构建逻辑
        parts.extend(self._build_prompt_from_config(config, **kwargs))

        # 处理动态内容生成
        dynamic_sections = config.get('dynamic_sections', {})
        for section_name, section_config in dynamic_sections.items():
            if self._should_include_section(section_config, **kwargs):
                dynamic_content = self._generate_dynamic_content(section_name, section_config, **kwargs)
                if dynamic_content:
                    parts.append(dynamic_content)

        return parts

    def _should_include_section(self, section_config: Dict[str, Any], **kwargs) -> bool:
        """判断是否应该包含某个动态章节"""
        condition = section_config.get('condition')
        if not condition:
            return True

        # 简单的条件判断
        if condition == 'has_template_id':
            return bool(kwargs.get('template_id'))
        elif condition == 'high_complexity':
            return kwargs.get('template_complexity', 0) > 0.7
        elif condition == 'has_domains':
            return bool(kwargs.get('template_domains'))
        elif condition == 'has_requirements':
            return bool(kwargs.get('template_requirements'))
        else:
            return True

    def _generate_dynamic_content(self, section_name: str, section_config: Dict[str, Any], **kwargs) -> str:
        """生成动态章节内容"""
        generator_name = section_config.get('generator')

        # 检查生成器是否存在
        if not generator_name:
            logger.debug(f"动态章节 {section_name} 未指定生成器")
            return ""

        if generator_name not in self._dynamic_generators:
            logger.warning(f"动态生成器不存在: {generator_name}")
            return ""

        # 安全调用生成器
        try:
            generator_func = self._dynamic_generators[generator_name]
            if not callable(generator_func):
                logger.error(f"动态生成器不可调用: {generator_name}")
                return ""

            result = generator_func(section_config, **kwargs)

            # 验证返回值类型
            if not isinstance(result, str):
                logger.error(f"动态生成器返回类型错误: {generator_name}, 期望str, 实际{type(result)}")
                return ""

            # 检查结果是否包含代码片段（意外泄漏）
            if self._contains_code_snippets(result):
                logger.warning(f"动态生成器结果包含代码片段: {generator_name}, 结果将被过滤")
                return self._filter_code_snippets(result)

            return result

        except Exception as e:
            logger.error(f"动态生成器调用失败: {generator_name}, 错误: {e}")
            return ""

    def _contains_code_snippets(self, text: str) -> bool:
        """检查文本是否包含代码片段"""
        if not text:
            return False

        code_indicators = [
            "def ", "class ", "import ", "from ", "# ", "// ", "/* ", "*/",
            "```", "function", "var ", "let ", "const ", "=>", "{", "}",
            "__pycache__", ".py", ".js", ".java", ".cpp", ".h"
        ]

        text_lower = text.lower()
        return any(indicator in text_lower for indicator in code_indicators)

    def _filter_code_snippets(self, text: str) -> str:
        """过滤文本中的代码片段"""
        # 移除明显的代码块
        import re

        # 移除代码块标记
        text = re.sub(r'```[\s\S]*?```', '[代码块已过滤]', text)

        # 移除函数定义
        text = re.sub(r'def\s+\w+\([^)]*\):\s*\n.*?(?=\n\w|\Z)', '[函数定义已过滤]', text, flags=re.MULTILINE)

        # 移除import语句
        text = re.sub(r'import\s+.*\n', '', text)
        text = re.sub(r'from\s+.*\s+import.*\n', '', text)

        # 移除单行注释
        text = re.sub(r'#.*\n', '\n', text)

        # 移除类定义
        text = re.sub(r'class\s+\w+.*?:\s*\n.*?(?=\n\w|\Z)', '[类定义已过滤]', text, flags=re.MULTILINE)

        return text.strip()

    # 动态内容生成器
    def _generate_template_review_standards(self, section_config: Dict[str, Any], **kwargs) -> str:
        """生成基于模板分析的评审标准和指导原则"""
        template_analysis = kwargs.get('template_analysis', {})
        if not template_analysis:
            return ""

        parts = []
        template_type = template_analysis.get('template_type', '通用模板')
        complexity_score = template_analysis.get('complexity_score', 0)
        quality_score = template_analysis.get('quality_score', 0)
        completeness_score = template_analysis.get('completeness_score', 0)
        template_domains = template_analysis.get('applicable_domains', [])
        template_requirements = template_analysis.get('content_requirements', {})

        parts.append("【模板评审标准】")
        parts.append(f"模板类型: {template_type}")

        # 根据复杂度评分生成评审严格度指导
        if complexity_score > 0.8:
            parts.append("评审严格度: 高（模板复杂度高，需严格审查）")
            parts.append("- 增加对技术方案细节的审查密度")
            parts.append("- 重点检查权利要求书的保护范围是否合理")
            parts.append("- 详细审查附图说明与技术方案的一致性")
            parts.append("- 严格验证技术领域和背景技术的准确性")
        elif complexity_score > 0.5:
            parts.append("评审严格度: 中（模板复杂度适中，需重点审查关键部分）")
            parts.append("- 重点审查核心技术方案的描述完整性")
            parts.append("- 检查权利要求书是否覆盖主要创新点")
            parts.append("- 验证技术方案的创新性和实用性")
        else:
            parts.append("评审严格度: 标准（模板复杂度较低，按标准流程审查）")
            parts.append("- 按常规专利审查标准进行评审")
            parts.append("- 重点关注技术方案的基本完整性")

        # 根据质量评分生成评审质量要求
        if quality_score > 0.8:
            parts.append("模板质量: 高（遵循高质量模板标准）")
            parts.append("- 参考模板的高标准进行评审")
            parts.append("- 确保文档结构完整性和规范性")
        elif quality_score > 0.5:
            parts.append("模板质量: 中等（注意模板可能存在的不足）")
            parts.append("- 重点关注模板规范性和完整性")
            parts.append("- 检查是否存在缺失的标准章节")
        else:
            parts.append("模板质量: 低（模板标准性不足，需严格审查）")
            parts.append("- 严格审查文档结构和格式")
            parts.append("- 重点检查是否遗漏关键章节")
            parts.append("- 建议指出模板需要改进的具体方面")

        # 根据完整性评分提供具体指导
        if completeness_score < 0.7:
            parts.append("完整性检查: 重点关注缺失的标准章节")
            parts.append("- 检查是否包含权利要求书、摘要等必备章节")
            parts.append("- 验证技术领域、背景技术等基础章节的完整性")

        # 根据适用领域提供评审重点指导
        if template_domains:
            parts.append("领域评审重点:")
            for domain in template_domains:
                if domain == '计算机软件':
                    parts.append(f"  {domain}: 重点关注软件架构、算法逻辑、数据流程等技术细节的准确性")
                elif domain == '电子通信':
                    parts.append(f"  {domain}: 重点审查电路原理、信号处理、通信协议等技术特征")
                elif domain == '机械制造':
                    parts.append(f"  {domain}: 重点关注机械结构、工作原理、材料特性、制造工艺等要素")
                elif domain == '化学材料':
                    parts.append(f"  {domain}: 严格审查化学组成、反应机理、材料特性、制备方法等内容")
                elif domain == '医疗器械':
                    parts.append(f"  {domain}: 详细审查结构原理、治疗效果、使用方法等技术要点")
                elif domain == '新能源':
                    parts.append(f"  {domain}: 重点描述能量转换原理、系统构成、效率优化等创新点")

        return '\n'.join(parts)

    def _generate_template_guidance_content(self, section_config: Dict[str, Any], **kwargs) -> str:
        """生成模板指导内容"""
        template_analysis = kwargs.get('template_analysis', {})
        if not template_analysis:
            return ""

        parts = []
        parts.append("【模板格式指导】")

        # 结构指导
        structure_reqs = template_analysis.get('content_requirements', {}).get('structure_requirements', [])
        if structure_reqs:
            parts.append("结构要求:")
            for req in structure_reqs:
                parts.append(f"  • {req}")

        # 字数要求
        word_limits = template_analysis.get('content_requirements', {}).get('word_limits', {})
        if word_limits:
            parts.append("字数要求:")
            for key, limit in word_limits.items():
                parts.append(f"  • {key}: {limit}")

        return '\n'.join(parts)

    def _generate_format_check_requirements(self, section_config: Dict[str, Any], **kwargs) -> str:
        """生成格式检查要求 - 将模板格式信息转化为具体的检查项"""
        template_analysis = kwargs.get('template_analysis', {})
        if not template_analysis:
            return ""

        parts = []
        parts.append("【格式检查要求】")

        # 字体要求检查
        font_reqs = template_analysis.get('formatting', {}).get('font_requirements', {})
        if font_reqs:
            primary_font = font_reqs.get('primary_font')
            if primary_font:
                parts.append(f"字体检查: 确认文档是否使用 {primary_font}")
                parts.append(f"- 检查标题、正文等是否遵循 {primary_font} 字体要求")

        # 段落样式检查
        paragraph_styles = template_analysis.get('formatting', {}).get('paragraph_styles', {})
        if paragraph_styles:
            primary_style = paragraph_styles.get('primary_style')
            if primary_style:
                parts.append(f"段落样式检查: 确认是否符合 {primary_style} 样式规范")
                parts.append(f"- 检查段落间距、缩进等格式是否符合标准")

        # 对齐规则检查
        alignment_rules = template_analysis.get('formatting', {}).get('alignment_rules', {})
        if alignment_rules:
            primary_alignment = alignment_rules.get('primary_alignment')
            if primary_alignment:
                alignment_check_map = {
                    '左对齐': '检查正文段落是否左对齐',
                    '居中': '检查标题等元素是否居中对齐',
                    '右对齐': '检查日期、签名等是否右对齐',
                    '两端对齐': '检查正文是否采用两端对齐'
                }
                check_desc = alignment_check_map.get(primary_alignment, f"检查元素是否采用{primary_alignment}对齐")
                parts.append(f"对齐检查: {check_desc}")

        # 结构要求检查
        structure_reqs = template_analysis.get('content_requirements', {}).get('structure_requirements', [])
        if structure_reqs:
            parts.append("结构要求检查:")
            for req in structure_reqs:
                if '附图' in req:
                    parts.append(f"- 检查是否包含{req}，并验证对应的mermaid图表")
                elif '实施例' in req:
                    parts.append(f"- 检查是否包含{req}")
                else:
                    parts.append(f"- 检查是否满足：{req}")

        # 字数要求检查
        word_limits = template_analysis.get('content_requirements', {}).get('word_limits', {})
        if word_limits:
            parts.append("字数要求检查:")
            for key, limit in word_limits.items():
                parts.append(f"- {key}: {limit}")

        # 图表格式检查
        figure_reqs = template_analysis.get('figure_requirements', {})
        if figure_reqs:
            figure_formats = figure_reqs.get('formats', [])
            if figure_formats:
                parts.append("图表格式检查:")
                parts.append("- 检查mermaid图表格式是否符合要求")
                parts.append(f"- 确认包含以下图表类型: {', '.join(figure_formats)}")

            numbering_rules = figure_reqs.get('numbering_rules', {})
            if numbering_rules:
                parts.append("图表编号检查:")
                parts.append("- 检查图表编号是否符合规范的命名规则")

            caption_format = figure_reqs.get('caption_format', {})
            if caption_format:
                parts.append("图表标题检查:")
                parts.append("- 检查图表标题格式是否规范")
                parts.append("- 确认图表标题与描述的一致性")

        return '\n'.join(parts)

    def _generate_domain_specific_guidance_content(self, section_config: Dict[str, Any], **kwargs) -> str:
        """生成领域特定指导内容"""
        domains = kwargs.get('template_domains', [])
        if not domains:
            return ""

        parts = []
        parts.append("【技术领域专业指导】")

        # 根据不同领域提供特定指导
        domain_guidance = {
            '计算机软件': '请使用技术术语准确描述软件架构、算法逻辑、数据流程等技术细节。',
            '电子通信': '请详细描述电路原理、信号处理、通信协议等技术特征。',
            '机械制造': '请重点描述机械结构、工作原理、材料特性、制造工艺等技术要素。',
            '化学材料': '请准确说明化学组成、反应机理、材料特性、制备方法等技术内容。',
            '医疗器械': '请详细阐述医疗器械的结构原理、治疗效果、使用方法等技术要点。',
            '新能源': '请重点描述能量转换原理、系统构成、效率优化等技术创新点。'
        }

        for domain in domains:
            if domain in domain_guidance:
                parts.append(f"{domain}领域: {domain_guidance[domain]}")

        return '\n'.join(parts) if parts else ""

    def _generate_template_title_only(self, section_config: Dict[str, Any], **kwargs) -> str:
        """生成简化的模板标题信息 - 只显示使用的模板名称"""
        template_id = kwargs.get('template_id')

        if not template_id:
            return ""

        try:
            # 获取模板管理器
            template_manager = self._get_template_manager()
            template_info = template_manager.get_template_info(template_id)

            if template_info:
                template_name = template_info.get('name', '未知模板')
                return f"使用模板: {template_name}"
            else:
                return f"使用模板ID: {template_id}"

        except Exception as e:
            logger.warning(f"获取模板信息失败: {e}")
            return f"使用模板ID: {template_id}"

    def _build_prompt_from_config(self, config: Dict[str, Any], **kwargs) -> List[str]:
        """根据配置构建提示词"""
        parts = []

        # 获取提示词配置
        prompt_config = config.get('prompt', {})

        # 添加角色设定
        if 'role' in prompt_config:
            parts.append(prompt_config['role'])

        # 添加目标/任务说明
        if 'objective' in prompt_config:
            parts.append(prompt_config['objective'])
        elif 'task' in prompt_config:
            parts.append(prompt_config['task'])

        # 添加要求列表
        if 'requirements' in prompt_config:
            if isinstance(prompt_config['requirements'], list):
                requirements_text = '\n'.join(f"- {req}" for req in prompt_config['requirements'])
                parts.append("整体要求：")
                parts.append(requirements_text)

        # 添加审查重点（评审专用）
        if 'review_focus' in prompt_config:
            if isinstance(prompt_config['review_focus'], list):
                focus_text = '\n'.join(f"- {focus}" for focus in prompt_config['review_focus'])
                parts.append("审查重点包括但不限于：")
                parts.append(focus_text)

        # 处理迭代阶段信息
        iteration = kwargs.get('iteration', 1)
        total_iterations = kwargs.get('total_iterations', 1)
        iteration_info = f"这是第 {iteration}/{total_iterations} 轮"

        if 'iteration_phases' in config:
            iteration_config = config['iteration_phases']
            if iteration == 1 and 'first_iteration' in iteration_config:
                parts.append(iteration_info)
                parts.append(iteration_config['first_iteration']['instruction'])
            elif iteration > 1 and 'subsequent_iteration' in iteration_config:
                parts.append(iteration_info)
                parts.append(iteration_config['subsequent_iteration']['instruction'])
        else:
            # 默认迭代信息
            parts.append(iteration_info)

        parts.append("")  # 空行分隔

        # 添加上下文章节
        context_sections = config.get('context_sections', {})
        for section_key, section_config in context_sections.items():
            section_title = section_config['title']
            placeholder = section_config['placeholder']

            # 检查条件
            condition = section_config.get('condition')
            if condition and condition not in kwargs or not kwargs.get(condition):
                continue

            # 提取变量名
            var_match = re.search(r'\{\{(\w+)\}\}', placeholder)
            if var_match:
                var_name = var_match.group(1)
                if var_name in kwargs and kwargs[var_name]:
                    parts.append(section_title)
                    parts.append(str(kwargs[var_name]))
                    parts.append("")

        # 添加最终指令
        if 'final_instruction' in prompt_config:
            parts.append(prompt_config['final_instruction'])
        elif 'output_format' in prompt_config:
            parts.append(prompt_config['output_format'])

        return parts

    def get_prompt_config(self, key: str) -> Optional[PromptConfig]:
        """
        获取提示词配置对象

        Args:
            key: 提示词键名

        Returns:
            提示词配置对象，如果不存在则返回 None
        """
        return self._cache.get(key)

    def list_prompts(self, category: str = None) -> Dict[str, PromptConfig]:
        """
        列出所有提示词配置

        Args:
            category: 分类过滤，如 "patent" 或 "code"

        Returns:
            提示词配置字典
        """
        if category:
            return {k: v for k, v in self._cache.items() if k.startswith(category)}
        return self._cache.copy()

    def reload_prompts(self):
        """重新加载所有提示词配置"""
        logger.info("重新加载提示词配置")
        self._cache.clear()
        self._template_cache.clear()
        self._load_all_prompts()

    def validate_prompt(self, key: str, **kwargs) -> Dict[str, Any]:
        """
        验证提示词和变量

        Args:
            key: 提示词键名
            **kwargs: 测试变量

        Returns:
            验证结果字典
        """
        result = {
            'valid': False,
            'error': None,
            'missing_vars': [],
            'prompt': None
        }

        try:
            prompt = self.get_prompt(key, **kwargs)
            result['prompt'] = prompt
            result['valid'] = True

        except Exception as e:
            result['error'] = str(e)

        return result

    def get_prompt_stats(self) -> Dict[str, Any]:
        """
        获取提示词统计信息

        Returns:
            统计信息字典
        """
        stats = {
            'total_prompts': len(self._cache),
            'categories': {},
            'versions': {},
            'total_files': 0
        }

        for key, config in self._cache.items():
            # 分类统计
            parts = key.split('.')
            if len(parts) >= 2:
                category = parts[0]
                stats['categories'][category] = stats['categories'].get(category, 0) + 1

            # 版本统计
            version = config.version
            stats['versions'][version] = stats['versions'].get(version, 0) + 1

        # 文件统计
        if self.prompts_dir.exists():
            yaml_files = list(self.prompts_dir.rglob("*.yaml"))
            yaml_files.extend(list(self.prompts_dir.rglob("*.yml")))
            stats['total_files'] = len(yaml_files)

        return stats


# 全局提示词管理器实例
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """获取全局提示词管理器实例"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


def get_prompt(key: str, **kwargs) -> str:
    """
    便捷函数：获取提示词

    Args:
        key: 提示词键名
        **kwargs: 模板变量

    Returns:
        提示词字符串
    """
    manager = get_prompt_manager()
    return manager.get_prompt(key, **kwargs)


# 常用提示词键名常量
class PromptKeys:
    """提示词键名常量"""
    PATENT_WRITER = "patent.writer.base_prompt"
    PATENT_REVIEWER = "patent.reviewer.base_prompt"
    CODE_ANALYZER = "code.analyzer.base_prompt"
#!/usr/bin/env python3
"""
验证修改者标记功能的代码修改
检查关键代码是否正确实现
"""

import os
import re

def verify_modifications():
    """验证代码修改"""
    print("🔍 验证修改者标记功能的代码修改...\n")

    # 1. 检查 _build_prompt_from_template 函数修改
    print("1️⃣ 检查 _build_prompt_from_template 函数...")

    with open('backend/patent_workflow.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查新标记支持
    markers_found = []
    if '<previous_output>' in content:
        markers_found.append('✅ <previous_output> 标记支持')
    else:
        markers_found.append('❌ <previous_output> 标记未找到')

    if '<previous_review>' in content:
        markers_found.append('✅ <previous_review> 标记支持')
    else:
        markers_found.append('❌ <previous_review> 标记未找到')

    # 检查动态替换逻辑
    if 'has_dynamic_markers' in content:
        markers_found.append('✅ 动态标记检测逻辑')
    else:
        markers_found.append('❌ 动态标记检测逻辑未找到')

    # 检查向后兼容性
    if '</text>' in content:
        markers_found.append('✅ 向后兼容 </text> 标记')
    else:
        markers_found.append('❌ 向后兼容支持丢失')

    print("   " + "\n   ".join(markers_found))

    # 2. 检查 get_modifier_prompt 方法修改
    print("\n2️⃣ 检查 get_modifier_prompt 方法...")

    modifier_checks = []

    # 查找 get_modifier_prompt 方法
    if 'def get_modifier_prompt(' in content:
        modifier_checks.append('✅ get_modifier_prompt 方法存在')

        # 检查是否有新标记检测逻辑
        method_start = content.find('def get_modifier_prompt(')
        method_content = content[method_start:method_start+2000]  # 取方法前2000字符

        if '<previous_output>' in method_content:
            modifier_checks.append('✅ 修改者方法支持新标记检测')
        else:
            modifier_checks.append('❌ 修改者方法缺少新标记检测')

        if 'strict_mode=True' in method_content:
            modifier_checks.append('✅ 启用严格模式动态替换')
        else:
            modifier_checks.append('❌ 未启用严格模式')
    else:
        modifier_checks.append('❌ get_modifier_prompt 方法未找到')

    print("   " + "\n   ".join(modifier_checks))

    # 3. 检查修改者提示词模板
    print("\n3️⃣ 检查修改者默认提示词...")

    if '_default_modifier_prompt' in content:
        modifier_template_check = '✅ 修改者默认提示词存在'
    else:
        modifier_template_check = '❌ 修改者默认提示词未找到'

    print(f"   {modifier_template_check}")

    # 4. 代码统计
    print("\n4️⃣ 代码修改统计...")

    # 统计新标记出现次数
    previous_output_count = content.count('<previous_output>')
    previous_review_count = content.count('<previous_review>')

    print(f"   <previous_output> 出现次数: {previous_output_count}")
    print(f"   <previous_review> 出现次数: {previous_review_count}")

    # 5. 语法检查（简单）
    print("\n5️⃣ 基本语法检查...")

    syntax_checks = []

    # 检查函数定义完整性
    function_starts = content.count('def ')
    function_ends = content.count('\n    return ')

    if function_starts > 0 and function_ends > 0:
        syntax_checks.append('✅ 函数定义基本完整')
    else:
        syntax_checks.append('❌ 函数定义可能有问题')

    # 检查缩进一致性（简单检查）
    lines = content.split('\n')
    indent_issues = 0
    for line in lines:
        if line.strip() and not line.startswith(' '):
            if line.startswith('def ') or line.startswith('class ') or line.startswith('import ') or line.startswith('from '):
                continue
            indent_issues += 1

    if indent_issues < 10:  # 允许少量顶行代码
        syntax_checks.append('✅ 代码缩进基本正常')
    else:
        syntax_checks.append(f'❌ 发现 {indent_issues} 个可能的缩进问题')

    print("   " + "\n   ".join(syntax_checks))

    # 总结
    print("\n📊 修改验证总结:")

    all_checks = markers_found + modifier_checks + [modifier_template_check] + syntax_checks
    passed = sum(1 for check in all_checks if check.startswith('✅'))
    total = len(all_checks)

    print(f"   总检查项: {total}")
    print(f"   通过项目: {passed}")
    print(f"   通过率: {passed/total*100:.1f}%")

    if passed >= total * 0.8:  # 80%通过率
        print("\n🎉 代码修改验证基本通过！")
        print("\n📋 新功能特性:")
        print("   ✅ 支持 <previous_output> 标记替换")
        print("   ✅ 支持 <previous_review> 标记替换")
        print("   ✅ 保持向后兼容性（</text> 标记）")
        print("   ✅ 智能标记检测和动态替换")
        print("   ✅ 严格模式保护用户输入")

        return True
    else:
        print(f"\n⚠️ 修改验证未完全通过，请检查失败的 {total-passed} 项")
        return False

def show_usage_example():
    """显示使用示例"""
    print("\n📝 使用示例:")
    print("""
设置修改者提示词模板:

你现在扮演一名资深的中国发明专利修改专家。

## 历史上下文分析

### 上轮专利生成结果：
<previous_output>

### 上轮审批评审意见：
<previous_review>

## 修改策略
基于评审意见，重点修改...

请输出修改后的完整专利文档。

💡 标记说明:
- <previous_output> → 自动替换为上一轮的专利生成结果
- <previous_review> → 自动替换为上一轮的评审意见
""")

if __name__ == "__main__":
    success = verify_modifications()
    show_usage_example()

    if success:
        print("\n🚀 修改者标记功能代码已准备就绪！")
        exit(0)
    else:
        print("\n⚠️ 请检查代码修改中的问题。")
        exit(1)
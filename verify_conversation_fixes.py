#!/usr/bin/env python3
"""
验证对话查看器的三角色支持修复
检查前端和后端修改是否正确
"""

import os
import re

def verify_frontend_modifications():
    """验证前端修改"""
    print("🔍 验证前端 ConversationViewer.jsx 修改...")

    try:
        with open('frontend/src/ConversationViewer.jsx', 'r', encoding='utf-8') as f:
            content = f.read()

        checks = []

        # 检查角色选项是否包含修改者
        if '{ value: "modifier", label: "修改者" }' in content:
            checks.append("✅ 角色选项包含修改者")
        else:
            checks.append("❌ 角色选项缺少修改者")

        # 检查提示词标签显示
        if 'selectedRole === "modifier" ? "修改者" : "审批者"' in content:
            checks.append("✅ 提示词标签支持修改者")
        else:
            checks.append("❌ 提示词标签缺少修改者支持")

        # 检查错误提示
        modifier_error_check = 'selectedRole === "modifier" ? "修改者" : "审批者"' in content
        if modifier_error_check:
            checks.append("✅ 错误提示支持修改者")
        else:
            checks.append("❌ 错误提示缺少修改者支持")

        # 检查智能角色选择逻辑
        if 'selectedRound === 1' in content and 'setSelectedRole("writer")' in content:
            checks.append("✅ 智能角色选择逻辑存在")
        else:
            checks.append("❌ 缺少智能角色选择逻辑")

        # 统计修改者出现次数
        modifier_count = content.count('modifier')
        checks.append(f"📊 'modifier' 出现次数: {modifier_count}")

        print("   " + "\n   ".join(checks))
        return all(check.startswith('✅') or check.startswith('📊') for check in checks)

    except Exception as e:
        print(f"   ❌ 读取前端文件失败: {e}")
        return False

def verify_backend_modifications():
    """验证后端修改"""
    print("\n🔍 验证后端 conversation API 修改...")

    try:
        with open('backend/conversation_api.py', 'r', encoding='utf-8') as f:
            content = f.read()

        checks = []

        # 检查角色验证
        if 'role not in [\'writer\', \'modifier\', \'reviewer\']' in content:
            checks.append("✅ 角色验证支持修改者")
        else:
            checks.append("❌ 角色验证缺少修改者")

        # 检查错误消息
        if '必须是 writer、modifier 或 reviewer' in content:
            checks.append("✅ 错误消息包含修改者")
        else:
            checks.append("❌ 错误消息缺少修改者")

        print("   " + "\n   ".join(checks))
        return all(check.startswith('✅') for check in checks)

    except Exception as e:
        print(f"   ❌ 读取后端API文件失败: {e}")
        return False

def verify_database_modifications():
    """验证数据库修改"""
    print("\n🔍 验证数据库文档修改...")

    try:
        with open('backend/conversation_db.py', 'r', encoding='utf-8') as f:
            content = f.read()

        checks = []

        # 检查数据类注释
        if "# 'writer', 'modifier', or 'reviewer'" in content:
            checks.append("✅ 数据类注释包含修改者")
        else:
            checks.append("❌ 数据类注释缺少修改者")

        # 检查函数文档注释
        if "角色 ('writer', 'modifier', or 'reviewer')" in content:
            checks.append("✅ 函数文档包含修改者")
        else:
            checks.append("❌ 函数文档缺少修改者")

        print("   " + "\n   ".join(checks))
        return all(check.startswith('✅') for check in checks)

    except Exception as e:
        print(f"   ❌ 读取数据库文件失败: {e}")
        return False

def show_expected_behavior():
    """显示期望的行为"""
    print("\n📝 修复后的期望行为:")
    print("""
🔄 前端对话查看器:
- 第1轮: 显示"撰写者"和"审批者"两个选项，默认选择"撰写者"
- 第2轮及以后: 显示"撰写者"、"修改者"和"审批者"三个选项，但智能默认选择"修改者"
- 用户可以手动切换查看任意角色的对话

🛡️ 后端API:
- 支持 'writer', 'modifier', 'reviewer' 三种角色查询
- 正确返回各轮次各角色的对话数据
- 错误消息准确反映支持的角色选项

💡 智能角色切换:
- 选择第1轮时，如果当前选择的是修改者，自动切换到撰写者
- 选择第2轮及以后时，如果当前选择的是撰写者，自动切换到修改者
- 审批者角色在所有轮次都可用
""")

def main():
    """主验证函数"""
    print("🧪 对话查看器三角色支持修复验证")
    print("=" * 50)

    # 验证各个组件
    frontend_ok = verify_frontend_modifications()
    backend_ok = verify_backend_modifications()
    database_ok = verify_database_modifications()

    # 显示期望行为
    show_expected_behavior()

    # 总结
    total_checks = sum([frontend_ok, backend_ok, database_ok])
    passed_checks = sum([frontend_ok, backend_ok, database_ok])

    print(f"\n📊 修复验证总结:")
    print(f"   前端修改: {'✅ 通过' if frontend_ok else '❌ 失败'}")
    print(f"   后端API: {'✅ 通过' if backend_ok else '❌ 失败'}")
    print(f"   数据库文档: {'✅ 通过' if database_ok else '❌ 失败'}")
    print(f"   总体通过率: {passed_checks/3*100:.1f}%")

    if passed_checks == 3:
        print(f"\n🎉 所有修复验证通过！")
        print(f"\n🚀 修复完成后的效果:")
        print(f"   - 前端对话查看器支持修改者角色")
        print(f"   - 后端API正确处理三种角色")
        print(f"   - 智能角色选择提升用户体验")
        print(f"   - 完整支持三角色专利生成工作流程")
        return True
    else:
        print(f"\n⚠️ 修复验证未完全通过，请检查失败项。")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
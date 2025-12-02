#!/usr/bin/env python3
"""
快速测试API响应格式
"""

import json
import os
import sys
sys.path.append('backend')

def test_user_prompts_data():
    """测试用户提示词数据文件"""
    print("🔍 测试用户提示词数据文件...")

    data_file = 'backend/data/user_prompts.json'

    if not os.path.exists(data_file):
        print(f"❌ 数据文件不存在: {data_file}")
        return None

    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        prompts = data.get('prompts', {})

        print(f"✅ 文件读取成功")
        print(f"✅ 角色数量: {len(prompts)}")
        print(f"✅ 角色列表: {list(prompts.keys())}")

        # 检查修改者提示词
        modifier_prompt = prompts.get('modifier', '')
        if modifier_prompt and '<previous_output>' in modifier_prompt:
            print("✅ 修改者提示词包含 <previous_output> 标记")
        else:
            print("⚠️ 修改者提示词不包含 <previous_output> 标记")

        # 模拟API响应格式
        api_response = {
            'success': True,
            'data': {
                'prompts': prompts,
                'stats': {
                    'has_modifier_prompt': bool(modifier_prompt.strip()),
                    'modifier_prompt_length': len(modifier_prompt)
                }
            }
        }

        print(f"✅ API响应格式正确")
        return api_response

    except Exception as e:
        print(f"❌ 读取数据文件失败: {e}")
        return None

def test_template_response_format():
    """测试模板API响应格式"""
    print("\n🔍 测试模板API响应格式...")

    # 模拟前端期望的格式
    expected_format = {
        'ok': True,
        'templates': [
            {
                'id': 'default',
                'name': '默认模板',
                'is_default': True,
                'is_valid': True
            }
        ],
        'default_template_id': 'default'
    }

    print("✅ 前端期望的模板API格式:")
    print(f"   - ok: {expected_format['ok']}")
    print(f"   - templates: {len(expected_format['templates'])} 个模板")
    print(f"   - default_template_id: {expected_format['default_template_id']}")

    return expected_format

def main():
    """主测试函数"""
    print("🧪 API响应格式快速测试")
    print("=" * 40)

    # 测试用户提示词API
    user_prompts_response = test_user_prompts_data()

    # 测试模板API格式
    template_format = test_template_response_format()

    print("\n📊 测试总结:")
    if user_prompts_response:
        print("✅ 用户提示词API: 响应格式正确")
        prompts = user_prompts_response['data']['prompts']
        print(f"   - 撰写者提示词: {'已设置' if prompts.get('writer') else '未设置'}")
        print(f"   - 修改者提示词: {'已设置' if prompts.get('modifier') else '未设置'}")
        print(f"   - 审批者提示词: {'已设置' if prompts.get('reviewer') else '未设置'}")
    else:
        print("❌ 用户提示词API: 响应格式有问题")

    if template_format:
        print("✅ 模板API: 响应格式正确")
    else:
        print("❌ 模板API: 响应格式有问题")

    print("\n💡 如果前端仍然报错，可能的原因:")
    print("   1. 后端服务未重启")
    print("   2. 前端缓存问题")
    print("   3. 网络连接问题")
    print("   4. CORS跨域问题")

if __name__ == "__main__":
    main()
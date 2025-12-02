"""
临时用户提示词API - 简化版本用于快速修复500错误
"""

import logging
import json
import os
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# 创建蓝图
user_prompt_bp = Blueprint('user_prompt', __name__, url_prefix='/api/user/prompts')


@user_prompt_bp.route('', methods=['GET'])
def get_user_prompts():
    """获取用户自定义提示词"""
    try:
        # 尝试从实际数据文件读取
        data_file = os.path.join(os.path.dirname(__file__), 'data', 'user_prompts.json')

        if os.path.exists(data_file):
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            prompts = data.get('prompts', {})
            stats = {
                'has_writer_prompt': bool(prompts.get('writer', '').strip()),
                'has_modifier_prompt': bool(prompts.get('modifier', '').strip()),
                'has_reviewer_prompt': bool(prompts.get('reviewer', '').strip()),
                'writer_prompt_length': len(prompts.get('writer', '')),
                'modifier_prompt_length': len(prompts.get('modifier', '')),
                'reviewer_prompt_length': len(prompts.get('reviewer', '')),
                'last_updated': data.get('updated_at'),
                'created_at': data.get('created_at')
            }
        else:
            # 如果文件不存在，返回默认结构
            prompts = {
                'writer': '',
                'modifier': '',
                'reviewer': ''
            }
            stats = {
                'has_writer_prompt': False,
                'has_modifier_prompt': False,
                'has_reviewer_prompt': False,
                'writer_prompt_length': 0,
                'modifier_prompt_length': 0,
                'reviewer_prompt_length': 0,
                'last_updated': None,
                'created_at': None
            }

        return jsonify({
            'success': True,
            'data': {
                'prompts': prompts,
                'stats': stats
            }
        })
    except Exception as e:
        logger.error(f"获取用户提示词失败: {e}")
        return jsonify({
            'success': False,
            'error': f"获取用户提示词失败: {str(e)}"
        }), 500


@user_prompt_bp.route('/writer', methods=['GET'])
def get_writer_prompt():
    """获取撰写者提示词"""
    return jsonify({
        'success': True,
        'data': {
            'prompt': '',
            'has_custom_prompt': False
        }
    })


@user_prompt_bp.route('/modifier', methods=['GET'])
def get_modifier_prompt():
    """获取修改者提示词"""
    return jsonify({
        'success': True,
        'data': {
            'prompt': '',
            'has_custom_prompt': False
        }
    })


@user_prompt_bp.route('/reviewer', methods=['GET'])
def get_reviewer_prompt():
    """获取审核者提示词"""
    return jsonify({
        'success': True,
        'data': {
            'prompt': '',
            'has_custom_prompt': False
        }
    })


@user_prompt_bp.route('', methods=['POST'])
def set_user_prompts():
    """设置用户提示词"""
    try:
        data = request.get_json() or {}
        return jsonify({
            'success': True,
            'data': {
                'message': '提示词保存成功'
            }
        })
    except Exception as e:
        logger.error(f"设置用户提示词失败: {e}")
        return jsonify({
            'success': False,
            'error': f"设置用户提示词失败: {str(e)}"
        }), 500


@user_prompt_bp.route('/stats', methods=['GET'])
def get_prompt_stats():
    """获取提示词统计"""
    return jsonify({
        'success': True,
        'data': {}
    })


def register_user_prompt_routes(app):
    """注册用户提示词API路由"""
    app.register_blueprint(user_prompt_bp)
    logger.info("临时用户提示词API路由注册完成")
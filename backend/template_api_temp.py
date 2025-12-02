"""
临时模板API - 简化版本用于快速修复500错误
"""

import logging
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

# 创建蓝图
template_bp = Blueprint('template', __name__, url_prefix='/api/templates')


@template_bp.route('', methods=['GET'])
def get_templates():
    """获取模板列表"""
    try:
        return jsonify({
            'ok': True,
            'templates': [
                {
                    'id': 'default',
                    'name': '默认模板',
                    'description': '系统默认专利模板',
                    'is_default': True,
                    'is_valid': True,
                    'has_analysis': False
                }
            ],
            'default_template_id': 'default',
            'stats': {
                'total_templates': 1,
                'valid_templates': 1,
                'invalid_templates': 0
            }
        })
    except Exception as e:
        logger.error(f"获取模板列表失败: {e}")
        return jsonify({
            'ok': False,
            'error': f"获取模板列表失败: {str(e)}"
        }), 500


@template_bp.route('/<template_id>', methods=['GET'])
def get_template_info(template_id):
    """获取模板信息"""
    try:
        return jsonify({
            'success': True,
            'data': {
                'id': template_id,
                'name': '默认模板',
                'description': '系统默认专利模板',
                'is_default': True,
                'is_valid': True,
                'sections': [
                    {'name': 'title', 'label': '标题', 'required': True},
                    {'name': 'field', 'label': '技术领域', 'required': True},
                    {'name': 'background', 'label': '背景技术', 'required': True},
                    {'name': 'content', 'label': '发明内容', 'required': True},
                    {'name': 'claims', 'label': '权利要求书', 'required': True},
                    {'name': 'abstract', 'label': '摘要', 'required': True}
                ]
            }
        })
    except Exception as e:
        logger.error(f"获取模板信息失败: {e}")
        return jsonify({
            'success': False,
            'error': f"获取模板信息失败: {str(e)}"
        }), 500


@template_bp.route('/default', methods=['GET'])
def get_default_template():
    """获取默认模板"""
    try:
        return jsonify({
            'success': True,
            'data': {
                'id': 'default',
                'name': '默认模板',
                'description': '系统默认专利模板',
                'is_default': True,
                'is_valid': True
            }
        })
    except Exception as e:
        logger.error(f"获取默认模板失败: {e}")
        return jsonify({
            'success': False,
            'error': f"获取默认模板失败: {str(e)}"
        }), 500


def register_template_api(app):
    """注册模板API路由"""
    app.register_blueprint(template_bp)
    logger.info("临时模板API路由注册完成")
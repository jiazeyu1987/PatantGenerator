"""
对话历史API接口
提供结构化的对话数据查询功能
"""

import json
import logging
from flask import Blueprint, request, jsonify
from conversation_db import get_conversation_db
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# 创建蓝图
conversation_bp = Blueprint('conversation', __name__, url_prefix='/api/conversations')


@conversation_bp.route('/tasks', methods=['GET'])
def get_all_tasks():
    """
    获取所有任务列表

    Returns:
        JSON: 任务列表
    """
    try:
        conversation_db = get_conversation_db()
        tasks = conversation_db.get_all_tasks()

        # 转换为字典格式
        result = []
        for task in tasks:
            result.append({
                'id': task.id,
                'title': task.title,
                'context': task.context[:200] + '...' if len(task.context) > 200 else task.context,
                'iterations': task.iterations,
                'created_at': task.created_at,
                'status': task.status
            })

        return jsonify({
            'success': True,
            'data': result,
            'total': len(result)
        })

    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@conversation_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task_detail(task_id: str):
    """
    获取指定任务的详细信息

    Args:
        task_id: 任务ID

    Returns:
        JSON: 任务详细信息
    """
    try:
        conversation_db = get_conversation_db()
        task = conversation_db.get_task(task_id)

        if not task:
            return jsonify({
                'success': False,
                'error': '任务不存在'
            }), 404

        # 获取任务的所有轮次
        rounds = conversation_db.get_task_rounds(task_id)

        return jsonify({
            'success': True,
            'data': {
                'id': task.id,
                'title': task.title,
                'context': task.context,
                'iterations': task.iterations,
                'created_at': task.created_at,
                'status': task.status,
                'rounds': rounds
            }
        })

    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@conversation_bp.route('/tasks/<task_id>/rounds', methods=['GET'])
def get_task_rounds(task_id: str):
    """
    获取任务的所有轮次信息

    Args:
        task_id: 任务ID

    Returns:
        JSON: 轮次列表
    """
    try:
        conversation_db = get_conversation_db()
        rounds = conversation_db.get_task_rounds(task_id)

        return jsonify({
            'success': True,
            'data': rounds,
            'total': len(rounds)
        })

    except Exception as e:
        logger.error(f"获取任务轮次失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@conversation_bp.route('/tasks/<task_id>/rounds/<int:round_number>', methods=['GET'])
def get_round_conversations(task_id: str, round_number: int):
    """
    获取指定轮次的所有角色对话

    Args:
        task_id: 任务ID
        round_number: 轮次编号

    Returns:
        JSON: 该轮次的所有对话
    """
    try:
        conversation_db = get_conversation_db()

        # 获取撰写者、修改者和审批者的对话
        writer_conversation = conversation_db.get_conversation_round(task_id, round_number, 'writer')
        modifier_conversation = conversation_db.get_conversation_round(task_id, round_number, 'modifier')
        reviewer_conversation = conversation_db.get_conversation_round(task_id, round_number, 'reviewer')

        result = {}

        if writer_conversation:
            result['writer'] = {
                'id': writer_conversation.id,
                'prompt': writer_conversation.prompt,
                'response': writer_conversation.response,
                'timestamp': writer_conversation.timestamp
            }

        if modifier_conversation:
            result['modifier'] = {
                'id': modifier_conversation.id,
                'prompt': modifier_conversation.prompt,
                'response': modifier_conversation.response,
                'timestamp': modifier_conversation.timestamp
            }

        if reviewer_conversation:
            result['reviewer'] = {
                'id': reviewer_conversation.id,
                'prompt': reviewer_conversation.prompt,
                'response': reviewer_conversation.response,
                'timestamp': reviewer_conversation.timestamp
            }

        return jsonify({
            'success': True,
            'data': result,
            'task_id': task_id,
            'round_number': round_number
        })

    except Exception as e:
        logger.error(f"获取轮次对话失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@conversation_bp.route('/tasks/<task_id>/rounds/<int:round_number>/<role>', methods=['GET'])
def get_specific_conversation(task_id: str, round_number: int, role: str):
    """
    获取指定轮次和角色的对话

    Args:
        task_id: 任务ID
        round_number: 轮次编号
        role: 角色 ('writer', 'modifier', or 'reviewer')

    Returns:
        JSON: 指定角色的对话
    """
    try:
        if role not in ['writer', 'modifier', 'reviewer']:
            return jsonify({
                'success': False,
                'error': '无效的角色，必须是 writer、modifier 或 reviewer'
            }), 400

        conversation_db = get_conversation_db()
        conversation = conversation_db.get_conversation_round(task_id, round_number, role)

        if not conversation:
            return jsonify({
                'success': False,
                'error': '对话不存在'
            }), 404

        return jsonify({
            'success': True,
            'data': {
                'id': conversation.id,
                'task_id': conversation.task_id,
                'round_number': conversation.round_number,
                'role': conversation.role,
                'prompt': conversation.prompt,
                'response': conversation.response,
                'timestamp': conversation.timestamp
            }
        })

    except Exception as e:
        logger.error(f"获取指定对话失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@conversation_bp.route('/tasks/<task_id>/conversations', methods=['GET'])
def get_all_task_conversations(task_id: str):
    """
    获取任务的所有对话（按轮次和角色组织）

    Args:
        task_id: 任务ID

    Returns:
        JSON: 任务的所有对话
    """
    try:
        conversation_db = get_conversation_db()
        conversations = conversation_db.get_task_conversations(task_id)

        # 按轮次组织对话
        organized_data = {}

        for conv in conversations:
            round_num = conv.round_number
            role = conv.role

            if round_num not in organized_data:
                organized_data[round_num] = {}

            organized_data[round_num][role] = {
                'id': conv.id,
                'prompt': conv.prompt,
                'response': conv.response,
                'timestamp': conv.timestamp
            }

        return jsonify({
            'success': True,
            'data': organized_data,
            'task_id': task_id
        })

    except Exception as e:
        logger.error(f"获取任务所有对话失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@conversation_bp.route('/health', methods=['GET'])
def health_check():
    """
    健康检查接口

    Returns:
        JSON: 健康状态
    """
    try:
        conversation_db = get_conversation_db()
        # 尝试获取任务列表来验证数据库连接
        conversation_db.get_all_tasks()

        return jsonify({
            'success': True,
            'message': '对话API服务正常'
        })

    except Exception as e:
        logger.error(f"对话API健康检查失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def register_conversation_routes(app):
    """
    注册对话API路由到Flask应用

    Args:
        app: Flask应用实例
    """
    app.register_blueprint(conversation_bp)
    logger.info("对话API路由注册完成")
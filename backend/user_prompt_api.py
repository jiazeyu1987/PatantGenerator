"""
用户自定义提示词API接口

提供RESTful API来管理用户自定义的撰写者、修改者和审核者提示词。
"""

import logging
from flask import Blueprint, request, jsonify
from user_prompt_manager import get_user_prompt_manager

logger = logging.getLogger(__name__)

# 创建蓝图
user_prompt_bp = Blueprint('user_prompt', __name__, url_prefix='/api/user/prompts')


@user_prompt_bp.route('', methods=['GET'])
def get_user_prompts():
    """
    获取用户自定义提示词

    Returns:
        JSON: 用户自定义提示词和统计信息
    """
    try:
        manager = get_user_prompt_manager()

        # 获取所有用户提示词
        prompts = manager.get_all_user_prompts()

        # 获取统计信息
        stats = manager.get_prompt_stats()

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
    """
    获取用户自定义撰写者提示词

    Returns:
        JSON: 撰写者提示词内容
    """
    try:
        manager = get_user_prompt_manager()
        prompt = manager.get_user_prompt('writer')

        return jsonify({
            'success': True,
            'data': {
                'prompt': prompt,
                'has_custom_prompt': bool(prompt and prompt.strip())
            }
        })

    except Exception as e:
        logger.error(f"获取撰写者提示词失败: {e}")
        return jsonify({
            'success': False,
            'error': f"获取撰写者提示词失败: {str(e)}"
        }), 500


@user_prompt_bp.route('/modifier', methods=['GET'])
def get_modifier_prompt():
    """
    获取用户自定义修改者提示词

    Returns:
        JSON: 修改者提示词内容
    """
    try:
        manager = get_user_prompt_manager()
        prompt = manager.get_user_prompt('modifier')

        return jsonify({
            'success': True,
            'data': {
                'prompt': prompt,
                'has_custom_prompt': bool(prompt and prompt.strip())
            }
        })

    except Exception as e:
        logger.error(f"获取修改者提示词失败: {e}")
        return jsonify({
            'success': False,
            'error': f"获取修改者提示词失败: {str(e)}"
        }), 500


@user_prompt_bp.route('/reviewer', methods=['GET'])
def get_reviewer_prompt():
    """
    获取用户自定义审核者提示词

    Returns:
        JSON: 审核者提示词内容
    """
    try:
        manager = get_user_prompt_manager()
        prompt = manager.get_user_prompt('reviewer')

        return jsonify({
            'success': True,
            'data': {
                'prompt': prompt,
                'has_custom_prompt': bool(prompt and prompt.strip())
            }
        })

    except Exception as e:
        logger.error(f"获取审核者提示词失败: {e}")
        return jsonify({
            'success': False,
            'error': f"获取审核者提示词失败: {str(e)}"
        }), 500


@user_prompt_bp.route('', methods=['POST'])
def set_user_prompts():
    """
    设置用户自定义提示词

    Request Body:
        {
            "writer": "撰写者提示词内容",
            "modifier": "修改者提示词内容",
            "reviewer": "审核者提示词内容"
        }

    Returns:
        JSON: 设置结果
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': "请求数据不能为空"
            }), 400

        manager = get_user_prompt_manager()
        results = {}

        # 设置撰写者提示词
        if 'writer' in data:
            writer_prompt = data['writer']
            if isinstance(writer_prompt, str):
                writer_success = manager.set_user_prompt('writer', writer_prompt)
                results['writer'] = writer_success
                if writer_success:
                    logger.info(f"撰写者提示词设置成功，长度: {len(writer_prompt)}")
                else:
                    logger.error("撰写者提示词设置失败")
            else:
                results['writer'] = False
                logger.error("撰写者提示词内容必须是字符串类型")

        # 设置修改者提示词
        if 'modifier' in data:
            modifier_prompt = data['modifier']
            if isinstance(modifier_prompt, str):
                modifier_success = manager.set_user_prompt('modifier', modifier_prompt)
                results['modifier'] = modifier_success
                if modifier_success:
                    logger.info(f"修改者提示词设置成功，长度: {len(modifier_prompt)}")
                else:
                    logger.error("修改者提示词设置失败")
            else:
                results['modifier'] = False
                logger.error("修改者提示词内容必须是字符串类型")

        # 设置审核者提示词
        if 'reviewer' in data:
            reviewer_prompt = data['reviewer']
            if isinstance(reviewer_prompt, str):
                reviewer_success = manager.set_user_prompt('reviewer', reviewer_prompt)
                results['reviewer'] = reviewer_success
                if reviewer_success:
                    logger.info(f"审核者提示词设置成功，长度: {len(reviewer_prompt)}")
                else:
                    logger.error("审核者提示词设置失败")
            else:
                results['reviewer'] = False
                logger.error("审核者提示词内容必须是字符串类型")

        # 检查是否至少有一个成功
        overall_success = any(results.values())

        if overall_success:
            return jsonify({
                'success': True,
                'data': {
                    'updated': results,
                    'message': '提示词保存成功'
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '提示词保存失败',
                'data': {
                    'updated': results
                }
            }), 400

    except Exception as e:
        logger.error(f"设置用户提示词失败: {e}")
        return jsonify({
            'success': False,
            'error': f"设置用户提示词失败: {str(e)}"
        }), 500


@user_prompt_bp.route('/writer', methods=['POST'])
def set_writer_prompt():
    """
    设置用户自定义撰写者提示词

    Request Body:
        {
            "prompt": "撰写者提示词内容"
        }

    Returns:
        JSON: 设置结果
    """
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({
                'success': False,
                'error': "缺少提示词内容"
            }), 400

        prompt = data['prompt']
        if not isinstance(prompt, str):
            return jsonify({
                'success': False,
                'error': "提示词内容必须是字符串类型"
            }), 400

        manager = get_user_prompt_manager()
        success = manager.set_user_prompt('writer', prompt)

        if success:
            return jsonify({
                'success': True,
                'data': {
                    'message': '撰写者提示词保存成功',
                    'prompt_length': len(prompt)
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '撰写者提示词保存失败'
            }), 500

    except Exception as e:
        logger.error(f"设置撰写者提示词失败: {e}")
        return jsonify({
            'success': False,
            'error': f"设置撰写者提示词失败: {str(e)}"
        }), 500


@user_prompt_bp.route('/modifier', methods=['POST'])
def set_modifier_prompt():
    """
    设置用户自定义修改者提示词

    Request Body:
        {
            "prompt": "修改者提示词内容"
        }

    Returns:
        JSON: 设置结果
    """
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({
                'success': False,
                'error': "缺少提示词内容"
            }), 400

        prompt = data['prompt']
        if not isinstance(prompt, str):
            return jsonify({
                'success': False,
                'error': "提示词内容必须是字符串类型"
            }), 400

        manager = get_user_prompt_manager()
        success = manager.set_user_prompt('modifier', prompt)

        if success:
            return jsonify({
                'success': True,
                'data': {
                    'message': '修改者提示词保存成功',
                    'prompt_length': len(prompt)
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '修改者提示词保存失败'
            }), 500

    except Exception as e:
        logger.error(f"设置修改者提示词失败: {e}")
        return jsonify({
            'success': False,
            'error': f"设置修改者提示词失败: {str(e)}"
        }), 500


@user_prompt_bp.route('/reviewer', methods=['POST'])
def set_reviewer_prompt():
    """
    设置用户自定义审核者提示词

    Request Body:
        {
            "prompt": "审核者提示词内容"
        }

    Returns:
        JSON: 设置结果
    """
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({
                'success': False,
                'error': "缺少提示词内容"
            }), 400

        prompt = data['prompt']
        if not isinstance(prompt, str):
            return jsonify({
                'success': False,
                'error': "提示词内容必须是字符串类型"
            }), 400

        manager = get_user_prompt_manager()
        success = manager.set_user_prompt('reviewer', prompt)

        if success:
            return jsonify({
                'success': True,
                'data': {
                    'message': '审核者提示词保存成功',
                    'prompt_length': len(prompt)
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '审核者提示词保存失败'
            }), 500

    except Exception as e:
        logger.error(f"设置审核者提示词失败: {e}")
        return jsonify({
            'success': False,
            'error': f"设置审核者提示词失败: {str(e)}"
        }), 500


@user_prompt_bp.route('/writer', methods=['DELETE'])
def delete_writer_prompt():
    """
    删除用户自定义撰写者提示词

    Returns:
        JSON: 删除结果
    """
    try:
        manager = get_user_prompt_manager()
        success = manager.delete_user_prompt('writer')

        if success:
            return jsonify({
                'success': True,
                'data': {
                    'message': '撰写者提示词已重置为默认'
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '撰写者提示词重置失败'
            }), 500

    except Exception as e:
        logger.error(f"删除撰写者提示词失败: {e}")
        return jsonify({
            'success': False,
            'error': f"删除撰写者提示词失败: {str(e)}"
        }), 500


@user_prompt_bp.route('/modifier', methods=['DELETE'])
def delete_modifier_prompt():
    """
    删除用户自定义修改者提示词

    Returns:
        JSON: 删除结果
    """
    try:
        manager = get_user_prompt_manager()
        success = manager.delete_user_prompt('modifier')

        if success:
            return jsonify({
                'success': True,
                'data': {
                    'message': '修改者提示词已重置为默认'
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '修改者提示词重置失败'
            }), 500

    except Exception as e:
        logger.error(f"删除修改者提示词失败: {e}")
        return jsonify({
            'success': False,
            'error': f"删除修改者提示词失败: {str(e)}"
        }), 500


@user_prompt_bp.route('/reviewer', methods=['DELETE'])
def delete_reviewer_prompt():
    """
    删除用户自定义审核者提示词

    Returns:
        JSON: 删除结果
    """
    try:
        manager = get_user_prompt_manager()
        success = manager.delete_user_prompt('reviewer')

        if success:
            return jsonify({
                'success': True,
                'data': {
                    'message': '审核者提示词已重置为默认'
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '审核者提示词重置失败'
            }), 500

    except Exception as e:
        logger.error(f"删除审核者提示词失败: {e}")
        return jsonify({
            'success': False,
            'error': f"删除审核者提示词失败: {str(e)}"
        }), 500


@user_prompt_bp.route('', methods=['DELETE'])
def delete_all_user_prompts():
    """
    删除所有用户自定义提示词

    Returns:
        JSON: 删除结果
    """
    try:
        manager = get_user_prompt_manager()

        # 删除撰写者提示词
        writer_success = manager.delete_user_prompt('writer')

        # 删除修改者提示词
        modifier_success = manager.delete_user_prompt('modifier')

        # 删除审核者提示词
        reviewer_success = manager.delete_user_prompt('reviewer')

        overall_success = writer_success and modifier_success and reviewer_success

        if overall_success:
            return jsonify({
                'success': True,
                'data': {
                    'message': '所有用户提示词已重置为默认',
                    'deleted': {
                        'writer': writer_success,
                        'modifier': modifier_success,
                        'reviewer': reviewer_success
                    }
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '部分提示词重置失败',
                'data': {
                    'deleted': {
                        'writer': writer_success,
                        'modifier': modifier_success,
                        'reviewer': reviewer_success
                    }
                }
            }), 500

    except Exception as e:
        logger.error(f"删除所有用户提示词失败: {e}")
        return jsonify({
            'success': False,
            'error': f"删除所有用户提示词失败: {str(e)}"
        }), 500


@user_prompt_bp.route('/stats', methods=['GET'])
def get_prompt_stats():
    """
    获取用户提示词统计信息

    Returns:
        JSON: 统计信息
    """
    try:
        manager = get_user_prompt_manager()
        stats = manager.get_prompt_stats()

        return jsonify({
            'success': True,
            'data': stats
        })

    except Exception as e:
        logger.error(f"获取提示词统计失败: {e}")
        return jsonify({
            'success': False,
            'error': f"获取提示词统计失败: {str(e)}"
        }), 500


def register_user_prompt_routes(app):
    """注册用户提示词API路由"""
    app.register_blueprint(user_prompt_bp)
    logger.info("用户提示词API路由注册完成")
"""
模板管理 API 接口

提供 REST API 接口来管理和操作专利模板。
"""

from flask import Blueprint, jsonify, request, send_file
from pathlib import Path
import os
from typing import Any, Dict
from template_manager import get_template_manager
from validators import validate_path

# 创建蓝图
template_bp = Blueprint('template', __name__, url_prefix='/api/templates')


@template_bp.route('/', methods=['GET'])
def get_templates():
    """获取所有模板列表"""
    try:
        manager = get_template_manager()
        templates = manager.get_template_list()

        return jsonify({
            'ok': True,
            'templates': templates,
            'default_template_id': manager.default_template_id,
            'stats': manager.get_stats()
        })
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': f"获取模板列表失败: {str(e)}"
        }), 500


@template_bp.route('/<template_id>/info', methods=['GET'])
def get_template_info(template_id: str):
    """获取指定模板的详细信息"""
    try:
        manager = get_template_manager()
        template_info = manager.get_template_info(template_id)

        if not template_info:
            return jsonify({
                'ok': False,
                'error': f"模板不存在: {template_id}"
            }), 404

        return jsonify({
            'ok': True,
            'template': template_info
        })
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': f"获取模板信息失败: {str(e)}"
        }), 500


@template_bp.route('/<template_id>/content', methods=['GET'])
def get_template_content(template_id: str):
    """获取模板内容（仅用于预览，不返回完整文档）"""
    try:
        manager = get_template_manager()
        template_info = manager.get_template_info(template_id)

        if not template_info:
            return jsonify({
                'ok': False,
                'error': f"模板不存在: {template_id}"
            }), 404

        # 返回模板的基本信息，不返回完整文档内容
        return jsonify({
            'ok': True,
            'template_id': template_id,
            'name': template_info['name'],
            'description': template_info['description'],
            'sections': template_info['sections'],
            'placeholder_count': template_info['placeholder_count'],
            'is_valid': template_info['is_valid']
        })
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': f"获取模板内容失败: {str(e)}"
        }), 500


@template_bp.route('/default', methods=['GET'])
def get_default_template():
    """获取默认模板信息"""
    try:
        manager = get_template_manager()
        default_template = manager.get_default_template()

        if not default_template:
            return jsonify({
                'ok': False,
                'error': "未找到默认模板"
            }), 404

        return jsonify({
            'ok': True,
            'template': default_template
        })
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': f"获取默认模板失败: {str(e)}"
        }), 500


@template_bp.route('/validate', methods=['POST'])
def validate_template():
    """验证模板文件"""
    try:
        data = request.get_json()
        if not data or 'file_path' not in data:
            return jsonify({
                'ok': False,
                'error': "缺少文件路径参数"
            }), 400

        file_path = data['file_path']

        # 验证路径安全性
        try:
            validated_path = validate_path(file_path)
        except Exception as e:
            return jsonify({
                'ok': False,
                'error': f"路径验证失败: {str(e)}"
            }), 400

        # 检查文件是否存在和是否为docx文件
        path = Path(validated_path)
        if not path.exists():
            return jsonify({
                'ok': False,
                'error': "文件不存在"
            }), 404

        if path.suffix.lower() != '.docx':
            return jsonify({
                'ok': False,
                'error': "文件格式不支持，请上传 .docx 文件"
            }), 400

        # 验证模板
        manager = get_template_manager()
        is_valid, message = manager.validate_template(validated_path)

        return jsonify({
            'ok': True,
            'is_valid': is_valid,
            'message': message,
            'file_path': validated_path
        })
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': f"验证模板失败: {str(e)}"
        }), 500


@template_bp.route('/upload', methods=['POST'])
def upload_template():
    """上传模板文件"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'ok': False,
                'error': "没有找到文件"
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'ok': False,
                'error': "文件名为空"
            }), 400

        # 检查文件格式
        if not file.filename.lower().endswith('.docx'):
            return jsonify({
                'ok': False,
                'error': "只支持 .docx 文件格式"
            }), 400

        # 获取模板管理器
        manager = get_template_manager()

        # 保存文件
        filename = file.filename
        file_path = manager.template_dir / filename

        # 避免文件名冲突
        counter = 1
        original_filename = filename
        while file_path.exists():
            name_part = Path(original_filename).stem
            ext_part = Path(original_filename).suffix
            filename = f"{name_part}_{counter}{ext_part}"
            file_path = manager.template_dir / filename
            counter += 1

        file.save(str(file_path))

        # 验证上传的模板
        is_valid, message = manager.validate_template(str(file_path))

        # 重新加载模板列表
        manager.reload_templates()

        # 获取新上传的模板信息
        template_info = None
        for template in manager.templates.values():
            if template.file_name == filename:
                template_info = template.to_dict()
                break

        return jsonify({
            'ok': True,
            'template': template_info,
            'is_valid': is_valid,
            'message': message,
            'uploaded_filename': filename
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': f"上传模板失败: {str(e)}"
        }), 500


@template_bp.route('/<template_id>/delete', methods=['DELETE'])
def delete_template(template_id: str):
    """删除指定模板"""
    try:
        manager = get_template_manager()
        template_info = manager.get_template_info(template_id)

        if not template_info:
            return jsonify({
                'ok': False,
                'error': f"模板不存在: {template_id}"
            }), 404

        # 删除文件
        file_path = Path(template_info['file_path'])
        if file_path.exists():
            file_path.unlink()

        # 重新加载模板列表
        manager.reload_templates()

        return jsonify({
            'ok': True,
            'message': f"模板 {template_info['name']} 已删除"
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': f"删除模板失败: {str(e)}"
        }), 500


@template_bp.route('/stats', methods=['GET'])
def get_template_stats():
    """获取模板统计信息"""
    try:
        manager = get_template_manager()
        stats = manager.get_stats()

        return jsonify({
            'ok': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': f"获取模板统计失败: {str(e)}"
        }), 500


@template_bp.route('/<template_id>/analysis', methods=['GET'])
def get_template_analysis(template_id: str):
    """获取模板深度分析结果"""
    try:
        manager = get_template_manager()

        # 检查模板是否存在
        template_info = manager.get_template_info(template_id)
        if not template_info:
            return jsonify({
                'ok': False,
                'error': f"模板不存在: {template_id}"
            }), 404

        # 获取分析结果
        analysis_summary = manager.get_template_analysis_summary(template_id)
        if not analysis_summary:
            return jsonify({
                'ok': False,
                'error': f"模板分析结果不存在: {template_id}"
            }), 404

        return jsonify({
            'ok': True,
            'template_id': template_id,
            'template_info': template_info,
            'analysis': analysis_summary
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': f"获取模板分析失败: {str(e)}"
        }), 500


@template_bp.route('/<template_id>/analysis', methods=['POST'])
def analyze_template(template_id: str):
    """分析指定模板"""
    try:
        manager = get_template_manager()

        # 检查模板是否存在
        template_info = manager.get_template_info(template_id)
        if not template_info:
            return jsonify({
                'ok': False,
                'error': f"模板不存在: {template_id}"
            }), 404

        # 强制重新分析
        force_reanalyze = request.json.get('force_reanalyze', False) if request.json else False

        # 执行分析
        analysis = manager.get_template_analysis(template_id, force_reanalyze=force_reanalyze)
        if not analysis:
            return jsonify({
                'ok': False,
                'error': f"模板分析失败: {template_id}"
            }), 500

        # 获取分析摘要
        analysis_summary = manager.get_template_analysis_summary(template_id)

        return jsonify({
            'ok': True,
            'message': f"模板分析完成: {template_info['name']}",
            'template_id': template_id,
            'analysis': analysis_summary,
            'force_reanalyzed': force_reanalyze
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': f"分析模板失败: {str(e)}"
        }), 500


@template_bp.route('/analyze-all', methods=['POST'])
def analyze_all_templates():
    """分析所有模板"""
    try:
        manager = get_template_manager()
        data = request.json or {}
        force_reanalyze = data.get('force_reanalyze', False)

        # 执行批量分析
        results = manager.analyze_all_templates(force_reanalyze=force_reanalyze)

        return jsonify({
            'ok': True,
            'message': "批量分析完成",
            'results': results
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': f"批量分析失败: {str(e)}"
        }), 500


@template_bp.route('/<template_id>/analysis/cache', methods=['DELETE'])
def clear_template_analysis_cache(template_id: str):
    """清除指定模板的分析缓存"""
    try:
        manager = get_template_manager()

        # 检查模板是否存在
        template_info = manager.get_template_info(template_id)
        if not template_info:
            return jsonify({
                'ok': False,
                'error': f"模板不存在: {template_id}"
            }), 404

        # 清除缓存
        template = manager.templates.get(template_id)
        if template:
            template.analysis_cached = False
            template.analysis = None
            template.analysis_timestamp = None

        # 从缓存中移除
        if template_id in manager._analysis_cache:
            del manager._analysis_cache[template_id]

        return jsonify({
            'ok': True,
            'message': f"已清除模板 {template_info['name']} 的分析缓存"
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': f"清除分析缓存失败: {str(e)}"
        }), 500


@template_bp.route('/analysis/stats', methods=['GET'])
def get_analysis_stats():
    """获取分析统计信息"""
    try:
        manager = get_template_manager()
        stats = manager.get_analysis_stats()

        return jsonify({
            'ok': True,
            'stats': stats
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': f"获取分析统计失败: {str(e)}"
        }), 500


@template_bp.route('/reload', methods=['POST'])
def reload_templates():
    """重新加载所有模板"""
    try:
        manager = get_template_manager()
        manager.reload_templates()

        return jsonify({
            'ok': True,
            'message': "模板已重新加载",
            'stats': manager.get_stats()
        })
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': f"重新加载模板失败: {str(e)}"
        }), 500


@template_bp.route('/<template_id>/download', methods=['GET'])
def download_template(template_id: str):
    """下载模板文件"""
    try:
        manager = get_template_manager()
        template_info = manager.get_template_info(template_id)

        if not template_info:
            return jsonify({
                'ok': False,
                'error': f"模板不存在: {template_id}"
            }), 404

        file_path = Path(template_info['file_path'])
        if not file_path.exists():
            return jsonify({
                'ok': False,
                'error': "模板文件不存在"
            }), 404

        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=template_info['file_name'],
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': f"下载模板失败: {str(e)}"
        }), 500


def register_template_api(app):
    """注册模板 API 到 Flask 应用"""
    app.register_blueprint(template_bp)
    return app
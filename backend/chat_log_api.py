"""
聊天日志 API 接口

提供 REST API 接口来查看和管理聊天日志。
"""

from flask import Blueprint, jsonify, request, send_file
from pathlib import Path
import os
from datetime import datetime
from chat_logger import get_chat_logger
from validators import validate_path

# 创建蓝图
chat_log_bp = Blueprint('chat_log', __name__, url_prefix='/api/chat-logs')


@chat_log_bp.route('/stats', methods=['GET'])
def get_chat_log_stats():
    """获取聊天日志统计信息"""
    try:
        chat_logger = get_chat_logger()
        stats = chat_logger.get_log_stats()
        return jsonify({
            "ok": True,
            "stats": stats
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"获取聊天日志统计失败: {str(e)}"
        }), 500


@chat_log_bp.route('/files', methods=['GET'])
def list_chat_log_files():
    """获取聊天日志文件列表"""
    try:
        chat_logger = get_chat_logger()
        log_files = chat_logger.get_log_files()

        # 获取文件详细信息
        file_info = []
        for log_file in log_files:
            try:
                path = Path(log_file)
                if path.exists():
                    stat = path.stat()
                    file_info.append({
                        "name": path.name,
                        "path": str(path),
                        "size": stat.st_size,
                        "size_human": _format_size(stat.st_size),
                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        "modified_timestamp": stat.st_mtime
                    })
            except Exception:
                continue

        # 按修改时间倒序排列
        file_info.sort(key=lambda x: x['modified_timestamp'], reverse=True)

        return jsonify({
            "ok": True,
            "files": file_info,
            "count": len(file_info)
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"获取聊天日志文件列表失败: {str(e)}"
        }), 500


@chat_log_bp.route('/files/<filename>/preview', methods=['GET'])
def preview_chat_log_file(filename):
    """预览聊天日志文件内容"""
    try:
        # 安全验证文件名
        if not filename.startswith('chat_prompt_') or not filename.endswith('.log'):
            return jsonify({
                "ok": False,
                "error": "无效的文件名"
            }), 400

        chat_logger = get_chat_logger()
        log_files = chat_logger.get_log_files()

        # 查找文件
        target_file = None
        for log_file in log_files:
            if Path(log_file).name == filename:
                target_file = log_file
                break

        if not target_file or not Path(target_file).exists():
            return jsonify({
                "ok": False,
                "error": "文件不存在"
            }), 404

        # 获取预览参数
        lines = request.args.get('lines', 100, type=int)
        offset = request.args.get('offset', 0, type=int)

        lines = max(1, min(lines, 1000))  # 限制最多1000行
        offset = max(0, offset)

        # 读取文件内容
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()

            total_lines = len(all_lines)
            preview_lines = all_lines[offset:offset + lines]

            return jsonify({
                "ok": True,
                "filename": filename,
                "total_lines": total_lines,
                "offset": offset,
                "lines_returned": len(preview_lines),
                "content": ''.join(preview_lines),
                "has_more": offset + lines < total_lines
            })
        except UnicodeDecodeError:
            return jsonify({
                "ok": False,
                "error": "文件编码错误"
            }), 500

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"预览文件失败: {str(e)}"
        }), 500


@chat_log_bp.route('/files/<filename>/download', methods=['GET'])
def download_chat_log_file(filename):
    """下载聊天日志文件"""
    try:
        # 安全验证文件名
        if not filename.startswith('chat_prompt_') or not filename.endswith('.log'):
            return jsonify({
                "ok": False,
                "error": "无效的文件名"
            }), 400

        chat_logger = get_chat_logger()
        log_files = chat_logger.get_log_files()

        # 查找文件
        target_file = None
        for log_file in log_files:
            if Path(log_file).name == filename:
                target_file = log_file
                break

        if not target_file or not Path(target_file).exists():
            return jsonify({
                "ok": False,
                "error": "文件不存在"
            }), 404

        return send_file(
            target_file,
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain'
        )

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"下载文件失败: {str(e)}"
        }), 500


@chat_log_bp.route('/files/<filename>', methods=['DELETE'])
def delete_chat_log_file(filename):
    """删除聊天日志文件"""
    try:
        # 安全验证文件名
        if not filename.startswith('chat_prompt_') or not filename.endswith('.log'):
            return jsonify({
                "ok": False,
                "error": "无效的文件名"
            }), 400

        chat_logger = get_chat_logger()
        log_files = chat_logger.get_log_files()

        # 查找文件
        target_file = None
        for log_file in log_files:
            if Path(log_file).name == filename:
                target_file = log_file
                break

        if not target_file or not Path(target_file).exists():
            return jsonify({
                "ok": False,
                "error": "文件不存在"
            }), 404

        # 删除文件
        Path(target_file).unlink()

        return jsonify({
            "ok": True,
            "message": f"文件 {filename} 已删除"
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"删除文件失败: {str(e)}"
        }), 500


@chat_log_bp.route('/search', methods=['POST'])
def search_chat_logs():
    """搜索聊天日志内容"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({
                "ok": False,
                "error": "缺少搜索查询"
            }), 400

        query = data['query'].strip()
        if not query:
            return jsonify({
                "ok": False,
                "error": "搜索查询不能为空"
            }), 400

        # 获取搜索参数
        max_results = min(data.get('max_results', 50), 200)  # 限制最多200个结果
        date_filter = data.get('date_filter')  # 格式: YYYY-MM-DD

        chat_logger = get_chat_logger()
        log_files = chat_logger.get_log_files()

        results = []
        total_searched = 0

        for log_file in log_files:
            # 日期过滤
            if date_filter:
                file_date = Path(log_file).stem.split('_')[-1]  # 提取日期部分
                if not file_date.startswith(date_filter):
                    continue

            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 简单的文本搜索
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if query.lower() in line.lower():
                        # 获取上下文
                        context_start = max(0, i - 2)
                        context_end = min(len(lines), i + 3)
                        context = lines[context_start:context_end]

                        results.append({
                            "file": Path(log_file).name,
                            "line_number": i + 1,
                            "match_line": line.strip(),
                            "context": context,
                            "timestamp": _extract_timestamp_from_context(context)
                        })

                        if len(results) >= max_results:
                            break

                total_searched += 1
                if len(results) >= max_results:
                    break

            except Exception as e:
                print(f"搜索文件 {log_file} 时出错: {e}")
                continue

        return jsonify({
            "ok": True,
            "query": query,
            "results": results,
            "total_results": len(results),
            "files_searched": total_searched,
            "date_filter": date_filter
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"搜索失败: {str(e)}"
        }), 500


def _format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return "0B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f}{size_names[i]}"


def _extract_timestamp_from_context(context):
    """从上下文中提取时间戳"""
    for line in context:
        if line.startswith("时间戳:"):
            return line.replace("时间戳:", "").strip()
    return ""


def register_chat_log_api(app):
    """注册聊天日志 API 到 Flask 应用"""
    app.register_blueprint(chat_log_bp)
    return app
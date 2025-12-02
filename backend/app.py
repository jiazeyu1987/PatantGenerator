import os
import logging
from typing import Any, Dict

from flask import Flask, jsonify, request, send_from_directory

from code_analyzer import build_code_innovation_context
from patent_workflow import run_patent_iteration
from validators import ValidationError, validate_request_data, sanitize_error_message, categorize_error
from task_manager import get_task_manager, TaskStatus
from config import get_config
from chat_log_api import register_chat_log_api
# 简化的模板处理
from conversation_api import register_conversation_routes
from user_prompt_manager import get_user_prompt_manager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# For production, serve the built React app from frontend/dist
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend", "dist"))

def create_app() -> Flask:
    """创建并配置 Flask 应用"""
    config = get_config()

    app = Flask(__name__, static_folder=None)

    # 应用 Flask 配置
    flask_config = config.get_flask_config()
    app.config.update(flask_config)

    # 注册聊天日志 API
    register_chat_log_api(app)

    # 注册模板管理 API
    # 简化的模板 API
    @app.route("/api/templates/", methods=["GET"])
    def get_templates():
        """获取模板列表"""
        try:
            # 简化的模板列表，硬编码以避免复杂的依赖问题
            templates = [
                {
                    'id': 'default',
                    'name': '默认模板',
                    'description': '系统默认专利模板',
                    'is_default': True,
                    'is_valid': True,
                    'has_analysis': False,
                    'created_at': '2025-12-01T00:00:00.000Z',
                    'file_size': 0,
                    'placeholder_count': 0
                }
            ]

            stats = {
                'total_templates': 1,
                'valid_templates': 1,
                'invalid_templates': 0
            }

            return jsonify({
                'ok': True,
                'templates': templates,
                'default_template_id': 'default',
                'stats': stats
            })

        except Exception as e:
            import traceback
            print(f"获取模板列表失败: {e}")
            print(f"详细错误: {traceback.format_exc()}")

            return jsonify({
                'ok': False,
                'error': f"获取模板列表失败: {str(e)}"
            }), 500

    # 注册对话历史 API
    register_conversation_routes(app)

    # 用户提示词 API
    @app.route("/api/user/prompts", methods=["GET"])
    def get_user_prompts():
        """获取用户提示词"""
        logger = logging.getLogger(__name__)
        try:
            manager = get_user_prompt_manager()
            prompts = manager.get_all_user_prompts()
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

    @app.route("/api/user/prompts", methods=["POST"])
    def set_user_prompts():
        """设置用户提示词"""
        logger = logging.getLogger(__name__)
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': "请求数据不能为空"
                }), 400

            manager = get_user_prompt_manager()
            results = {}

            # 设置各角色提示词
            for role in ['writer', 'modifier', 'reviewer']:
                if role in data:
                    prompt = data[role]
                    if isinstance(prompt, str):
                        success = manager.set_user_prompt(role, prompt)
                        results[role] = success
                        if success:
                            logger.info(f"{role}提示词设置成功，长度: {len(prompt)}")
                        else:
                            logger.error(f"{role}提示词设置失败")

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

    # 添加调试API
    @app.route("/api/debug/prompts", methods=["GET"])
    def debug_prompts():
        """调试提示词使用情况 - 使用内联简单提示词引擎"""
        logger = logging.getLogger(__name__)
        try:
            from patent_workflow import get_simple_prompt_engine

            # 创建简单提示词引擎实例
            simple_prompt_engine = get_simple_prompt_engine()

            # 获取用户提示词
            user_prompt_manager = simple_prompt_engine.user_prompt_manager
            writer_prompt = user_prompt_manager.get_user_prompt('writer')
            modifier_prompt = user_prompt_manager.get_user_prompt('modifier')
            reviewer_prompt = user_prompt_manager.get_user_prompt('reviewer')

            debug_info = {
                "engine_status": "内联SimplePromptEngine 已初始化",
                "user_prompts": {
                    "writer": {
                        "exists": bool(writer_prompt),
                        "length": len(writer_prompt) if writer_prompt else 0,
                        "content_preview": writer_prompt[:100] + "..." if writer_prompt else None,
                        "is_empty": not writer_prompt.strip() if writer_prompt else True,
                        "starts_with_hash": writer_prompt.startswith("##") if writer_prompt else False
                    },
                    "modifier": {
                        "exists": bool(modifier_prompt),
                        "length": len(modifier_prompt) if modifier_prompt else 0,
                        "content_preview": modifier_prompt[:100] + "..." if modifier_prompt else None,
                        "is_empty": not modifier_prompt.strip() if modifier_prompt else True,
                        "starts_with_hash": modifier_prompt.startswith("##") if modifier_prompt else False
                    },
                    "reviewer": {
                        "exists": bool(reviewer_prompt),
                        "length": len(reviewer_prompt) if reviewer_prompt else 0,
                        "content_preview": reviewer_prompt[:100] + "..." if reviewer_prompt else None,
                        "is_empty": not reviewer_prompt.strip() if reviewer_prompt else True,
                        "starts_with_hash": reviewer_prompt.startswith("##") if reviewer_prompt else False
                    }
                },
                "default_prompts": {
                    "writer_loaded": bool(simple_prompt_engine._default_writer_prompt),
                    "writer_length": len(simple_prompt_engine._default_writer_prompt) if simple_prompt_engine._default_writer_prompt else 0,
                    "modifier_loaded": bool(simple_prompt_engine._default_modifier_prompt),
                    "modifier_length": len(simple_prompt_engine._default_modifier_prompt) if simple_prompt_engine._default_modifier_prompt else 0,
                    "reviewer_loaded": bool(simple_prompt_engine._default_reviewer_prompt),
                    "reviewer_length": len(simple_prompt_engine._default_reviewer_prompt) if simple_prompt_engine._default_reviewer_prompt else 0
                }
            }

            return jsonify({
                "success": True,
                "data": debug_info
            })

        except Exception as e:
            logger.error(f"调试提示词失败: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/debug/test-prompts", methods=["GET"])
    def test_prompts():
        """测试提示词获取功能"""
        logger = logging.getLogger(__name__)
        try:
            from patent_workflow import get_simple_prompt_engine

            # 创建简单提示词引擎实例
            simple_prompt_engine = get_simple_prompt_engine()

            # 模拟测试提示词获取
            test_context = "这是一个测试技术背景"
            test_draft = """# 测试专利标题

## 技术领域
本发明涉及一种测试技术。

## 背景技术
现有技术存在一些问题。

## 发明内容
本发明提供一种解决方案。"""

            writer_prompt = simple_prompt_engine.get_writer_prompt(
                context=test_context, iteration=1, total_iterations=3
            )

            reviewer_prompt = simple_prompt_engine.get_reviewer_prompt(
                context=test_context, current_draft=test_draft, iteration=1, total_iterations=3
            )

            # 检查是否包含</text>标记以及是否被替换
            reviewer_has_text_marker = "</text>" in reviewer_prompt
            reviewer_contains_draft = test_draft in reviewer_prompt if test_draft else False

            test_results = {
                "test_context": test_context,
                "test_draft_length": len(test_draft),
                "test_draft_preview": test_draft[:100] + "...",
                "writer_prompt": {
                    "length": len(writer_prompt),
                    "preview": writer_prompt[:200] + "...",
                    "is_user_custom": writer_prompt.startswith("##") if writer_prompt else False
                },
                "reviewer_prompt": {
                    "length": len(reviewer_prompt),
                    "preview": reviewer_prompt[:300] + "...",
                    "full_preview": reviewer_prompt,
                    "is_user_custom": reviewer_prompt.startswith("##") if reviewer_prompt else False,
                    "has_text_marker": reviewer_has_text_marker,
                    "contains_draft_content": reviewer_contains_draft,
                    "replacement_worked": reviewer_has_text_marker == False and reviewer_contains_draft == True
                }
            }

            return jsonify({
                "success": True,
                "data": test_results
            })

        except Exception as e:
            logger.error(f"测试提示词失败: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    return app


# 创建应用实例
app = create_app()


@app.route("/api/generate", methods=["POST"])
def generate() -> Any:
    # 配置日志
    logger = logging.getLogger(__name__)
    config = get_config()

    try:
        # 获取请求数据
        data: Dict[str, Any] = request.get_json(silent=True)
        if not data:
            return jsonify({
                "error": "invalid_request",
                "message": "请求数据格式错误或为空"
            }), 400

        # 验证请求数据
        try:
            validated_data = validate_request_data(data)
        except ValidationError as e:
            logger.warning(f"输入验证失败: {str(e)}")
            error_msg = str(e)
            user_msg = sanitize_error_message(error_msg, True)
            return jsonify({
                "error": "validation_error",
                "message": user_msg
            }), 400

        mode = validated_data["mode"]

        # 构建上下文
        if mode == "code":
            try:
                project_path = validated_data["project_path"]
                context = build_code_innovation_context(project_path)
                logger.info(f"代码模式：分析路径 {project_path}")
            except Exception as e:
                logger.error(f"代码分析失败: {str(e)}")
                return jsonify({
                    "error": "code_analysis_failed",
                    "message": "代码分析失败，请检查路径是否正确"
                }), 400
        else:  # mode == "idea"
            idea_text = validated_data["idea_text"]
            context = "\n".join([
                "# Idea Based Context",
                "",
                "User provided idea / requirement:",
                "",
                idea_text,
                "",
                "Goal: Extract key technical innovations and write a full "
                "Chinese invention patent based on this idea.",
            ])
            logger.info("创意模式：处理用户创意文本")

        # 获取参数
        iterations = validated_data["iterations"]
        output_name = validated_data["output_name"]
        template_id = validated_data.get("template_id")

        # 执行专利生成
        try:
            logger.info(f"开始生成专利，迭代次数: {iterations}，使用模板: {template_id or '无'}")
            result = run_patent_iteration(
                context=context,
                iterations=iterations,
                base_name=output_name,
                template_id=template_id
            )
            logger.info(f"专利生成成功: {result.get('output_path')}")
        except Exception as e:
            logger.error(f"专利生成失败: {str(e)}")
            error_msg = sanitize_error_message(str(e))
            return jsonify({
                "error": "generation_failed",
                "message": error_msg
            }), 500

        # 准备响应数据
        try:
            output_rel = os.path.relpath(result["output_path"], os.getcwd())
            last_review = result.get("last_review")
            preview = last_review[:2000] if isinstance(last_review, str) else None

            return jsonify({
                "ok": True,
                "outputPath": output_rel,
                "iterations": result.get("iterations", iterations),
                "lastReviewPreview": preview,
            })
        except Exception as e:
            logger.error(f"响应数据准备失败: {str(e)}")
            return jsonify({
                "error": "response_failed",
                "message": "响应数据准备失败"
            }), 500

    except Exception as e:
        # 捕获未预期的错误
        logger.critical(f"未预期的错误: {str(e)}", exc_info=True)
        return jsonify({
            "error": "internal_error",
            "message": "服务器内部错误，请稍后重试"
        }), 500


@app.route("/api/generate/async", methods=["POST"])
def generate_async() -> Any:
    """
    异步专利生成接口
    立即返回任务ID，客户端可以轮询任务状态
    """
    logger = logging.getLogger(__name__)

    try:
        # 获取请求数据
        data: Dict[str, Any] = request.get_json(silent=True)
        if not data:
            return jsonify({
                "error": "invalid_request",
                "message": "请求数据格式错误或为空"
            }), 400

        # 验证请求数据
        try:
            validated_data = validate_request_data(data)
        except ValidationError as e:
            logger.warning(f"输入验证失败: {str(e)}")
            error_msg = str(e)
            user_msg = sanitize_error_message(error_msg, True)
            return jsonify({
                "error": "validation_error",
                "message": user_msg
            }), 400

        mode = validated_data["mode"]
        iterations = validated_data["iterations"]
        output_name = validated_data["output_name"]
        template_id = validated_data.get("template_id")

        # 构建上下文
        if mode == "code":
            project_path = validated_data["project_path"]
            context = build_code_innovation_context(project_path)
            logger.info(f"异步代码模式：分析路径 {project_path}")
        else:  # mode == "idea"
            idea_text = validated_data["idea_text"]
            context = "\n".join([
                "# Idea Based Context",
                "",
                "User provided idea / requirement:",
                "",
                idea_text,
                "",
                "Goal: Extract key technical innovations and write a full "
                "Chinese invention patent based on this idea.",
            ])
            logger.info("异步创意模式：处理用户创意文本")

        # 提交异步任务
        task_manager = get_task_manager()
        task_id = task_manager.submit_task(
            run_patent_iteration,
            context=context,
            iterations=iterations,
            base_name=output_name,
            template_id=template_id
        )

        logger.info(f"异步任务已提交，任务ID: {task_id}")

        return jsonify({
            "ok": True,
            "taskId": task_id,
            "message": "任务已提交，请使用任务ID查询进度"
        })

    except Exception as e:
        logger.critical(f"异步任务提交失败: {str(e)}", exc_info=True)
        return jsonify({
            "error": "task_submission_failed",
            "message": "任务提交失败，请稍后重试"
        }), 500


@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_task_status(task_id: str) -> Any:
    """
    获取任务状态接口
    """
    logger = logging.getLogger(__name__)

    try:
        task_manager = get_task_manager()
        task_status = task_manager.get_task_status(task_id)

        if not task_status:
            return jsonify({
                "error": "task_not_found",
                "message": "任务不存在"
            }), 404

        return jsonify(task_status)

    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}", exc_info=True)
        return jsonify({
            "error": "status_query_failed",
            "message": "查询任务状态失败"
        }), 500


@app.route("/api/tasks/<task_id>/cancel", methods=["POST"])
def cancel_task(task_id: str) -> Any:
    """
    取消任务接口
    """
    logger = logging.getLogger(__name__)

    try:
        task_manager = get_task_manager()
        success = task_manager.cancel_task(task_id)

        if not success:
            return jsonify({
                "error": "cancel_failed",
                "message": "任务不存在或无法取消"
            }), 400

        logger.info(f"任务已取消: {task_id}")
        return jsonify({
            "ok": True,
            "message": "任务已取消"
        })

    except Exception as e:
        logger.error(f"取消任务失败: {str(e)}", exc_info=True)
        return jsonify({
            "error": "cancel_failed",
            "message": "取消任务失败"
        }), 500


@app.route("/api/tasks/statistics", methods=["GET"])
def get_task_statistics() -> Any:
    """
    获取任务统计信息接口
    """
    logger = logging.getLogger(__name__)

    try:
        task_manager = get_task_manager()
        stats = task_manager.get_statistics()

        return jsonify({
            "ok": True,
            "statistics": stats
        })

    except Exception as e:
        logger.error(f"获取任务统计失败: {str(e)}", exc_info=True)
        return jsonify({
            "error": "statistics_query_failed",
            "message": "查询任务统计失败"
        }), 500


@app.route("/")
def index() -> Any:
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path: str) -> Any:
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")


def setup_logging() -> None:
    """配置应用日志系统"""
    # 获取日志级别
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # 配置根日志器
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=log_format,
        handlers=[
            logging.StreamHandler(),  # 控制台输出
            logging.FileHandler('patent_generator.log', encoding='utf-8')  # 文件输出
        ]
    )

    # 设置第三方库日志级别
    logging.getLogger('werkzeug').setLevel(logging.WARNING)


def setup_logging_from_config() -> None:
    """根据配置设置日志系统"""
    config = get_config()
    log_config = config.logging

    # 获取日志级别
    log_level = getattr(logging, log_config.level.upper(), logging.INFO)

    # 配置处理器
    handlers = []

    if log_config.console_enabled:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        handlers.append(console_handler)

    if log_config.file_enabled:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_config.file_path,
            maxBytes=log_config.file_max_size,
            backupCount=log_config.file_backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        handlers.append(file_handler)

    # 配置根日志器
    logging.basicConfig(
        level=log_level,
        format=log_config.format,
        handlers=handlers,
        force=True
    )

    # 设置第三方库日志级别
    logging.getLogger('werkzeug').setLevel(logging.WARNING)


def main() -> None:
    """主函数"""
    try:
        # 加载配置
        config = get_config()

        # 设置日志
        setup_logging_from_config()
        logger = logging.getLogger(__name__)

        # 确保输出目录存在
        config.ensure_output_dir()

        logger.info(f"启动专利生成服务器")
        logger.info(f"配置信息: 端口={config.server.port}, 调试模式={config.server.debug}, "
                   f"最大工作线程={config.task_manager.max_workers}")

        # 启动任务管理器
        task_manager = get_task_manager()
        task_manager.max_workers = config.task_manager.max_workers
        task_manager.cleanup_interval = config.task_manager.cleanup_interval
        task_manager.start()
        logger.info("任务管理器已启动")

        # 启动 Flask 应用
        app.run(
            host=config.server.host,
            port=config.server.port,
            debug=config.server.debug,
            threaded=config.server.threaded
        )

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.critical(f"服务器启动失败: {str(e)}", exc_info=True)
        raise
    finally:
        # 确保 task manager 正确关闭
        try:
            task_manager = get_task_manager()
            task_manager.stop()
            logger.info("任务管理器已关闭")
        except Exception as e:
            logger.error(f"关闭任务管理器时出错: {str(e)}")


if __name__ == "__main__":
    main()

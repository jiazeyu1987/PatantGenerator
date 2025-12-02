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
# 完整的模板处理
from conversation_api import register_conversation_routes
from template_api import register_template_api
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
    register_template_api(app)

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
            for role in ['writer', 'modifier', 'reviewer', 'template']:
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

    # Main patent generation endpoint
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

                # 在创意模式下，提取并传递 idea_text
                idea_text = validated_data.get("idea_text") if mode == "idea" else None

                result = run_patent_iteration(
                    context=context,
                    iterations=iterations,
                    base_name=output_name,
                    template_id=template_id,
                    idea_text=idea_text
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

    # Static file serving for frontend
    @app.route("/")
    def index() -> Any:
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/<path:path>")
    def static_files(path: str) -> Any:
        file_path = os.path.join(FRONTEND_DIR, path)
        if os.path.isfile(file_path):
            return send_from_directory(FRONTEND_DIR, path)
        return send_from_directory(FRONTEND_DIR, "index.html")

    return app


# 创建应用实例
app = create_app()


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
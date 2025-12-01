#!/usr/bin/env python3
"""
简化的Flask服务器用于测试
"""

try:
    import os
    import sys
    from flask import Flask, jsonify, request, send_from_directory
    from datetime import datetime
    import json
    import uuid
    import time

    print("✓ 依赖导入成功")
except ImportError as e:
    print(f"✗ 依赖导入失败: {e}")
    print("请安装 Flask: pip install Flask")
    sys.exit(1)

# 创建Flask应用
app = Flask(__name__)

# 内存存储任务状态
tasks = {}

@app.route('/')
def index():
    """主页"""
    return jsonify({
        "message": "专利生成系统后端服务",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/health')
def health():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "services": {
            "flask": "ok",
            "task_manager": "ok"
        },
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/generate', methods=['POST'])
def generate_sync():
    """同步专利生成"""
    try:
        data = request.get_json() or {}

        # 模拟处理
        time.sleep(2)

        # 返回模拟结果
        output_file = f"output/patent-{datetime.now().strftime('%Y%m%d%H%M%S')}.md"

        return jsonify({
            "ok": True,
            "outputPath": output_file,
            "iterations": data.get('iterations', 1),
            "lastReviewPreview": "这是一个模拟的专利评审结果。系统运行正常，等待集成真实的LLM服务。"
        })

    except Exception as e:
        return jsonify({
            "error": "generation_failed",
            "message": str(e)
        }), 500

@app.route('/api/generate/async', methods=['POST'])
def generate_async():
    """异步专利生成"""
    try:
        data = request.get_json() or {}
        task_id = str(uuid.uuid4())

        # 创建任务
        tasks[task_id] = {
            "taskId": task_id,
            "status": "pending",
            "progress": 0,
            "message": "任务已创建，等待处理",
            "createdAt": datetime.now().isoformat(),
            "startedAt": None,
            "completedAt": None,
            "result": None,
            "error": None
        }

        # 模拟异步处理 (实际中这里会启动后台任务)
        def simulate_processing():
            time.sleep(1)
            if task_id in tasks:
                tasks[task_id]["status"] = "running"
                tasks[task_id]["startedAt"] = datetime.now().isoformat()
                tasks[task_id]["progress"] = 20
                tasks[task_id]["message"] = "正在分析代码..."

            time.sleep(2)
            if task_id in tasks:
                tasks[task_id]["progress"] = 50
                tasks[task_id]["message"] = "正在生成专利草案..."

            time.sleep(2)
            if task_id in tasks:
                tasks[task_id]["progress"] = 80
                tasks[task_id]["message"] = "正在进行合规评审..."

            time.sleep(1)
            if task_id in tasks:
                output_file = f"output/patent-{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
                tasks[task_id]["status"] = "completed"
                tasks[task_id]["progress"] = 100
                tasks[task_id]["message"] = "任务完成"
                tasks[task_id]["completedAt"] = datetime.now().isoformat()
                tasks[task_id]["result"] = {
                    "outputPath": output_file,
                    "iterations": data.get('iterations', 1),
                    "lastReview": "这是一个模拟的专利评审结果。专利草案已生成，包含完整的技术方案描述、创新点分析和权利要求。"
                }

        # 在后台启动模拟处理
        import threading
        thread = threading.Thread(target=simulate_processing)
        thread.daemon = True
        thread.start()

        return jsonify({
            "ok": True,
            "taskId": task_id,
            "message": "任务已提交，请使用任务ID查询进度"
        })

    except Exception as e:
        return jsonify({
            "error": "task_submission_failed",
            "message": str(e)
        }), 500

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """获取任务状态"""
    if task_id not in tasks:
        return jsonify({
            "error": "task_not_found",
            "message": "任务不存在"
        }), 404

    return jsonify(tasks[task_id])

@app.route('/api/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """取消任务"""
    if task_id not in tasks:
        return jsonify({
            "error": "task_not_found",
            "message": "任务不存在"
        }), 404

    if tasks[task_id]["status"] in ["completed", "failed", "cancelled"]:
        return jsonify({
            "error": "cancel_failed",
            "message": "任务已完成或已取消"
        }), 400

    tasks[task_id]["status"] = "cancelled"
    tasks[task_id]["message"] = "任务已取消"

    return jsonify({
        "ok": True,
        "message": "任务已取消"
    })

@app.route('/api/tasks/statistics', methods=['GET'])
def get_task_statistics():
    """获取任务统计"""
    stats = {
        "total_tasks": len(tasks),
        "status_counts": {}
    }

    for task in tasks.values():
        status = task["status"]
        stats["status_counts"][status] = stats["status_counts"].get(status, 0) + 1

    return jsonify({
        "ok": True,
        "statistics": stats
    })

@app.route('/<path:path>')
def static_files(path):
    """静态文件服务"""
    # 尝试从frontend目录提供静态文件
    frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    if os.path.exists(os.path.join(frontend_dir, path)):
        return send_from_directory(frontend_dir, path)

    # 默认返回index.html
    return send_from_directory(frontend_dir, 'index.html')

if __name__ == "__main__":
    print("=== 专利生成系统简化服务器 ===")
    print(f"Python版本: {sys.version}")
    print(f"Flask版本: {getattr(__import__('flask'), '__version__', 'unknown')}")

    # 检查环境变量
    llm_cmd = os.getenv("LLM_CMD")
    if llm_cmd:
        print(f"✓ LLM_CMD 已配置: {llm_cmd}")
    else:
        print("⚠ LLM_CMD 未配置，将使用模拟模式")

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "3000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    print(f"启动服务器: http://{host}:{port}")
    print(f"调试模式: {debug}")
    print("\n可用的API端点:")
    print("  GET  /                 - 主页")
    print("  GET  /api/health       - 健康检查")
    print("  POST /api/generate     - 同步生成")
    print("  POST /api/generate/async - 异步生成")
    print("  GET  /api/tasks/<id>   - 查询任务")
    print("  POST /api/tasks/<id>/cancel - 取消任务")
    print("  GET  /api/tasks/statistics - 任务统计")
    print("\n按 Ctrl+C 停止服务器")
    print("-" * 50)

    try:
        app.run(host=host, port=port, debug=debug, threaded=True)
    except KeyboardInterrupt:
        print("\n服务器已停止")
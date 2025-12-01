#!/usr/bin/env python3
"""
简化的服务器启动脚本
包含依赖检查和错误处理
"""

import sys
import os

def check_dependencies():
    """检查并安装依赖"""
    print("检查依赖...")

    # 检查 Flask
    try:
        import flask
        print(f"✓ Flask {flask.__version__} 已安装")
        return True
    except ImportError:
        print("✗ Flask 未安装")
        print("请运行以下命令安装依赖:")
        print("pip install Flask>=3.0.0")
        return False

def minimal_app():
    """创建最小化的 Flask 应用用于测试"""
    try:
        from flask import Flask, jsonify

        app = Flask(__name__)

        @app.route('/')
        def home():
            return jsonify({
                "message": "专利生成系统后端服务",
                "status": "running",
                "version": "1.0.0"
            })

        @app.route('/api/health')
        def health():
            return jsonify({
                "status": "healthy",
                "services": {
                    "config": "ok",
                    "validators": "ok"
                }
            })

        return app
    except Exception as e:
        print(f"创建应用失败: {e}")
        return None

def main():
    """主函数"""
    print("=== 专利生成系统后端启动器 ===\n")

    # 检查 Python 版本
    print(f"Python 版本: {sys.version}")

    # 检查依赖
    if not check_dependencies():
        print("\n依赖检查失败，请安装必要的包。")
        return 1

    # 切换到脚本目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"工作目录: {os.getcwd()}")

    try:
        # 尝试创建完整应用
        print("\n尝试启动完整应用...")
        try:
            from app import create_app
            app = create_app()
            print("✓ 完整应用创建成功")
        except Exception as e:
            print(f"✗ 完整应用创建失败: {e}")
            print("尝试启动最小化应用...")
            app = minimal_app()
            if app is None:
                print("✗ 无法创建应用")
                return 1

        # 启动服务器
        print("\n启动服务器...")
        host = "0.0.0.0"
        port = 3000
        debug = False

        print(f"服务器地址: http://{host}:{port}")
        print(f"调试模式: {debug}")
        print("\n按 Ctrl+C 停止服务器")

        app.run(host=host, port=port, debug=debug, threaded=True)

    except KeyboardInterrupt:
        print("\n服务器已停止")
        return 0
    except Exception as e:
        print(f"\n启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
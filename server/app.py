"""
Flask应用入口
创建Flask实例，注册蓝图，初始化数据库和CORS
"""
import os
from flask import Flask
from flask_cors import CORS
from config import Config
from models import db
# 注册蓝图（路由模块）
from routes.auth import auth_bp
from routes.knowledge_base import kb_bp
from routes.document import doc_bp
from routes.chat import chat_bp
from routes.user import user_bp
from routes.stats import stats_bp


def create_app():
    """
    应用工厂函数
    创建并配置Flask应用实例
    :return: Flask应用实例
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    # 初始化数据库
    db.init_app(app)

    # 启用跨域支持
    CORS(app, supports_credentials=True)

    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(kb_bp, url_prefix='/api/knowledge_base')
    app.register_blueprint(doc_bp, url_prefix='/api/document')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(stats_bp, url_prefix='/api/stats')

    # 启动时预加载嵌入模型，避免首个问答请求长时间卡在模型加载
    with app.app_context():
        try:
            from services.app_services import get_vector_service

            get_vector_service()
            app.logger.info('向量嵌入模型已预加载')
        except Exception as e:
            app.logger.warning('向量嵌入模型预加载失败（首个相关请求仍会尝试加载）: %s', e)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)

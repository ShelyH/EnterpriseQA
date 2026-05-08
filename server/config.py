"""
项目配置文件
包含数据库、Ollama、Chroma等配置信息
"""
import os

from langchain_openai import ChatOpenAI


class Config:
    """基础配置类"""

    # Flask密钥，用于JWT签名
    SECRET_KEY = os.environ.get('SECRET_KEY', 'enterprise-qa-secret-key-2024')

    # MySQL数据库配置（端口3308，密码123456）
    MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'mysql')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'db_enterprise_qa')

    # SQLAlchemy数据库连接URI
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT Token有效期（秒），默认24小时
    JWT_EXPIRATION = 86400

    # ChromaDB持久化存储路径
    CHROMA_PERSIST_DIR = os.environ.get(
        'CHROMA_PERSIST_DIR',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chroma_data')
    )

    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 最大上传文件大小：50MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'md', 'docx'}

    # 文档分块配置
    CHUNK_SIZE = 1000  # 每个分块的字符数
    CHUNK_OVERLAP = 100  # 分块之间的重叠字符数

    # 向量化批处理配置
    EMBED_BATCH_SIZE = 10  # 分块数量
    EMBED_MAX_RETRIES = 3  # 嵌入失败最大重试次数

    # RAG检索配置
    RETRIEVER_TOP_K = 10  # 检索返回的相似文档数量

    # LLM设置：支持 DeepSeek 或内网 OpenAI 兼容服务（如 vLLM、Ollama、Xinference、FastChat 等）
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.deepseek.com')
    LLM_API_KEY = os.environ.get('LLM_API_KEY') or os.environ.get('DEEPSEEK_API_KEY') or 'EMPTY'
    LLM_MODEL = os.environ.get('LLM_MODEL', 'deepseek-v4-pro')
    LLM_TEMPERATURE = float(os.environ.get('LLM_TEMPERATURE', 0.7))
    LLM_MAX_TOKENS = int(os.environ.get('LLM_MAX_TOKENS', 4096))

    LLM = ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        streaming=True,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL
    )

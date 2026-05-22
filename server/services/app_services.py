"""
进程内复用重量级依赖（嵌入模型、LLM 客户端），避免每个请求重复初始化。
"""
import threading

_lock = threading.Lock()
_vector_service = None
_rag_service = None


def get_vector_service():
    """单例向量服务（嵌入模型加载成本高，必须复用）。"""
    global _vector_service
    if _vector_service is None:
        with _lock:
            if _vector_service is None:
                from flask import current_app

                store = current_app.config.get('VECTOR_STORE', 'milvus')
                if store == 'chroma':
                    from services.vector_service import VectorService

                    _vector_service = VectorService()
                else:
                    from services.vector_service_milvus import MilvusVectorService

                    _vector_service = MilvusVectorService()

    return _vector_service


def get_rag_service():
    """单例 RAG 服务（共享向量检索与 LLM 客户端）。"""
    global _rag_service
    if _rag_service is None:
        with _lock:
            if _rag_service is None:
                from services.rag_service import RAGService

                _rag_service = RAGService(vector_service=get_vector_service())
    return _rag_service

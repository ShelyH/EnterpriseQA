"""
RAG问答核心服务
基于LangChain构建检索增强生成（RAG）问答链
"""
import time
from flask import current_app
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from services.vector_service import VectorService


# RAG系统提示词模板
SYSTEM_PROMPT = """你是一个企业内部知识库智能问答助手。请根据以下提供的参考资料来回答用户的问题。

要求：
请确保你的回答完全基于这些上下文。

参考资料：
{context}
"""

# 用户提问模板
USER_PROMPT = "{question}"


def _extract_source_docs(docs):
    """
    提取参考文档来源信息
    :param docs: 检索到的文档列表
    :return: 来源信息列表
    """
    sources = []
    seen = set()
    for doc in docs:
        file_name = doc.metadata.get('file_name', '未知')
        if file_name not in seen:
            seen.add(file_name)
            sources.append({
                'file_name': file_name,
                'content': doc.page_content[:200]
            })
    return sources


class RAGService:
    """RAG问答服务类"""

    def __init__(self, vector_service=None):
        """初始化 LLM 与向量服务；vector_service 建议由 app_services 注入以进程内复用。"""

        self.llm = current_app.config['LLM']
        self.vector_service = vector_service if vector_service is not None else VectorService()
        self._prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("human", USER_PROMPT),
            ]
        )

    def _format_docs(self, docs):
        """
        将检索到的文档格式化为上下文文本
        :param docs: 检索到的文档列表
        :return: 格式化后的文本
        """
        formatted = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get('file_name', '未知来源')
            formatted.append(f"[来源{i}: {source}]\n{doc.page_content}")
        return '\n\n'.join(formatted)

    def _create_rag_chain(self, docs):
        """构建RAG问答链"""
        return (
                {
                    'context': lambda x: self._format_docs(docs),
                    'question': RunnablePassthrough()
                }
                | self._prompt
                | self.llm
                | StrOutputParser()
        )

    def _retrieve_docs(self, question, kb_id):
        retriever = self.vector_service.get_retriever(kb_id)
        return retriever.invoke(question)

    def ask(self, question, kb_id):
        """
        RAG问答主方法
        流程: 用户提问 -> 向量检索 -> 构建上下文 -> LLM生成回答
        :param question: 用户问题
        :param kb_id: 知识库ID
        :return: (回答文本, 参考来源列表)
        """
        docs = self._retrieve_docs(question, kb_id)

        if not docs:
            return '抱歉，在知识库中未找到与您问题相关的内容，请尝试换个方式提问。', []

        rag_chain = self._create_rag_chain(docs)
        start = time.perf_counter()
        answer = rag_chain.invoke(question)
        elapsed = time.perf_counter() - start
        print(f"rag_chain.invoke 耗时: {elapsed:.4f} 秒")
        source_docs = _extract_source_docs(docs)

        return answer, source_docs

    def ask_stream(self, question, kb_id):
        """
        RAG流式问答方法
        :param question: 用户问题
        :param kb_id: 知识库ID
        :return: 逐段回答文本生成器和参考来源列表
        """
        docs = self._retrieve_docs(question, kb_id)

        if not docs:
            source_docs = []
            chunks = iter(['抱歉，在知识库中未找到与您问题相关的内容，请尝试换个方式提问。'])
            return chunks, source_docs

        rag_chain = self._create_rag_chain(docs)
        source_docs = _extract_source_docs(docs)
        return rag_chain.stream(question), source_docs

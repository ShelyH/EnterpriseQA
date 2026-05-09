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
SYSTEM_PROMPT = """你是一个企业内部知识库智能问答助手。你的任务是只基于下方“参考资料”回答用户问题，并尽可能给出完整、准确、结构清晰的答案。
参考资料格式说明：
参考资料由多个 <document> 块组成。每个 <document> 是一个独立来源，包含 doc_id、file_name、chunk_index 和 content。
回答规则：
1. 严格依据参考资料作答，不要编造参考资料中没有的信息。
2. 必须尊重文档边界，不要把不同 document 的内容混为同一来源。
3. 如果多个 document 可以共同支持答案，可以综合回答，但要说明信息分别来自哪些文件。
4. 如果不同 document 之间存在冲突或口径不同，应明确指出差异，不要强行合并。
5. 回答关键结论时，尽量在句末标注来源文件名，例如：（来源：员工请假管理办法.docx）。
6. 如果参考资料只能支持部分答案，请先回答已知部分，再明确说明“参考资料中未提供/未明确说明”的内容。
7. 如果参考资料与问题无关或无法回答，请直接说明无法从当前知识库资料中找到答案。
8. 保持中文回答，语言简洁专业；必要时使用分点、编号或小标题提升可读性。
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
            doc_id = doc.metadata.get('doc_id', '未知')
            file_name = doc.metadata.get('file_name', '未知来源')
            chunk_index = doc.metadata.get('chunk_index', '未知')
            formatted.append(
                f"<document index=\"{i}\">\n"
                f"<doc_id>{doc_id}</doc_id>\n"
                f"<file_name>{file_name}</file_name>\n"
                f"<chunk_index>{chunk_index}</chunk_index>\n"
                f"<content>\n{doc.page_content}\n</content>\n"
                f"</document>"
            )
        return "\n\n".join(formatted)

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

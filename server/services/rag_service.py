"""
RAG问答核心服务
基于LangChain构建检索增强生成（RAG）问答链
"""
from flask import current_app
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from services.vector_service import VectorService

# RAG系统提示词模板
SYSTEM_PROMPT = """你是一个企业内部知识库智能问答助手。你的任务是只基于下方“参考资料”回答用户问题，并尽可能给出完整、准确、结构清晰的答案。
参考资料格式说明：
参考资料由多个 <document> 块组成。每个 <document> 对应知识库中的一份独立文件，属性 index 为引用编号 n（每个编号在整个资料中只出现一次）；块内包含 doc_id、file_name、chunk_index 与 content。同一文件若有多段检索内容，已合并在一个 <document> 块内。
回答规则：
1. 严格依据参考资料作答，不要编造参考资料中没有的信息。
2. 不同 index 代表不同文件，不要把不同 index 的内容混为同一来源；同一 index 块内可综合阅读。
3. 如果多个 document 可以共同支持答案，可以综合回答。
4. 如果不同 document 之间存在冲突或口径不同，应明确指出差异，不要强行合并。
5. 如果参考资料只能支持部分答案，请先回答已知部分，再明确说明“参考资料中未提供/未明确说明”的内容。
6. 如果参考资料与问题无关或无法回答，请直接说明无法从当前知识库资料中找到答案。
7. 保持中文回答，语言简洁专业；必要时使用分点、编号或小标题提升可读性。
8. 文档引用：正文中的【n】必须与下方参考资料的 <document index="n"> 一一对应，且仅使用该列表中出现的编号；每个编号对应唯一一份文件。引用同一文件时只使用同一个【n】，不要为同一文件编造多个不同编号。
参考资料：
{context}
"""

# 用户提问模板
USER_PROMPT = "{question}"


def _doc_dedupe_key(meta):
    """用于合并「同一文档」多条检索：优先 doc_id，否则用 file_name。"""
    doc_id = meta.get('doc_id', '')
    if doc_id not in (None, '', '未知'):
        return ('id', str(doc_id))
    return ('name', str(meta.get('file_name', '未知来源')))


def _merge_retrieved_docs_for_context(docs):
    """
    按文档合并检索片段，顺序为检索结果中首次出现的文档顺序；
    用于构造「每个 index 对应唯一文档」的 LLM 上下文。
    """
    order = []
    buckets = {}
    for doc in docs:
        meta = doc.metadata or {}
        key = _doc_dedupe_key(meta)
        if key not in buckets:
            buckets[key] = {'meta': meta, 'texts': []}
            order.append(key)
        text = (_doc_content_for_llm(doc) or '').strip()
        if text:
            buckets[key]['texts'].append(text)
    merged = []
    for key in order:
        b = buckets[key]
        parts = []
        seen = set()
        for t in b['texts']:
            if t not in seen:
                seen.add(t)
                parts.append(t)
        merged_text = '\n\n---\n\n'.join(parts) if len(parts) > 1 else (parts[0] if parts else '')
        merged.append({
            'meta': b['meta'],
            'text': merged_text,
            'source_chunk_count': len(b['texts']),
        })
    return merged


def _extract_source_docs_from_merged(merged_items):
    """与合并后的 <document index> 一致：每条仅含一个 ref_index。"""
    sources = []
    for i, item in enumerate(merged_items, 1):
        meta = item['meta']
        sources.append({
            'ref_index': i,
            'doc_id': meta.get('doc_id', '') or '',
            'file_name': meta.get('file_name', '未知来源'),
        })
    return sources


def _doc_content_for_llm(doc):
    """
    送入 LLM 的正文：若存在 SentenceWindow 写入的 window 元数据则使用窗口文本，否则用 page_content。
    """
    from flask import has_request_context, current_app

    meta = doc.metadata or {}
    keys = []
    if has_request_context():
        keys.append(current_app.config.get('SENTENCE_WINDOW_METADATA_KEY', 'window'))
    if 'window' not in keys:
        keys.append('window')
    for k in keys:
        window_text = meta.get(k)
        if isinstance(window_text, str) and window_text.strip():
            return window_text
    return doc.page_content or ''


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

    def _format_merged_context(self, merged_items):
        """将合并后的文档列表格式化为参考资料 XML。"""
        formatted = []
        for i, item in enumerate(merged_items, 1):
            meta = item['meta']
            doc_id = meta.get('doc_id', '未知')
            file_name = meta.get('file_name', '未知来源')
            if item.get('source_chunk_count', 0) > 1:
                chunk_index = '合并'
            else:
                chunk_index = meta.get('chunk_index', '未知')
            formatted.append(
                f"<document index=\"{i}\">\n"
                f"<doc_id>{doc_id}</doc_id>\n"
                f"<file_name>{file_name}</file_name>\n"
                f"<chunk_index>{chunk_index}</chunk_index>\n"
                f"<content>\n{item['text']}\n</content>\n"
                f"</document>"
            )
        return "\n\n".join(formatted)

    def _create_rag_chain_merged(self, merged_items):
        """基于合并后的文档构建 RAG 链。"""
        return (
                {
                    'context': lambda x: self._format_merged_context(merged_items),
                    'question': RunnablePassthrough()
                }
                | self._prompt
                | self.llm
                | StrOutputParser()
        )

    def _retrieve_docs(self, question, kb_id):
        retriever = self.vector_service.get_retriever(kb_id)
        docs = retriever.invoke(question)
        top_k = current_app.config['RETRIEVER_TOP_K']
        if len(docs) > top_k:
            docs = docs[:top_k]
        return docs

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

        merged = _merge_retrieved_docs_for_context(docs)
        rag_chain = self._create_rag_chain_merged(merged)
        source_docs = _extract_source_docs_from_merged(merged)
        return rag_chain.stream(question), source_docs

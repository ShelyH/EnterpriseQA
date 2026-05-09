"""
问答对话路由
提供RAG问答和对话历史查询接口
"""
import uuid
import json
from flask import Blueprint, request, g, Response, stream_with_context
from models import db
from models.chat_history import ChatHistory
from models.knowledge_base import KnowledgeBase
from utils.auth import login_required
from utils.response import success, error, page_response

# 创建问答蓝图
chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/ask/stream', methods=['POST'])
@login_required
def ask_stream():
    """
    RAG知识库流式问答接口
    使用Server-Sent Events返回answer_delta（正文流式）→ source_docs → done/error
    """
    data = request.get_json()
    if not data:
        return error('请提供问题信息')

    question = data.get('question', '').strip()
    kb_id = data.get('kb_id')
    session_id = data.get('session_id', str(uuid.uuid4().hex[:16]))

    if not question:
        return error('问题不能为空')
    if not kb_id:
        return error('请选择知识库')

    kb = KnowledgeBase.query.get(kb_id)
    if not kb or kb.status != 1:
        return error('知识库不存在或已禁用')

    user_id = g.user_id

    def sse_event(event, payload):
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    @stream_with_context
    def generate():
        answer_parts = []
        source_docs = []

        yield sse_event('ping', {'message': 'connected'})

        try:
            from services.app_services import get_rag_service

            chunks, source_docs = get_rag_service().ask_stream(question, kb_id)

            for chunk in chunks:
                if not chunk:
                    continue
                answer_parts.append(chunk)
                yield sse_event('answer_delta', {'delta': chunk})

            yield sse_event('source_docs', {'source_docs': source_docs, 'session_id': session_id})

            answer = ''.join(answer_parts)
            chat = ChatHistory(
                user_id=user_id,
                kb_id=kb_id,
                session_id=session_id,
                question=question,
                answer=answer,
                source_docs=json.dumps(source_docs, ensure_ascii=False)
            )
            db.session.add(chat)
            db.session.commit()
            yield sse_event('done', {
                'answer': answer,
                'source_docs': source_docs,
                'session_id': session_id,
                'chat_id': chat.id
            })
        except Exception as e:
            db.session.rollback()
            yield sse_event('error', {'message': f'问答服务异常: {str(e)}'})

    response = Response(generate(), mimetype='text/event-stream; charset=utf-8')
    response.headers['Cache-Control'] = 'no-cache, no-transform'
    response.headers['Connection'] = 'keep-alive'
    response.headers['X-Accel-Buffering'] = 'no'
    return response


@chat_bp.route('/history', methods=['GET'])
@login_required
def get_history():
    """
    获取对话历史列表（分页）
    查询参数: page, page_size, kb_id(可选)
    普通用户只能查看自己的记录，管理员可查看所有
    """
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    kb_id = request.args.get('kb_id', type=int)

    query = ChatHistory.query

    # 普通用户只能查看自己的对话记录
    if g.role != 'admin':
        query = query.filter_by(user_id=g.user_id)

    if kb_id:
        query = query.filter_by(kb_id=kb_id)

    query = query.order_by(ChatHistory.create_time.desc())
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)

    items = [item.to_dict() for item in pagination.items]
    return page_response(items, pagination.total, page, page_size)


@chat_bp.route('/session/<session_id>', methods=['GET'])
@login_required
def get_session(session_id):
    """
    获取指定会话的所有对话记录
    路径参数: session_id(会话ID)
    """
    query = ChatHistory.query.filter_by(session_id=session_id)

    # 普通用户只能查看自己的对话
    if g.role != 'admin':
        query = query.filter_by(user_id=g.user_id)

    chats = query.order_by(ChatHistory.create_time.asc()).all()
    return success([chat.to_dict() for chat in chats])

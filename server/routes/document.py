"""
文档路由
提供文档上传、列表查询和删除接口
"""
import os
from flask import Blueprint, request, g, current_app
from models import db
from models.document import Document
from models.knowledge_base import KnowledgeBase
from utils.auth import login_required, admin_required
from utils.response import success, error, page_response

# 创建文档蓝图
doc_bp = Blueprint('document', __name__)


def allowed_file(filename):
    """检查文件扩展名是否允许上传"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def _sanitize_storage_stem(original_filename):
    """从上传文件名得到安全的磁盘文件主名（不含扩展名），去掉路径与 Windows 非法字符。"""
    stem = os.path.splitext(os.path.basename((original_filename or '').strip()))[0]
    for ch in '<>:"/\\|?*':
        stem = stem.replace(ch, '_')
    stem = stem.strip(' .')
    return stem or 'upload'


def _allocate_upload_path(upload_folder, original_filename, ext_lower):
    """
    基于原名生成磁盘路径；若已存在同名文件则追加 _1、_2 …
    返回 (完整路径, 磁盘上的文件名)。
    """
    stem = _sanitize_storage_stem(original_filename)
    basename = f'{stem}.{ext_lower}'
    path = os.path.join(upload_folder, basename)
    n = 1
    while os.path.exists(path):
        basename = f'{stem}_{n}.{ext_lower}'
        path = os.path.join(upload_folder, basename)
        n += 1
    return path, basename


@doc_bp.route('/list', methods=['GET'])
@login_required
def get_list():
    """
    获取文档列表（分页）
    查询参数: page, page_size, kb_id
    """
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    kb_id = request.args.get('kb_id', type=int)

    query = Document.query
    if kb_id:
        query = query.filter_by(kb_id=kb_id)

    query = query.order_by(Document.id.asc())
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)

    items = [item.to_dict() for item in pagination.items]
    return page_response(items, pagination.total, page, page_size)


def _collect_upload_files():
    """
    从 multipart 中收集待处理文件。
    支持多文件字段名 files；兼容旧客户端单文件字段 file。
    """
    files = [f for f in request.files.getlist('files') if f and f.filename]
    if not files:
        legacy = request.files.get('file')
        if legacy and legacy.filename:
            files = [legacy]
    return files


def _process_one_upload(file_storage, kb_id, kb):
    """
    保存单个文件、写入数据库并执行向量化。
    :return: dict，含 success、file_name、document（失败且未建库时为 None）、error
    """
    display_name = os.path.basename((file_storage.filename or '').strip()) or file_storage.filename
    if not allowed_file(file_storage.filename):
        ext_hint = ', '.join(sorted(current_app.config['ALLOWED_EXTENSIONS']))
        return {
            'success': False,
            'file_name': display_name,
            'document': None,
            'error': f'不支持的文件类型，仅支持: {ext_hint}',
        }

    file_ext = file_storage.filename.rsplit('.', 1)[1].lower()
    file_path, _ = _allocate_upload_path(
        current_app.config['UPLOAD_FOLDER'],
        file_storage.filename,
        file_ext,
    )
    file_storage.save(file_path)
    file_size = os.path.getsize(file_path)

    doc = Document(
        kb_id=kb_id,
        file_name=file_storage.filename,
        file_path=file_path,
        file_size=file_size,
        file_type=file_ext,
        creator_id=g.user_id,
    )
    db.session.add(doc)
    db.session.commit()

    try:
        from services.app_services import get_vector_service

        vector_service = get_vector_service()
        chunk_count = vector_service.process_document(
            doc.id,
            file_path,
            file_ext,
            kb_id,
            display_file_name=display_name,
        )
        doc.status = 'vectorized'
        doc.chunk_count = chunk_count
        kb.doc_count = Document.query.filter_by(kb_id=kb_id, status='vectorized').count()
        db.session.commit()
        return {'success': True, 'file_name': display_name, 'document': doc.to_dict(), 'error': None}
    except ConnectionError:
        doc.status = 'failed'
        db.session.commit()
        return {
            'success': False,
            'file_name': display_name,
            'document': doc.to_dict(),
            'error': '无法连接Ollama服务，请确认Ollama已启动并可访问',
        }
    except Exception as e:
        doc.status = 'failed'
        db.session.commit()
        err_msg = str(e)
        if 'status code' in err_msg:
            err_msg = f'Ollama服务处理异常，请检查Ollama运行状态和系统资源: {err_msg}'
        else:
            err_msg = f'文档向量化失败: {err_msg}'
        return {
            'success': False,
            'file_name': display_name,
            'document': doc.to_dict(),
            'error': err_msg,
        }


@doc_bp.route('/upload', methods=['POST'])
@admin_required
def upload():
    """
    上传文档并进行向量化处理（仅管理员）
    表单参数: kb_id（知识库ID）；files（可多文件）或 file（单文件，兼容旧版）
    """
    kb_id = request.form.get('kb_id', type=int)
    if not kb_id:
        return error('请选择知识库')

    kb = KnowledgeBase.query.get(kb_id)
    if not kb:
        return error('知识库不存在')

    files = _collect_upload_files()
    if not files:
        return error('请选择要上传的文件')

    max_n = current_app.config.get('MAX_UPLOAD_FILES_PER_REQUEST', 30)
    if len(files) > max_n:
        return error(f'单次最多上传 {max_n} 个文件')

    results = []
    for file_storage in files:
        results.append(_process_one_upload(file_storage, kb_id, kb))

    succeeded = sum(1 for r in results if r['success'])
    failed = len(results) - succeeded
    if failed:
        message = f'上传完成：成功 {succeeded} 个，失败 {failed} 个'
    else:
        message = f'上传成功（共 {succeeded} 个文件）'

    return success(
        {
            'items': results,
            'summary': {
                'total': len(results),
                'succeeded': succeeded,
                'failed': failed,
            },
        },
        message,
    )


def _delete_document_record(doc):
    kb_id = doc.kb_id

    try:
        from services.app_services import get_vector_service

        vector_service = get_vector_service()
        vector_service.delete_document(doc.id, kb_id)
    except Exception:
        pass

    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.session.delete(doc)
    return kb_id


def _refresh_kb_doc_counts(kb_ids):
    for kb_id in set(kb_ids):
        kb = KnowledgeBase.query.get(kb_id)
        if kb:
            kb.doc_count = Document.query.filter_by(kb_id=kb_id, status='vectorized').count()


@doc_bp.route('/batch-delete', methods=['POST'])
@admin_required
def batch_delete():
    """
    批量删除文档（仅管理员）
    请求体 JSON: { "ids": [1, 2, 3] }
    """
    data = request.get_json() or {}
    raw_ids = data.get('ids')
    if not raw_ids or not isinstance(raw_ids, list):
        return error('请提供要删除的文档ID列表')

    id_set = set()
    for i in raw_ids:
        if isinstance(i, int) and i > 0:
            id_set.add(i)
        elif isinstance(i, str) and i.isdigit():
            id_set.add(int(i))

    if not id_set:
        return error('请提供有效的文档ID')

    docs = Document.query.filter(Document.id.in_(id_set)).all()
    if not docs:
        return error('未找到可删除的文档', 404)

    affected_kb_ids = []
    for doc in docs:
        affected_kb_ids.append(_delete_document_record(doc))

    db.session.flush()
    _refresh_kb_doc_counts(affected_kb_ids)
    db.session.commit()
    return success({'deleted': len(docs)}, message=f'已删除 {len(docs)} 个文档')


@doc_bp.route('/<int:doc_id>', methods=['DELETE'])
@admin_required
def delete(doc_id):
    """
    删除文档（仅管理员）
    同时删除对应的向量数据和物理文件
    """
    doc = Document.query.get(doc_id)
    if not doc:
        return error('文档不存在', 404)

    kb_id = _delete_document_record(doc)
    db.session.flush()
    _refresh_kb_doc_counts([kb_id])
    db.session.commit()
    return success(message='删除成功')

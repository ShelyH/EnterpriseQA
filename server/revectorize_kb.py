"""
重新向量化已有知识库文档。

用途：修改 CHUNK_SIZE / CHUNK_OVERLAP 后，不重新上传文件，直接基于数据库中保存的
Document.file_path 对已有文档重新切块并写入 Milvus（当前向量库）。

示例：
    python revectorize_kb.py --kb-id 1
    python revectorize_kb.py --all
    python revectorize_kb.py --doc-id 12
    python revectorize_kb.py --kb-id 1 --dry-run
"""
import argparse
import os
import sys

from app import create_app
from models import db
from models.document import Document
from models.knowledge_base import KnowledgeBase
from services.app_services import get_vector_service


def parse_args():
    parser = argparse.ArgumentParser(description="重新向量化已有知识库文档")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--kb-id", type=int, help="只重新向量化指定知识库 ID 下的文档")
    target.add_argument("--doc-id", type=int, help="只重新向量化指定文档 ID")
    target.add_argument("--all", action="store_true", help="重新向量化所有知识库文档")
    parser.add_argument("--dry-run", action="store_true", help="只打印将处理的文档，不实际删除或写入向量")
    parser.add_argument("--include-failed", action="store_true", help="包含当前状态为 failed/uploading 的文档")
    return parser.parse_args()


def load_documents(args):
    query = Document.query

    if args.kb_id is not None:
        kb = KnowledgeBase.query.get(args.kb_id)
        if not kb:
            raise ValueError(f"知识库不存在: kb_id={args.kb_id}")
        query = query.filter_by(kb_id=args.kb_id)
    elif args.doc_id is not None:
        query = query.filter_by(id=args.doc_id)

    if not args.include_failed:
        query = query.filter_by(status="vectorized")

    return query.order_by(Document.kb_id.asc(), Document.id.asc()).all()


def update_kb_doc_count(kb_ids):
    for kb_id in kb_ids:
        kb = KnowledgeBase.query.get(kb_id)
        if not kb:
            continue
        kb.doc_count = Document.query.filter_by(kb_id=kb_id, status="vectorized").count()


def revectorize_documents(docs, dry_run=False):
    if not docs:
        print("没有找到需要重新向量化的文档")
        return 0, 0

    print(f"待处理文档数: {len(docs)}")
    for doc in docs:
        print(
            f"- doc_id={doc.id}, kb_id={doc.kb_id}, file_name={doc.file_name}, "
            f"status={doc.status}, path={doc.file_path}"
        )

    if dry_run:
        print("dry-run 模式：未执行删除和重新向量化")
        return 0, 0

    vector_service = get_vector_service()
    success_count = 0
    failed_count = 0
    affected_kb_ids = set()

    for index, doc in enumerate(docs, 1):
        print(f"\n[{index}/{len(docs)}] 开始处理: doc_id={doc.id}, file_name={doc.file_name}")
        affected_kb_ids.add(doc.kb_id)

        if not os.path.exists(doc.file_path):
            doc.status = "failed"
            db.session.commit()
            failed_count += 1
            print(f"失败：文件不存在: {doc.file_path}")
            continue

        try:
            doc.status = "uploading"
            db.session.commit()

            vector_service.delete_document(doc.id, doc.kb_id)
            chunk_count = vector_service.process_document(
                doc.id,
                doc.file_path,
                doc.file_type,
                doc.kb_id,
                display_file_name=doc.file_name,
            )

            doc.chunk_count = chunk_count
            doc.status = "vectorized"
            db.session.commit()

            success_count += 1
            print(f"完成：doc_id={doc.id}, chunks={chunk_count}")
        except Exception as exc:
            db.session.rollback()
            doc = Document.query.get(doc.id)
            if doc:
                doc.status = "failed"
                db.session.commit()
            failed_count += 1
            print(f"失败：doc_id={doc.id}, error={exc}")

    update_kb_doc_count(affected_kb_ids)
    db.session.commit()

    return success_count, failed_count


def main():
    args = parse_args()
    app = create_app()

    with app.app_context():
        try:
            docs = load_documents(args)
            success_count, failed_count = revectorize_documents(docs, dry_run=args.dry_run)
        except Exception as exc:
            print(f"执行失败: {exc}", file=sys.stderr)
            return 1

    print(f"\n执行结束：成功 {success_count} 个，失败 {failed_count} 个")
    return 0 if failed_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

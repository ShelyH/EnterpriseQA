"""
RAG检索召回率评估脚本

使用方法：
    python evaluate_retrieval.py --kb-id 1                       评估指定知识库
    python evaluate_retrieval.py --kb-id 1 --k 5 10 20           指定k值列表
    python evaluate_retrieval.py --all                            评估所有知识库
    python evaluate_retrieval.py --list-docs                      查看所有文档ID与名称对照
    python evaluate_retrieval.py --kb-id 1 --test-file tests.json 使用外部测试集文件

外部测试集 JSON 格式：
{
    "知识库ID": {
        "问题1": [期望的文档ID列表],
        "问题2": [期望的文档ID列表]
    }
}
"""
import argparse
import json
import sys
import os

# 将项目根目录加入 sys.path，使 import 能找到 services、models 等模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from config import Config
from models import db
from models.document import Document
from models.knowledge_base import KnowledgeBase
from services.app_services import get_vector_service


# ============================================================
# 默认测试用例（可根据实际文档内容调整）
# 格式：{ kb_id: { "问题": [期望检索到的文档ID列表] } }
# ============================================================
DEFAULT_TEST_CASES = {
    1: {  # 人事制度知识库
        "公司考勤制度中迟到如何定义？": [12],
        "考勤制度对旷工是怎么规定的？": [12],
        "薪酬福利制度包括哪些内容？": [13],
        "请假审批流程是什么？": [14],
        "年假可以休几天？": [14],
        "员工行为规范有哪些要求？": [15],
        "员工着装要求是什么？": [15],
    },
    2: {  # 技术规范知识库
        "请写出上传归档病案接口 AnnounceUpload 中，至少 5 个必填字段": [13],
        "ftp站点怎么部署？": [20],
        "无纸化归档流程有哪些？": [12],
        "Python编码规范要求什么？": [11],
        "电子病历系统有哪些文书？": [17],
        "病案系统会有哪些报错编码？": [13],
    },
    3: {  # 系统操作知识库
        "OA系统怎么使用？": [20],
        "OA系统审批流程怎么操作？": [20],
        "企业邮箱如何配置？": [21],
        "项目管理平台如何操作？": [22],
        "新员工入职需要做什么？": [23],
        "新员工培训流程是什么？": [23],
    },
}


def create_app_context():
    """创建 Flask 应用上下文，用于加载配置和数据库"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    app.app_context().push()
    return app


def list_documents(kb_id=None):
    """列出文档信息，辅助构建测试用例"""
    create_app_context()
    query = Document.query
    if kb_id:
        query = query.filter_by(kb_id=kb_id)
    docs = query.order_by(Document.kb_id, Document.id).all()

    print(f"\n{'='*80}")
    print(f"{'文档ID列表':^80}")
    print(f"{'='*80}")
    print(f"{'ID':<6} {'知识库ID':<10} {'知识库名称':<20} {'文件名称':<40}")
    print(f"{'-'*80}")
    for doc in docs:
        kb_name = doc.knowledge_base.kb_name if doc.knowledge_base else '未知'
        print(f"{doc.id:<6} {doc.kb_id:<10} {kb_name:<20} {doc.file_name:<40}")
    print(f"{'='*80}")
    print(f"总计: {len(docs)} 个文档\n")


def load_test_cases(args):
    """加载测试用例：优先使用外部文件，否则使用默认测试用例"""
    if args.test_file:
        with open(args.test_file, 'r', encoding='utf-8') as f:
            all_cases = json.load(f)
        # 将 key 转为 int
        return {int(k): v for k, v in all_cases.items()}
    return DEFAULT_TEST_CASES


def recall_at_k(retrieved_docs, relevant_doc_ids, k):
    """
    计算 Recall@k
    :param retrieved_docs: 检索到的文档列表（含 metadata）
    :param relevant_doc_ids: 相关的文档ID列表 (ground truth)
    :param k: top-k 截断
    :return: Recall@k (0-1)
    """
    retrieved_ids = set()
    for doc in retrieved_docs[:k]:
        doc_id = doc.metadata.get('doc_id')
        if doc_id is not None:
            retrieved_ids.add(doc_id)

    relevant = set(relevant_doc_ids)
    if len(relevant) == 0:
        return 1.0

    hits = len(retrieved_ids & relevant)
    return hits / len(relevant)


def precision_at_k(retrieved_docs, relevant_doc_ids, k):
    """
    计算 Precision@k（辅助指标）
    衡量检索结果中有多少是相关的
    """
    retrieved_ids = set()
    for doc in retrieved_docs[:k]:
        doc_id = doc.metadata.get('doc_id')
        if doc_id is not None:
            retrieved_ids.add(doc_id)

    relevant = set(relevant_doc_ids)
    if k == 0:
        return 0.0
    hits = len(retrieved_ids & relevant)
    return hits / k


def hit_rate_at_k(retrieved_docs, relevant_doc_ids, k):
    """
    计算 HitRate@k：只要检索到了至少一个相关文档即为命中
    """
    retrieved_ids = set()
    for doc in retrieved_docs[:k]:
        doc_id = doc.metadata.get('doc_id')
        if doc_id is not None:
            retrieved_ids.add(doc_id)

    relevant = set(relevant_doc_ids)
    return 1.0 if len(retrieved_ids & relevant) > 0 else 0.0


def detailed_query_report(retrieved_docs, relevant_ids, question, k):
    """输出单个查询的详细结果报告"""
    retrieved_ids = {}
    for rank, doc in enumerate(retrieved_docs[:k], 1):
        did = doc.metadata.get('doc_id')
        fname = doc.metadata.get('file_name', '未知')
        score = doc.metadata.get('relevance_score', None)
        content_preview = doc.page_content[:80].replace('\n', ' ')
        retrieved_ids[rank] = {
            'doc_id': did,
            'file_name': fname,
            'content_preview': content_preview,
        }

    relevant_set = set(relevant_ids)
    hits = {rank: info for rank, info in retrieved_ids.items()
            if info['doc_id'] in relevant_set}

    print(f"\n  ▶ 问题: {question}")
    print(f"    期望文档: {relevant_ids}")
    print(f"    检索结果 (top-{k}):")
    for rank, info in retrieved_ids.items():
        marker = " ✅" if info['doc_id'] in relevant_set else ""
        print(f"      [{rank}] doc_id={info['doc_id']} | {info['file_name']}{marker}")
        print(f"           预览: {info['content_preview']}")

    print(f"    命中: {len(hits)}/{len(relevant_ids)} 个相关文档")


def evaluate_kb(kb_id, k_values, vector_service, test_cases):
    """
    评估指定知识库的检索召回率
    """
    print(f"\n正在加载知识库 {kb_id} 的检索器...")
    retriever = vector_service.get_retriever(kb_id)

    # 过滤属于当前知识库的测试用例
    kb_cases = {q: ids for q, ids in test_cases.get(kb_id, {}).items()}
    if not kb_cases:
        print(f"  知识库 {kb_id} 没有测试用例，跳过")
        return None

    print(f"  共 {len(kb_cases)} 个测试查询")

    # 存储每个查询的详细结果，用于输出详细报告
    query_details = []

    for k in k_values:
        k_results = {
            'recalls': [],
            'precisions': [],
            'hit_rates': [],
        }

        for question, relevant_ids in kb_cases.items():
            # 执行检索
            retrieved_docs = retriever.invoke(question)

            recall = recall_at_k(retrieved_docs, relevant_ids, k)
            precision = precision_at_k(retrieved_docs, relevant_ids, k)
            hit_rate = hit_rate_at_k(retrieved_docs, relevant_ids, k)

            k_results['recalls'].append(recall)
            k_results['precisions'].append(precision)
            k_results['hit_rates'].append(hit_rate)

        avg_recall = sum(k_results['recalls']) / len(k_results['recalls'])
        avg_precision = sum(k_results['precisions']) / len(k_results['precisions'])
        avg_hit_rate = sum(k_results['hit_rates']) / len(k_results['hit_rates'])

        query_details.append({
            'k': k,
            'avg_recall': round(avg_recall, 4),
            'avg_precision': round(avg_precision, 4),
            'avg_hit_rate': round(avg_hit_rate, 4),
            'min_recall': round(min(k_results['recalls']), 4),
            'max_recall': round(max(k_results['recalls']), 4),
            'recalls_per_query': k_results['recalls'],
            'hit_rates_per_query': k_results['hit_rates'],
        })

    return query_details


def print_evaluation_report(kb_id, results, k_values, test_cases):
    """打印评估报告"""
    if results is None:
        return

    kb_cases = test_cases.get(kb_id, {})
    print(f"\n{'='*70}")
    print(f" 📊 知识库 {kb_id} 检索召回率评估报告")
    print(f"{'='*70}")
    print(f" 测试查询数: {len(kb_cases)}")
    print(f"{'='*70}")

    # 主表格
    header = f"{'k':<8} {'Recall@k':<14} {'Precision@k':<14} {'HitRate@k':<14} {'Recall(min)':<14}"
    print(f"\n{header}")
    print(f"{'-'*70}")

    for r in results:
        print(f"{r['k']:<8} {r['avg_recall']:<14.4f} {r['avg_precision']:<14.4f} {r['avg_hit_rate']:<14.4f} {r['min_recall']:<14.4f}")

    print(f"{'='*70}")

    # 建议
    current_top_k = None
    try:
        from config import Config as AppConfig
        current_top_k = AppConfig.RETRIEVER_TOP_K
    except (ImportError, AttributeError):
        pass

    print(f"\n 📋 建议分析:")
    for r in results:
        if current_top_k and r['k'] == current_top_k:
            if r['avg_recall'] < 0.8:
                print(f"   ⚠️  Recall@{r['k']} = {r['avg_recall']:.2%} < 80%")
                print(f"      建议: 增大 config.py 中 RETRIEVER_TOP_K (当前={current_top_k})")
                print(f"      或: 优化 CHUNK_SIZE / CHUNK_OVERLAP 分块策略")
            if r['avg_precision'] < 0.3:
                print(f"   💡  Precision@{r['k']} = {r['avg_precision']:.2%} < 30%")
                print(f"      建议: 减小 RETRIEVER_TOP_K 或尝试使用 MMR 检索策略")
            if r['avg_recall'] >= 0.9 and r['avg_precision'] >= 0.8:
                print(f"   ✅  Recall@{r['k']} = {r['avg_recall']:.2%}, Precision@{r['k']} = {r['avg_precision']:.2%}")
                print(f"      检索效果良好")

    if current_top_k:
        print(f"\n 🔧 当前配置: RETRIEVER_TOP_K = {current_top_k}")
    else:
        print(f"\n 🔧 提示: 可在 config.py 中调整 RETRIEVER_TOP_K 等参数")


def print_individual_results(kb_id, results, k_values, test_cases):
    """打印每个查询的详细结果（针对默认第一个 k 值）"""
    print(f"\n{'='*70}")
    print(f" 📝 各查询详细结果 (k={k_values[0]})")
    print(f"{'='*70}")

    # 重新检索一次并打印详情
    from services.app_services import get_vector_service
    vector_service = get_vector_service()
    retriever = vector_service.get_retriever(kb_id)

    kb_cases = test_cases.get(kb_id, {})
    for question, relevant_ids in kb_cases.items():
        retrieved_docs = retriever.invoke(question)
        detailed_query_report(retrieved_docs, relevant_ids, question, k_values[0])


def main():
    parser = argparse.ArgumentParser(
        description='RAG检索召回率评估工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python evaluate_retrieval.py --kb-id 1              # 评估知识库1
  python evaluate_retrieval.py --kb-id 1 --k 5 10 20  # 自定义k值
  python evaluate_retrieval.py --all                   # 评估所有知识库
  python evaluate_retrieval.py --list-docs             # 查看文档列表
  python evaluate_retrieval.py --kb-id 1 --verbose     # 打印详细结果
        """
    )
    parser.add_argument('--kb-id', type=int, help='知识库ID', default=2)
    parser.add_argument('--all', action='store_true', help='评估所有知识库')
    parser.add_argument('--k', type=int, nargs='+', default=[5, 10, 20],
                        help='评估的k值列表，默认 5 10 20')
    parser.add_argument('--list-docs', action='store_true', help='列出所有文档信息')
    parser.add_argument('--test-file', type=str, help='外部测试集JSON文件路径')
    parser.add_argument('--verbose', action='store_true', help='输出每个查询的详细结果')
    args = parser.parse_args()

    # 仅列出文档
    if args.list_docs:
        list_documents()
        return

    # 验证参数
    if not args.kb_id and not args.all:
        print("请指定 --kb-id <ID> 或 --all")
        parser.print_help()
        sys.exit(1)

    # 创建 Flask 应用上下文
    app = create_app_context()

    # 加载测试用例
    test_cases = load_test_cases(args)
    print(f"已加载测试用例: {sum(len(v) for v in test_cases.values())} 个查询 "
          f"({len(test_cases)} 个知识库)")

    # 确定要评估的知识库ID列表
    kb_ids = []
    if args.all:
        kbs = KnowledgeBase.query.filter_by(status=1).all()
        kb_ids = [kb.id for kb in kbs]
        if not kb_ids:
            print("没有找到可用的知识库")
            return
    else:
        kb_ids = [args.kb_id]

    # 初始化向量服务
    print("\n正在初始化向量服务...")
    vector_service = get_vector_service()

    # 对每个知识库进行评估
    for kb_id in kb_ids:
        results = evaluate_kb(kb_id, args.k, vector_service, test_cases)
        if results is None:
            continue

        # 打印报告
        print_evaluation_report(kb_id, results, args.k, test_cases)

        if args.verbose:
            print_individual_results(kb_id, results, args.k, test_cases)

    print(f"\n{'='*70}")
    print(" ✅ 评估完成！")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()

import os
from pathlib import Path
import docx
import PyPDF2
from sentence_transformers import SentenceTransformer
from pymilvus import MilvusClient

# ========== 配置 ==========
MILVUS_URI = "http://localhost:19530"
COLLECTION_NAME = "test_qa_docs"
EMBEDDING_DIM = 512
UPLOAD_DIR = Path(r"F:\pythonpro\EnterpriseQA\server\uploads")
MODEL_PATH = r"F:\pythonpro\EnterpriseQA\server\bge-small-zh-v1.5"


# ========== 文本提取 ==========

def read_text_file(file_path, file_type):
    text = ''
    if file_type in ('txt', 'md'):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    elif file_type == 'pdf':
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + '\n'
    elif file_type == 'docx':
        from docx import Document as DocxDocument
        doc = DocxDocument(file_path)
        for para in doc.paragraphs:
            if para.text.strip():
                text += para.text + '\n'

    return text


def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    return read_text_file(file_path, suffix)


# ========== Milvus 操作 ==========
def init_milvus():
    client = MilvusClient(uri=MILVUS_URI)
    print(f"✅ 已连接到 Milvus ({MILVUS_URI})")
    return client


def setup_collection(client: MilvusClient):
    if client.has_collection(COLLECTION_NAME):
        print(f"ℹ️ 集合 '{COLLECTION_NAME}' 已存在，将直接使用")
        return
    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="IVF_FLAT",
        metric_type="IP",
        params={"nlist": 128},
    )
    client.create_collection(
        collection_name=COLLECTION_NAME,
        dimension=EMBEDDING_DIM,
        metric_type="IP",
        auto_id=True,
        enable_dynamic_field=True,
        index_params=index_params,
    )
    print(f"✅ 集合 '{COLLECTION_NAME}' 创建成功（已附带 IVF_FLAT 索引）")


def create_index_and_load(client: MilvusClient):
    """创建索引并加载集合。每个字段只能有一个索引；create_collection 可能已建默认索引。"""
    existing_indexes = client.list_indexes(COLLECTION_NAME)
    if existing_indexes:
        print(f"ℹ️ 向量字段已有索引 {existing_indexes}，跳过 create_index")
    else:
        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="IVF_FLAT",
            metric_type="IP",
            params={"nlist": 128},
        )
        client.create_index(COLLECTION_NAME, index_params=index_params)
        print("✅ 索引创建完成")

    client.load_collection(COLLECTION_NAME)
    print("✅ 集合已加载")


def insert_documents(client: MilvusClient, model: SentenceTransformer):
    if not UPLOAD_DIR.exists():
        raise FileNotFoundError(f"目录不存在: {UPLOAD_DIR}")

    files = [f for f in UPLOAD_DIR.iterdir() if f.suffix.lower() in [".txt", ".docx", ".pdf"]]
    if not files:
        print("⚠️ 未找到任何文件，跳过插入")
        return

    data_to_insert = []
    for file_path in files:
        try:
            text = extract_text(file_path)
            if not text or not text.strip():
                print(f"⚠️ 文件内容为空，跳过: {file_path.name}")
                continue
            vec = model.encode(text, normalize_embeddings=True).tolist()
            data_to_insert.append({"vector": vec, "text": text})
            print(f"✔ 已处理文件: {file_path.name}")
        except Exception as e:
            print(f"✖ 处理文件失败 {file_path.name}: {e}")

    if not data_to_insert:
        print("⚠️ 没有有效文本可以插入")
        return

    insert_result = client.insert(COLLECTION_NAME, data_to_insert)
    print(f"✅ 成功插入 {len(data_to_insert)} 条文档，计数: {insert_result['insert_count']}")


def search_test(client: MilvusClient, model: SentenceTransformer, query_text="测试查询"):
    stats = client.get_collection_stats(COLLECTION_NAME)
    if stats["row_count"] == 0:
        print("⚠️ 集合为空，跳过检索测试")
        return

    query_with_prefix = f"为这个句子生成表示以用于检索相关文章：{query_text}"
    query_vec = model.encode([query_with_prefix], normalize_embeddings=True).tolist()

    results = client.search(
        collection_name=COLLECTION_NAME,
        data=query_vec,
        limit=3,
        output_fields=["text"],
        search_params={"metric_type": "IP", "params": {"nprobe": 10}},
        anns_field="vector"
    )
    print(f"\n🔍 查询: '{query_text}'")
    for i, hits in enumerate(results):
        for j, hit in enumerate(hits):
            print(f"  排名 {j + 1}: ID={hit['id']}, 距离={hit['distance']:.4f}")
            print(f"  文本片段: {hit['entity']['text'][:100]}...")


# ========== 主流程 ==========
def main():
    client = init_milvus()
    setup_collection(client)

    print(f"⏳ 正在加载模型 {MODEL_PATH} ...")
    model = SentenceTransformer(MODEL_PATH)
    print("✅ 模型加载完成")

    insert_documents(client, model)
    client.flush(COLLECTION_NAME)
    create_index_and_load(client)
    search_test(client, model, query_text="数据库错误代码？")

    client.close()
    print("✅ 测试完成")


if __name__ == "__main__":
    main()

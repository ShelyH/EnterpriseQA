# RAG 检索召回率评估工具

## 快速开始

### 1️⃣ 查看文档列表（辅助构建测试用例）

```bash
cd server
python evaluate_retrieval.py --list-docs
```

输出示例：
```
ID    知识库ID   知识库名称             文件名称                                     
12    1          人事制度               公司考勤管理制度.txt
13    1          人事制度               公司薪酬福利制度.pdf
14    1          人事制度               员工请假管理办法.md
...
```

### 2️⃣ 评估指定知识库

```bash
# 评估知识库1（人事制度）
python evaluate_retrieval.py --kb-id 1

# 自定义 k 值
python evaluate_retrieval.py --kb-id 1 --k 3 5 10

# 输出每个查询的详细结果
python evaluate_retrieval.py --kb-id 1 --verbose
```

### 3️⃣ 评估所有知识库

```bash
python evaluate_retrieval.py --all
```

### 4️⃣ 使用外部测试集文件

```bash
python evaluate_retrieval.py --kb-id 1 --test-file my_tests.json
```

## 测试集文件格式

```json
{
    "1": {
        "公司考勤制度中迟到如何定义？": [12],
        "薪酬福利包括哪些内容？": [13],
        "请假审批流程是什么？": [14]
    },
    "2": {
        "API接口设计有什么规范？": [16],
        "Git分支管理策略是怎样的？": [17]
    }
}
```

## 评估指标说明

| 指标 | 公式 | 说明 |
|------|------|------|
| **Recall@k** | 检索到的相关文档数 / 总相关文档数 | 越高越好，衡量"有没有漏掉" |
| **Precision@k** | 检索到的相关文档数 / k | 越高越好，衡量"检索结果是否精准" |
| **HitRate@k** | 是否至少命中1个相关文档 | 衡量"能否回答" |

## 结果解读

```
k       Recall@k       Precision@k     HitRate@k       Recall(min)
5       0.6667         0.2000          0.8571          0.0000
10      0.8333         0.1167          1.0000          0.5000      ← 当前配置
20      0.9167         0.0643          1.0000          0.5000
```

- **Recall@10 = 83.33%**：平均能检索到 83% 的相关文档
- **HitRate@10 = 100%**：所有问题至少能命中 1 个相关文档
- 如果 Recall 偏低 → 增大 `RETRIEVER_TOP_K` 或优化分块
- 如果 Precision 偏低 → 减小 `RETRIEVER_TOP_K` 或更换检索策略

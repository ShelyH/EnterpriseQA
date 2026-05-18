from pymilvus import MilvusClient
import numpy as np

client = MilvusClient("./milvus_demo.db")
if not client.has_collection(collection_name="test"):
    client.create_collection(collection_name="test",
                             dimension=384
                             )
client.load_collection("test")
docs = [
    "Artificial intelligence was founded as an academic discipline in 1956.",
    "Alan Turing was the first person to conduct substantial research in AI.",
    "Born in Maida Vale, London, Turing was raised in southern England.",
]

vectors = [[np.random.uniform(-1, 1) for i in range(384)] for _ in range(len(docs))]

data = [{"id": i, "vector": vectors[i], "text": docs[i], "subject": "history"} for i in range(len(vectors))]

res = client.insert(collection_name="test", data=data)

res = client.search(collection_name="test", data=[vectors[0]], filter="subject=='history'", limit=2, output_fields=["text", "subject"])
print(res)

res=client.query(collection_name="test",filter="subject=='history'",output_fields=["text", "subject"])
print(res)
from pymilvus import connections, Collection
import ollama
from motor.motor_asyncio import AsyncIOMotorCollection


connections.connect(host="localhost", port=19530)
milvus_collection = Collection(name="rag_books")
milvus_collection.load()


async def retrieve(query: str, top_k: int, dbcollection: AsyncIOMotorCollection):
    clean_query = query.encode('utf-8', 'ignore').decode('utf-8')
    response = ollama.embeddings(model="nomic-embed-text", prompt=clean_query)
    query_embedding = response["embedding"]

    results = milvus_collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=top_k,
        output_fields=["chunk_id"]
    )
    chunks = []
    for hit in results[0]:
        chunk_id = hit.entity.get("chunk_id")
        doc = await dbcollection.find_one({"chunk_id": chunk_id})
        if doc:
            chunks.append({
                "chunk_id": chunk_id,
                "text":     doc["text"],
                "source":   doc["source"],
                "page":     doc["page"],
                "score":    hit.score
            })
    print("Milvus results:", results)
    print("Chunks found:", len(chunks))

    return chunks



    
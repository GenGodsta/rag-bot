from pymilvus import MilvusClient
import ollama
from motor.motor_asyncio import AsyncIOMotorCollection
from sentence_transformers import CrossEncoder
from rank_bm25 import BM25Okapi

milvus_client = MilvusClient(uri="http://localhost:19530")
milvus_client.load_collection("rag_books")
print("Collection loaded")

reranker = CrossEncoder("C:/Users/nipun/OneDrive/Desktop/rag-bot/crossencodermodel")

bm25_index = None
bm25_corpus = []

async def build_bm25_index(dbcollection: AsyncIOMotorCollection):
    global bm25_index, bm25_corpus
    cursor = dbcollection.find({}, {"chunk_id": 1, "text": 1, "source": 1, "page": 1})
    async for doc in cursor:
        bm25_corpus.append({
            "chunk_id": doc["chunk_id"],
            "text":     doc["text"],
            "source":   doc["source"],
            "page":     doc["page"],
        })
    tokenized = [doc["text"].lower().split() for doc in bm25_corpus]
    bm25_index = BM25Okapi(tokenized)

async def retrieve(query: str, top_k: int, dbcollection: AsyncIOMotorCollection):
    clean_query = query.encode('utf-8', 'ignore').decode('utf-8')

    response = ollama.embeddings(model="nomic-embed-text", prompt=clean_query)
    query_embedding = response["embedding"]

    results = milvus_client.search(
        collection_name="rag_books",
        data=[query_embedding],
        anns_field="embedding",
        search_params={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=15,
        output_fields=["chunk_id"]
    )

    dense_chunks = []
    for hit in results[0]:
        chunk_id = hit["entity"]["chunk_id"]
        doc = await dbcollection.find_one({"chunk_id": chunk_id})
        if doc:
            dense_chunks.append({
                "chunk_id": chunk_id,
                "text":     doc["text"],
                "source":   doc["source"],
                "page":     doc["page"],
            })

    tokenized_query = clean_query.lower().split()
    bm25_scores = bm25_index.get_scores(tokenized_query)
    top_bm25_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:5]
    bm25_chunks = [bm25_corpus[i] for i in top_bm25_indices]

    rrf_scores = {}
    chunk_map  = {}

    for rank, chunk in enumerate(dense_chunks):
        cid = chunk["chunk_id"]
        rrf_scores[cid] = rrf_scores.get(cid, 0) + 1 / (rank + 60)
        chunk_map[cid]  = chunk

    for rank, chunk in enumerate(bm25_chunks):
        cid = chunk["chunk_id"]
        rrf_scores[cid] = rrf_scores.get(cid, 0) + 1 / (rank + 120)
        chunk_map[cid]  = chunk

    merged = sorted(chunk_map.values(), key=lambda c: rrf_scores[c["chunk_id"]], reverse=True)

    pairs = [(query, c["text"]) for c in merged]
    scores = reranker.predict(pairs)
    for i, score in enumerate(scores):
        merged[i]["score"] = float(score)
    ranked = sorted(merged, key=lambda x: x["score"], reverse=True)

    print(f"Dense: {len(dense_chunks)} | BM25: {len(bm25_chunks)} | Merged: {len(merged)} | Top score: {ranked[0]['score']:.2f}")

    return ranked[:top_k]
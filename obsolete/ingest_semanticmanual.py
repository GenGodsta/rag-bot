from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from pymongo import MongoClient
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import ollama
from pathlib import Path
import sys
from nltk import sent_tokenize
import numpy as np

connections.connect(host="localhost", port=19530)

if not utility.has_collection("rag_books"):
    fields = [
        FieldSchema(name="id",        dtype=DataType.INT64,         is_primary=True, auto_id=True),
        FieldSchema(name="chunk_id",  dtype=DataType.VARCHAR,       max_length=100),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR,  dim=768),
    ]
    schema = CollectionSchema(fields=fields, description="RAG book chunks")
    collection = Collection(name="rag_books", schema=schema)
    collection.create_index(
        field_name="embedding",
        index_params={"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
    )
    print(f"Collection 'rag_books' created.")
else:
    collection = Collection(name="rag_books")
    print(f"Collection 'rag_books' already exists.")


def cosine(i, j):
    return np.dot(i, j) / (np.linalg.norm(i) * np.linalg.norm(j))


mongoclient = MongoClient("mongodb://localhost:27017")
db = mongoclient["ragdb"]
mongo_col = db["rag_books"]


splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=100,
)


data_dir = Path(__file__).parent/ "data"
pdf_files = list(data_dir.glob("*.pdf"))

if not pdf_files:
    print("No PDFs found in data/ folder!")
    sys.exit(1)

print(f"\nFound {len(pdf_files)} PDFs: {[f.name for f in pdf_files]}\n")

for pdf_path in pdf_files:
    try:
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
    except Exception as e:
        print(f"Skipping {pdf_path.name}: {e}")
        continue

    split_chunks = []
    for page in pages:
        page_num = page.metadata.get("page", 0)
        sentences = sent_tokenize(page.page_content)

        if not sentences:
            continue

        sentence_embeddings = [ollama.embeddings(model="nomic-embed-text", prompt=s)["embedding"] for s in sentences]

        chunks = []
        current_chunk = [sentences[0]]

        for i in range(len(sentence_embeddings) - 1):
            sim = cosine(sentence_embeddings[i], sentence_embeddings[i+1])
            if sim >= 0.75:
                current_chunk.append(sentences[i+1])
            else:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentences[i+1]]
        chunks.append(" ".join(current_chunk))

        for chunk in chunks:
            for split in splitter.split_text(chunk):
                split_chunks.append((split, page_num))

    print(f"{len(split_chunks)} chunks created")

    embeddings = []
    chunk_ids  = []
    mongo_docs = []

    for i, (clean_text, page_num) in enumerate(split_chunks):
        chunk_id = f"{pdf_path.stem}_{i}"
        clean_text = clean_text.encode('utf-8', 'ignore').decode('utf-8')
        response = ollama.embeddings(model="nomic-embed-text", prompt=clean_text)
        embedding = response["embedding"]

        embeddings.append(embedding)
        chunk_ids.append(chunk_id)
        mongo_docs.append({
            "chunk_id": chunk_id,
            "text":     clean_text,
            "source":   pdf_path.name,
            "page":     page_num,
        })

        if (i + 1) % 100 == 0:
            print(f"Embedded {i+1}/{len(split_chunks)} chunks...")

    collection.insert([chunk_ids, embeddings])
    collection.flush()
    mongo_col.insert_many(mongo_docs)

    print(f"Done: {pdf_path.name}\n")

print("Books ingested successfully")
print(f"Chunks in Database: {mongo_col.count_documents({})}")
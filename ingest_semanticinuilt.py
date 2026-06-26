from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from pymongo import MongoClient
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.embeddings import OllamaEmbeddings
from pathlib import Path
import sys

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

mongoclient = MongoClient("mongodb://localhost:27017")
db = mongoclient["ragdb"]
mongo_col = db["rag_books"]

embedder = OllamaEmbeddings(model="nomic-embed-text")

semantic_splitter = SemanticChunker(
    embedder,
    breakpoint_threshold_type="percentile",
    breakpoint_threshold_amount=75
)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=100,
)

data_dir = Path(__file__).parent / "data"
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
    
    print(f"Starting processing of book {pdf_path.name}")
    split_chunks = []
    for page in pages:

        page_num = page.metadata.get("page", 0)

        if not page.page_content.strip():
            continue

        
        print(f"Processing page {page_num}...")

        semantic_chunks = semantic_splitter.split_text(page.page_content)

        for chunk in semantic_chunks:
            for split in splitter.split_text(chunk):
                split_chunks.append((split, page_num))

    print(f"{len(split_chunks)} chunks created")

    embeddings = []
    chunk_ids  = []
    mongo_docs = []

    for i, (clean_text, page_num) in enumerate(split_chunks):
        chunk_id = f"{pdf_path.stem}_{i}"
        clean_text = clean_text.encode('utf-8', 'ignore').decode('utf-8')
        embedding = embedder.embed_query(clean_text)

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
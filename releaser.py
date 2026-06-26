from pymilvus import connections, Collection

connections.connect(host="localhost", port=19530)
col = Collection(name="rag_books")

col.release()
print("Released")

col.load()
print("Loaded")
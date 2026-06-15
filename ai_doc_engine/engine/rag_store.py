import chromadb

class DocVectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(name="repo_docs")

    def upsert_doc(self, doc_id, text, metadata):
        """Insert or update a documentation chunk."""
        self.collection.upsert(
            documents=[text],
            metadatas=[metadata],
            ids=[doc_id]
        )

    def search(self, query, n_results=3):
        """Retrieve relevant documentation chunks for chat."""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results['documents'][0] if results['documents'] else []
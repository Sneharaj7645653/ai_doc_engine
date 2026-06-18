import os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

class DocVectorStore:
    def __init__(self):
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = "doc-engine-cloud" # Changed name to force a fresh index
        
        # Automatically provision the index on AWS with Pinecone's inference dimensions (1024)
        if self.index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=self.index_name,
                dimension=1024, 
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
            )
        
        self.index = self.pc.Index(self.index_name)

    def get_doc(self, doc_id):
        """Fetches existing markdown documentation from Pinecone Cloud."""
        try:
            response = self.index.fetch(ids=[doc_id])
            if response and 'vectors' in response and doc_id in response['vectors']:
                return response['vectors'][doc_id]['metadata']['text']
        except Exception as e:
            print(f"Error fetching from Pinecone: {e}", flush=True)
        return None

    def upsert_doc(self, doc_id, text=None, document=None, **kwargs):
        """Converts text to an embedding vector and saves it to the cloud."""
        # Bulletproof grab of the text, regardless of what the UI called the variable
        content = text or document
        if not content and kwargs:
            content = list(kwargs.values())[0]

        # 1. Use Pinecone's free serverless inference to generate the embedding
        embed_data = self.pc.inference.embed(
            model="multilingual-e5-large",
            inputs=[content],
            parameters={"input_type": "passage", "truncate": "END"}
        )
        vector = embed_data[0].values
        
        # 2. Save the embedding and the text to the cloud database
        self.index.upsert(
            vectors=[{
                "id": doc_id, 
                "values": vector, 
                "metadata": {"text": content}
            }]
        )
    def search(self, query, top_k=3):
        """Embeds the user chat query and searches Pinecone for relevant docs."""
        try:
            # 1. Translate the user's question into a vector using the same model
            embed_data = self.pc.inference.embed(
                model="multilingual-e5-large",
                inputs=[query],
                parameters={"input_type": "query"} 
            )
            query_vector = embed_data[0].values

            # 2. Search the cloud index for the top 3 closest matches
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True
            )

            # 3. Extract the actual Markdown text to send back to the LLM
            chunks = []
            if results and 'matches' in results:
                for match in results['matches']:
                    if 'metadata' in match and 'text' in match['metadata']:
                        chunks.append(match['metadata']['text'])
            return chunks
            
        except Exception as e:
            print(f"Error during Pinecone search: {e}", flush=True)
            return []
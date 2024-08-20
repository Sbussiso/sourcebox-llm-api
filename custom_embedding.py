class CustomEmbeddingFunction:
    def __init__(self, client):
        self.client = client

    def embed_documents(self, documents):
        document_texts = [str(doc) for doc in documents]
        response = self.client.embeddings.create(
            input=document_texts,
            model="text-embedding-3-small"
        )
        return [item.embedding for item in response.data]

    def embed_query(self, query):
        query_text = str(query)
        response = self.client.embeddings.create(
            input=[query_text],
            model="text-embedding-3-small"
        )
        return response.data[0].embedding

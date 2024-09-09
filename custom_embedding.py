import logging

# Configure logging (if not already configured elsewhere in your application)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

class CustomEmbeddingFunction:
    def __init__(self, client):
        self.client = client
        self.logger = logging.getLogger(__name__)
        self.logger.info("CustomEmbeddingFunction initialized with client: %s", client)

    def embed_documents(self, documents):
        self.logger.info("Embedding documents. Number of documents: %d", len(documents))
        
        document_texts = [str(doc) for doc in documents]
        self.logger.debug("Document texts: %s", document_texts)
        
        try:
            response = self.client.embeddings.create(
                input=document_texts,
                model="text-embedding-3-small"
            )
            self.logger.debug("Received response for document embeddings: %s", response)
        except Exception as e:
            self.logger.error("Error creating embeddings for documents: %s", str(e))
            raise

        embeddings = [item.embedding for item in response.data]
        self.logger.info("Successfully created embeddings for documents. Number of embeddings: %d", len(embeddings))
        
        return embeddings

    def embed_query(self, query):
        self.logger.info("Embedding query: %s", query)
        
        query_text = str(query)
        self.logger.debug("Query text: %s", query_text)
        
        try:
            response = self.client.embeddings.create(
                input=[query_text],
                model="text-embedding-3-small"
            )
            self.logger.debug("Received response for query embedding: %s", response)
        except Exception as e:
            self.logger.error("Error creating embedding for query: %s", str(e))
            raise

        embedding = response.data[0].embedding
        self.logger.info("Successfully created embedding for query.")
        
        return embedding

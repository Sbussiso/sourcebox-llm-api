import logging
import time

# Configure logging (if not already configured elsewhere in your application)
logging.basicConfig(
    level=logging.ERROR,  # Only log errors
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

class CustomEmbeddingFunction:
    def __init__(self, client, max_retries=3, retry_delay=5):
        self.client = client
        self.max_retries = max_retries  # Maximum number of retries
        self.retry_delay = retry_delay  # Delay in seconds between retries
        self.logger = logging.getLogger(__name__)

    def embed_documents(self, documents):
        document_texts = [str(doc) for doc in documents]
        retries = 0

        while retries < self.max_retries:
            try:
                response = self.client.embeddings.create(
                    input=document_texts,
                    model="text-embedding-3-small"
                )
                embeddings = [item.embedding for item in response.data]
                return embeddings  # Return embeddings if successful
            except Exception as e:
                if "rate limit" in str(e).lower():
                    self.logger.error("Rate limit error: %s. Retrying in %d seconds...", str(e), self.retry_delay)
                    retries += 1
                    time.sleep(self.retry_delay)  # Wait before retrying
                else:
                    self.logger.error("Error creating embeddings for documents: %s", str(e))
                    raise  # Reraise other errors that are not rate limit related

        self.logger.error("Max retries reached. Failed to create embeddings for documents.")
        raise Exception("Rate limit exceeded, max retries reached")

    def embed_query(self, query):
        query_text = str(query)
        retries = 0

        while retries < self.max_retries:
            try:
                response = self.client.embeddings.create(
                    input=[query_text],
                    model="text-embedding-3-small"
                )
                embedding = response.data[0].embedding
                return embedding  # Return embedding if successful
            except Exception as e:
                if "rate limit" in str(e).lower():
                    self.logger.error("Rate limit error: %s. Retrying in %d seconds...", str(e), self.retry_delay)
                    retries += 1
                    time.sleep(self.retry_delay)  # Wait before retrying
                else:
                    self.logger.error("Error creating embedding for query: %s", str(e))
                    raise  # Reraise other errors that are not rate limit related

        self.logger.error("Max retries reached. Failed to create embedding for query.")
        raise Exception("Rate limit exceeded, max retries reached")
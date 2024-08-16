from langchain_community.vectorstores import DeepLake
from custom_embedding import CustomEmbeddingFunction
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()
# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# Initialize the embedding function
embedding_function = CustomEmbeddingFunction(client)
db = DeepLake(dataset_path="./my_deeplake/", embedding=embedding_function, read_only=True)


def perform_query(query):
    try:
        docs = db.similarity_search(query)
        output = {}
        for i, doc in enumerate(docs):
            output[f"Document {i + 1}"] = doc.page_content
        return output

    except Exception as e:
        print(f"Error during similarity search: {e}")


if __name__ == "__main__":
    query = "where is the database being used"
    response = perform_query(query)
    for key, value in response.items():
        print(f"{key}: {value}")
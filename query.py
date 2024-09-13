from langchain_community.vectorstores import DeepLake
from custom_embedding import CustomEmbeddingFunction
from openai import OpenAI
import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Minimum level of severity to capture
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log message format
    handlers=[
        logging.FileHandler('app.log'),  # Log to a file
        logging.StreamHandler()  # Also log to the console
    ]
)

# Load environment variables
load_dotenv()

def perform_query(db_instance, query):
    logging.info(f"Initiating query with text: {query}")
    try:
        # Validate query
        if not isinstance(query, str) or not query.strip():
            logging.error(f"Invalid query provided: {query}")
            raise ValueError("Query must be a non-empty string.")

        logging.info("Checking if db_instance is initialized properly...")
        if db_instance is None:
            logging.error("The db_instance is None. Aborting query.")
            return {}

        # Start performing the similarity search
        logging.info(f"Executing similarity search with query: '{query}'")
        docs = db_instance.similarity_search(query)
        
        # Check how many documents were found
        logging.info(f"Search complete. {len(docs)} documents were found matching the query.")

        if len(docs) == 0:
            logging.warning("No documents returned for the query. Returning an empty result.")
            return {}

        output = {}
        logging.info(f"Processing each document retrieved from the search...")
        
        # Log detailed information for each document
        for i, doc in enumerate(docs):
            if doc is None:
                logging.warning(f"Document {i + 1} is None. Skipping this document.")
                continue

            # Ensure the document has page_content and it is a string
            if not hasattr(doc, 'page_content') or not isinstance(doc.page_content, str):
                logging.warning(f"Document {i + 1} does not have valid page_content or it's not a string. Skipping.")
                continue

            # Log metadata if it exists, otherwise log that metadata is missing
            if hasattr(doc, 'metadata') and doc.metadata:
                logging.info(f"Document {i + 1} metadata: {doc.metadata}")
            else:
                logging.info(f"Document {i + 1} has no metadata.")

            # Log a snippet of the document for clarity
            logging.info(f"Document {i + 1} content snippet: {doc.page_content[:100]}...")

            output[f"Document {i + 1}"] = doc.page_content
        
        logging.info(f"Finished processing all {len(docs)} documents. Returning results.")
        return output

    except ValueError as ve:
        logging.error(f"ValueError occurred: {ve}")
        return {}
    except Exception as e:
        logging.error(f"An error occurred during the similarity search: {e}", exc_info=True)
        return {}




if __name__ == "__main__":
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Initialize the embedding function
    embedding_function = CustomEmbeddingFunction(client)

    # Define user_id and pack_id dynamically
    user_id = "example_user_id"  # Replace with the actual user_id
    pack_id = "example_pack_id"  # Replace with the actual pack_id

    # Construct the DeepLake dataset path based on user_id and pack_id
    dataset_path = os.path.join("my_deeplake", user_id, pack_id, "actual_deeplake_name")

    # Initialize DeepLake instance
    logging.info(f"Loading DeepLake from path: {dataset_path}")
    db = DeepLake(dataset_path=dataset_path, embedding=embedding_function, read_only=True)
    
    # Define the query
    query = "where is the database being used"

    # Perform the query and process the response
    response = perform_query(db, query)
    for key, value in response.items():
        print(f"{key}: {value}")

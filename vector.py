import os
from dotenv import load_dotenv
from openai import OpenAI
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import DeepLake
from custom_embedding import CustomEmbeddingFunction
import logging
import hashlib

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize the embedding function
embedding_function = CustomEmbeddingFunction(client)

def project_to_vector(user_folder_path, access_token):
    """Process files in the user folder and create a user-specific DeepLake dataset."""
    
    # Create a unique user dataset path using a hashed token
    hashed_token = hashlib.sha256(access_token.encode()).hexdigest()  # Ensures uniqueness for each user
    dataset_path = os.path.join("my_deeplake", hashed_token)
    
    # Ensure the dataset folder exists
    os.makedirs(dataset_path, exist_ok=True)

    logging.info(f"Processing files for embedding from folder: {user_folder_path}")
    
    # Initialize DeepLake instance for the specific user
    db = DeepLake(dataset_path=dataset_path, embedding=embedding_function, overwrite=True)
    
    # Define allowed file extensions
    allowed_extensions = {
        ".py", ".txt", ".csv", ".json", ".md", ".html", ".xml", ".yaml", ".yml", ".pdf",
        ".js", ".docx", ".xlsx", "Dockerfile", "Procfile", ".gitignore",
        ".java", ".rb", ".go", ".sh", ".php", ".cs", ".cpp", ".c", ".ts", ".swift", ".kt", ".rs", ".r", ".scala", ".pl", ".sql"
    }

    failed_files = []

    for root, dirs, files in os.walk(user_folder_path):
        for filename in files:
            file_path = os.path.join(root, filename)
            file_extension = os.path.splitext(filename)[1]
            
            if file_extension not in allowed_extensions:
                logging.warning(f"Skipping unsupported file: {filename}")
                continue

            if os.path.isfile(file_path):
                try:
                    loader = TextLoader(file_path)
                    documents = loader.load()

                    # Split the document respecting OpenAI's token limits
                    max_chunk_size = 8192 - 100  # Keep chunks within token limit with some buffer
                    text_splitter = CharacterTextSplitter(chunk_size=max_chunk_size, chunk_overlap=100)
                    docs = text_splitter.split_documents(documents)
                    logging.info(f"Successfully split document: {filename} into {len(docs)} chunks.")
                except Exception as e:
                    failed_files.append(file_path)
                    logging.error(f"Failed to load or split file: {filename}, Error: {e}")
                    continue

                try:
                    db.add_documents(docs)  # Add documents to the user's specific DeepLake dataset
                    logging.info(f"Successfully added documents from file: {filename}")
                except Exception as e:
                    failed_files.append(file_path)
                    logging.error(f"Failed to add documents from file: {filename}, Error: {e}")

    if failed_files:
        logging.error(f"The following files failed to process: {failed_files}")
    else:
        logging.info("All files processed successfully.")

    return db





if __name__ == "__main__":
    project_to_vector('uploads/12b593a49c6be1fe2638968d5a022c19fab46bfc7d85f5b990d99a88856d8775')

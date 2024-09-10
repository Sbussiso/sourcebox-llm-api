import os
from dotenv import load_dotenv
from openai import OpenAI
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import DeepLake
from custom_embedding import CustomEmbeddingFunction
import logging
import hashlib
import shutil

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize the embedding function
embedding_function = CustomEmbeddingFunction(client)

def project_to_vector(user_folder_path, access_token):
    """Process files in the user folder, clear existing dataset, and create a user-specific DeepLake dataset."""

    logging.info(f"Starting vectorization for user folder: {user_folder_path}")
    logging.info(f"Access token (hashed): {hashlib.sha256(access_token.encode()).hexdigest()}")

    try:
        # Create a unique user dataset path using a hashed token
        hashed_token = hashlib.sha256(access_token.encode()).hexdigest()  # Ensures uniqueness for each user
        dataset_path = os.path.join("my_deeplake", hashed_token)
        logging.info(f"Dataset path: {dataset_path}")

        # Ensure the dataset folder exists
        os.makedirs(dataset_path, exist_ok=True)
        logging.info(f"Directory {dataset_path} created/exists.")
        
        # Initialize DeepLake instance for the specific user and remove existing data
        logging.info(f"Checking if the dataset needs to be cleared for user: {hashed_token}")
        
        if os.path.exists(dataset_path):
            logging.info(f"Flushing existing dataset at {dataset_path}...")
            try:
                shutil.rmtree(dataset_path)  # Remove the folder and all its contents
                os.makedirs(dataset_path, exist_ok=True)  # Recreate an empty dataset directory
                logging.info(f"Successfully cleared and recreated dataset folder at {dataset_path}.")
            except Exception as e:
                logging.error(f"Failed to clear the dataset folder {dataset_path}: {e}")
                raise Exception(f"Could not clear dataset folder: {e}")
        
        # Initialize DeepLake instance after clearing
        db = DeepLake(dataset_path=dataset_path, embedding=embedding_function, overwrite=True)
        logging.info(f"DeepLake instance initialized for path: {dataset_path}")
        
        # Define allowed file extensions
        allowed_extensions = {
            ".py", ".txt", ".csv", ".json", ".md", ".html", ".xml", ".yaml", ".yml", ".pdf",
            ".js", ".docx", ".xlsx", "Dockerfile", "Procfile", ".gitignore",
            ".java", ".rb", ".go", ".sh", ".php", ".cs", ".cpp", ".c", ".ts", ".swift", ".kt", ".rs", ".r", ".scala", ".pl", ".sql"
        }

        failed_files = []

        # Traverse the user folder and process files
        for root, dirs, files in os.walk(user_folder_path):
            logging.info(f"Processing folder: {root}, found {len(files)} files.")
            
            for filename in files:
                file_path = os.path.join(root, filename)
                file_extension = os.path.splitext(filename)[1]
                logging.info(f"Processing file: {filename}, Extension: {file_extension}")

                if file_extension not in allowed_extensions:
                    logging.warning(f"Skipping unsupported file: {filename}")
                    continue

                if os.path.isfile(file_path):
                    try:
                        loader = TextLoader(file_path)
                        documents = loader.load()

                        # Split the document respecting OpenAI's token limits
                        max_chunk_size = 2000  # Keep chunks within token limit with some buffer
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

    except Exception as e:
        logging.error(f"Error in vectorization process: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    # Example test run
    user_folder_path = 'uploads/12b593a49c6be1fe2638968d5a022c19fab46bfc7d85f5b990d99a88856d8775'
    access_token = "example_access_token"  # Replace with actual access token for testing
    project_to_vector(user_folder_path, access_token)

import os
import shutil
from dotenv import load_dotenv
from openai import OpenAI
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import DeepLake
from custom_embedding import CustomEmbeddingFunction
import logging

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize the embedding function
embedding_function = CustomEmbeddingFunction(client)


def project_to_vector(user_folder_path, user_id, pack_id, pack_type):
    """Process files in the user folder, ensure proper cleanup, and create a user-specific DeepLake dataset."""

    logging.info(f"Starting vectorization for user folder: {user_folder_path}")
    logging.info(f"User ID: {user_id}, Pack ID: {pack_id}, Pack Type: {pack_type}")

    try:
        # Create a unique dataset path using user_id, pack_id, and pack_type
        dataset_path = os.path.join("my_deeplake", user_id, pack_type, pack_id, "actual_deeplake_name")
        logging.info(f"Dataset path: {dataset_path}")

        # Ensure the dataset folder exists and clear it before use
        if os.path.exists(dataset_path):
            logging.info(f"Existing dataset found at {dataset_path}. Attempting to delete it...")
            try:
                # Initialize the dataset and attempt to delete
                db = DeepLake(dataset_path=dataset_path, embedding=embedding_function)
                db.delete_dataset()  # Try to delete using DeepLake's delete_dataset method
                logging.info(f"Successfully deleted dataset at {dataset_path}.")
            except Exception as e:
                logging.error(f"Failed to delete dataset using delete_dataset(). Attempting force delete... Error: {e}")
                try:
                    # Force delete in case the regular deletion fails
                    DeepLake.force_delete_by_path(dataset_path)
                    logging.info(f"Successfully force-deleted dataset at {dataset_path}.")
                except Exception as force_error:
                    logging.error(f"Failed to force delete dataset at {dataset_path}. Error: {force_error}")
                    raise Exception(f"Could not delete dataset folder: {force_error}")
        else:
            logging.info(f"No existing dataset found for {dataset_path}. Creating new dataset folder...")

        # Recreate the empty dataset directory after clearing
        os.makedirs(dataset_path, exist_ok=True)
        logging.info(f"Recreated empty dataset folder at {dataset_path}.")

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

        # Delete the user's folder after processing the files into DeepLake
        try:
            shutil.rmtree(user_folder_path)
            logging.info(f"Successfully deleted user folder: {user_folder_path}")

            # Delete the user_id folder itself (i.e., the folder in 'uploads/{user_id}')
            parent_folder = os.path.dirname(user_folder_path)
            if os.path.exists(parent_folder) and not os.listdir(parent_folder):  # Check if the folder is empty
                os.rmdir(parent_folder)
                logging.info(f"Successfully deleted user_id folder: {parent_folder}")
                
        except Exception as e:
            logging.error(f"Failed to delete user folder: {user_folder_path}. Error: {e}")
            raise Exception(f"Error deleting user folder: {e}")

        return db

    except Exception as e:
        logging.error(f"Error in vectorization process: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    # Example test run
    user_folder_path = 'uploads/3c308c688090b826ecd9f454f848ebaebf27e15b4cc757a7b5f39391ed5232d0'
    user_id = "1"  # Replace with actual user_id
    pack_id = "1"  # Replace with actual pack_id
    project_to_vector(user_folder_path, user_id, pack_id)

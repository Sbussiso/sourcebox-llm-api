import os
import shutil
from dotenv import load_dotenv
from openai import OpenAI
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import DeepLake
from custom_embedding import CustomEmbeddingFunction
from prepare_data import prepare_csv_for_embedding
from langchain.docstore.document import Document
import logging
import tiktoken
import requests

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize the embedding function
embedding_function = CustomEmbeddingFunction(client)

# Token counting function
def count_vector_tokens(access_token, text_chunks):
    encoding = tiktoken.get_encoding("cl100k_base")  # Adapt as necessary

    total_tokens = sum(len(encoding.encode(chunk)) for chunk in text_chunks)
    logging.info(f"Total vector token usage: {total_tokens}")

    # Send the total tokens to the API to record it in the database
    BASE_URL = os.getenv('AUTH_API')
    if not BASE_URL:
        logging.error("AUTH_API environment variable is not set")
        return total_tokens

    add_tokens_url = f"{BASE_URL}/user/add_tokens"
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    payload = {'tokens': total_tokens}

    try:
        response = requests.post(add_tokens_url, json=payload, headers=headers)
        if response.status_code == 200:
            logging.info(f"Successfully added {total_tokens} tokens to the user's account.")
        else:
            logging.error(f"Failed to add tokens. Status code: {response.status_code}, Response: {response.text}")
    except requests.RequestException as e:
        logging.error(f"Error occurred while trying to add tokens: {e}")

    return total_tokens


def project_to_vector(user_folder_path, user_id, pack_id, pack_type, access_token):
    """Process files in the user folder, ensure proper cleanup, and create a user-specific DeepLake dataset."""
    logging.info(f"Starting vectorization for user folder: {user_folder_path}")
    logging.info(f"User ID: {user_id}, Pack ID: {pack_id}, Pack Type: {pack_type}")

    total_tokens = 0

    try:
        # Create a unique dataset path using user_id, pack_id, and pack_type
        dataset_path = os.path.join("my_deeplake", user_id, pack_type, pack_id, "actual_deeplake_name")
        logging.info(f"Dataset path: {dataset_path}")

        # Initialize the dataset and embedding function
        db = DeepLake(dataset_path=dataset_path, embedding=embedding_function, overwrite=True)
        logging.info(f"DeepLake instance initialized for path: {dataset_path}")

        # Define allowed file extensions
        allowed_extensions = {
            ".py", ".txt", ".csv", ".json", ".md", ".html", ".xml", ".yaml", ".yml", ".pdf",
            ".js", ".docx", ".xlsx", "Dockerfile", "Procfile", ".gitignore",
            ".java", ".rb", ".go", ".sh", ".php", ".cs", ".cpp", ".c", ".ts", ".swift", ".kt", ".rs", ".r", ".scala", ".pl", ".sql"
        }

        failed_files = []
        all_chunks = []  # To collect all document chunks for token counting

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
                    if file_extension == ".csv":
                        try:
                            logging.info(f"Processing CSV file: {filename}")
                            prepared_csv_data = prepare_csv_for_embedding(file_path)
                            docs = [Document(page_content=row, metadata={'source': filename}) for row in prepared_csv_data]
                            db.add_documents(docs)

                            # Collect the CSV rows as text chunks for token counting
                            all_chunks.extend(prepared_csv_data)

                        except Exception as e:
                            failed_files.append(file_path)
                            logging.error(f"Failed to process CSV file: {filename}, Error: {e}")
                            continue
                    else:
                        try:
                            loader = TextLoader(file_path)
                            documents = loader.load()

                            # Split the document respecting token limits
                            max_chunk_size = 2000  # Adjust chunk size as needed
                            text_splitter = CharacterTextSplitter(chunk_size=max_chunk_size, chunk_overlap=100)
                            docs = text_splitter.split_documents(documents)

                            # Collect text chunks for token counting
                            all_chunks.extend([doc.page_content for doc in docs])

                            # Add documents to DeepLake
                            db.add_documents(docs)
                            logging.info(f"Successfully split document: {filename} into {len(docs)} chunks.")

                        except Exception as e:
                            failed_files.append(file_path)
                            logging.error(f"Failed to load or split file: {filename}, Error: {e}")
                            continue

        # After processing all files, count the tokens used
        if all_chunks:
            count_vector_tokens(access_token, all_chunks)

        if failed_files:
            logging.error(f"The following files failed to process: {failed_files}")
        else:
            logging.info("All files processed successfully.")

        # Clean up the user folder after processing
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

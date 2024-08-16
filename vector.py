import os
from dotenv import load_dotenv
from openai import OpenAI
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import DeepLake
from custom_embedding import CustomEmbeddingFunction

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize the embedding function
embedding_function = CustomEmbeddingFunction(client)

def project_to_vector(session_folder):
    main_directory = os.getcwd()
    user_files = os.path.join(main_directory, session_folder)
    failed_files = []

    db = DeepLake(dataset_path="./my_deeplake/", embedding=embedding_function, overwrite=True)

    # Define allowed file extensions
    allowed_extensions = allowed_extensions = {
    ".py", ".txt", ".csv", ".json", ".md", ".html", ".xml", ".yaml", ".yml", ".pdf",
    ".js", ".docx", ".xlsx", "Dockerfile", "Procfile", ".gitignore",
    ".java", ".rb", ".go", ".sh", ".php", ".cs", ".cpp", ".c", ".ts", ".swift", ".kt", ".rs", ".r", ".scala", ".pl", ".sql"
    }

    for root, dirs, files in os.walk(user_files):
        for filename in files:
            file_path = os.path.join(root, filename)
            file_extension = os.path.splitext(filename)[1]
            
            # Skip files that don't have an allowed extension
            if file_extension not in allowed_extensions:
                continue
            
            if os.path.isfile(file_path):
                try:
                    loader = TextLoader(file_path)
                    documents = loader.load()
                    text_splitter = CharacterTextSplitter(chunk_size=1500, chunk_overlap=100)
                    docs = text_splitter.split_documents(documents)
                except Exception as e:
                    failed_files.append(file_path)
                    continue

                try:
                    db.add_documents(docs)
                except Exception as e:
                    failed_files.append(file_path)

    print("Document processing done!")

    for failed_file in failed_files:
        print(failed_file)

    return db

if __name__ == "__main__":
    project_to_vector()

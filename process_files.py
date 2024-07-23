import fitz  # PyMuPDF
import pandas as pd
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import docx
import os
from io import StringIO
from openai import OpenAI
from dotenv import load_dotenv
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')
)

def get_embedding(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def read_pdf(file_path):
    text = ""
    document = fitz.open(file_path)
    for page_num in range(len(document)):
        page = document.load_page(page_num)
        text += page.get_text()
    return text

def read_txt(file_path):
    with open(file_path, 'r') as file:
        text = file.read()
    return text

def read_csv(file_path):
    data = pd.read_csv(file_path)
    return data.to_string()

def read_excel(file_path):
    data = pd.read_excel(file_path)
    return data.to_string()

def read_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return json.dumps(data, indent=4)

def read_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    return ET.tostring(root, encoding='unicode')

def read_html(file_path):
    with open(file_path, 'r') as file:
        soup = BeautifulSoup(file, 'html.parser')
    tables = pd.read_html(StringIO(str(soup)))
    result = ""
    for df in tables:
        result += df.to_string()
    return result

def read_docx(file_path):
    doc = docx.Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def read_file(file_path):
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.pdf':
        return read_pdf(file_path)
    elif file_extension == '.txt':
        return read_txt(file_path)
    elif file_extension == '.csv':
        return read_csv(file_path)
    elif file_extension in ['.xls', '.xlsx']:
        return read_excel(file_path)
    elif file_extension == '.json':
        return read_json(file_path)
    elif file_extension == '.xml':
        return read_xml(file_path)
    elif file_extension == '.html':
        return read_html(file_path)
    elif file_extension == '.docx':
        return read_docx(file_path)
    else:
        return f"Unsupported file format: {file_extension}"

def process_and_save_embeddings(session_folder):
    file_paths = [os.path.join(session_folder, file_name) for file_name in os.listdir(session_folder) if os.path.isfile(os.path.join(session_folder, file_name))]
    embeddings = {}
    for file_path in file_paths:
        content = read_file(file_path)
        if isinstance(content, str) and content.strip():
            embedding = get_embedding(content)
            embeddings[file_path] = embedding
    embeddings_file = os.path.join(session_folder, 'embeddings.npy')
    np.save(embeddings_file, embeddings)
    return embeddings_file

def load_embeddings(embeddings_file):
    return np.load(embeddings_file, allow_pickle=True).item()

def query_embeddings(embeddings, query):
    query_embedding = get_embedding(query)
    similarities = {}
    for file_path, embedding in embeddings.items():
        similarities[file_path] = cosine_similarity([query_embedding], [embedding])[0][0]
    sorted_files = sorted(similarities, key=similarities.get, reverse=True)
    return sorted_files

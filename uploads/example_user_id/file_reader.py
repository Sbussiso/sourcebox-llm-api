import os
import mimetypes
import json
import csv
import configparser
import xml.etree.ElementTree as ET
from PyPDF2 import PdfReader
from docx import Document
import openpyxl
import yaml
from bs4 import BeautifulSoup
from openai import OpenAI, OpenAIError, RateLimitError, APIError, Timeout
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure the API key is loaded
# Function to save the API key to a .env file
def save_api_key_to_env(api_key):
    # Remove existing .env file if it exists
    if os.path.exists(".env"):
        os.remove(".env")
    
    # Create a new .env file and save the API key
    with open(".env", "w") as env_file:
        env_file.write(f"OPENAI_API_KEY={api_key}\n")
    print(".env file created with the API key.")


try:
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    
    # Prompt the user to enter the API key if it's not present or failed
    manual_api_key = input("Enter your OpenAI API key: ")
    
    # Save the entered API key to a new .env file
    try:
        save_api_key_to_env(manual_api_key)
        # Reload the environment with the new API key
        load_dotenv()
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        print("OpenAI client initialized successfully.")
    except Exception as save_error:
        print(f"Error saving API key: {save_error}")
   

def is_binary_file(file_path):
    """Determines if a file is likely binary by reading the first 1024 bytes."""
    try:
        with open(file_path, 'rb') as file:
            chunk = file.read(1024)
            return b'\x00' in chunk  # If there are null bytes, it's likely binary
    except OSError as e:
        print(f"Error opening file: {e}")
        return True

def read_plain_text(file_path):
    """Reads plain text files (e.g., .txt, .py, etc.)."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"Error reading text file: {e}")
        return ""

def read_pdf(file_path):
    """Reads PDFs using PyPDF2."""
    try:
        content = ""
        reader = PdfReader(file_path)
        for page in reader.pages:
            content += page.extract_text() or ""
        return content
    except Exception as e:
        print(f"Error reading PDF file: {e}")
        return ""

def read_word_doc(file_path):
    """Reads .docx files using python-docx."""
    try:
        doc = Document(file_path)
        return '\n'.join([para.text for para in doc.paragraphs])
    except Exception as e:
        print(f"Error reading Word document: {e}")
        return ""

def read_excel(file_path):
    """Reads Excel files using openpyxl."""
    try:
        wb = openpyxl.load_workbook(file_path)
        sheet = wb.active
        content = ""
        for row in sheet.iter_rows(values_only=True):
            content += ' '.join([str(cell) for cell in row if cell is not None]) + '\n'
        return content
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return ""

def read_csv(file_path):
    """Reads CSV files using the csv module."""
    try:
        content = ""
        with open(file_path, 'r') as file:
            reader = csv.reader(file)
            for row in reader:
                content += ', '.join(row) + '\n'
        return content
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return ""

def read_json(file_path):
    """Reads JSON files using the json module."""
    try:
        with open(file_path, 'r') as file:
            return json.dumps(json.load(file), indent=4)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file: {e}")
        return ""
    except OSError as e:
        print(f"Error opening JSON file: {e}")
        return ""

def read_html(file_path):
    """Reads HTML files using BeautifulSoup."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser')
        return soup.get_text()
    except Exception as e:
        print(f"Error reading HTML file: {e}")
        return ""

def read_xml(file_path):
    """Reads XML files using xml.etree.ElementTree."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        return ET.tostring(root, encoding='unicode')
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        return ""
    except OSError as e:
        print(f"Error opening XML file: {e}")
        return ""

def read_yaml(file_path):
    """Reads YAML files using PyYAML."""
    try:
        with open(file_path, 'r') as file:
            content = yaml.safe_load(file)
        return yaml.dump(content)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        return ""
    except OSError as e:
        print(f"Error opening YAML file: {e}")
        return ""

def read_ini(file_path):
    """Reads INI configuration files using configparser."""
    try:
        config = configparser.ConfigParser()
        config.read(file_path)
        content = ""
        for section in config.sections():
            content += f"[{section}]\n"
            for key, value in config.items(section):
                content += f"{key} = {value}\n"
        return content
    except configparser.Error as e:
        print(f"Error parsing INI file: {e}")
        return ""
    except OSError as e:
        print(f"Error opening INI file: {e}")
        return ""

def read_file(file_path):
    """Attempts to read the file based on its type. Calls appropriate file-reading functions for different formats."""
    try:
        if not os.path.exists(file_path):
            print(f"The file at {file_path} does not exist.")
            return ""

        if is_binary_file(file_path):
            print(f"The file at {file_path} appears to be binary and is not human-readable.")
            return ""

        file_type, _ = mimetypes.guess_type(file_path)

        if file_type and 'text' in file_type:
            content = read_plain_text(file_path)
        elif file_type == 'application/pdf':
            content = read_pdf(file_path)
        elif file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            content = read_word_doc(file_path)
        elif file_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
            content = read_excel(file_path)
        elif file_type == 'text/csv':
            content = read_csv(file_path)
        elif file_type == 'application/json':
            content = read_json(file_path)
        elif file_type == 'text/html':
            content = read_html(file_path)
        elif file_type in ['application/xml', 'text/xml']:
            content = read_xml(file_path)
        elif file_type in ['application/x-yaml', 'text/yaml']:
            content = read_yaml(file_path)
        elif file_type == 'text/ini':
            content = read_ini(file_path)
        else:
            print(f"Unsupported file type: {file_type}")
            return ""

        return content

    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return ""

def read_directory(directory_path):
    """Iterates through all the files in the directory and subdirectories, calling read_file() on each human-readable file."""
    try:
        if not os.path.exists(directory_path):
            print(f"The directory {directory_path} does not exist.")
            return ""

        content = ""
        for root, dirs, files in os.walk(directory_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                print(f"Reading {file_path}")
                content += read_file(file_path) + "\n"

        return content

    except Exception as e:
        print(f"An error occurred while reading the directory: {e}")
        return ""

def gpt_response(prompt, file, history):
    """
    Sends a request to the GPT API with the current prompt, file content, and conversation history.
    Updates the conversation history with the new response.
    """
    history_text = f"Previous prompt: {history['prompt']}\nPrevious file content: {history['file']}\nPrevious response: {history['response']}\n"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful file reader on a user's local computer."},
                {"role": "user", "content": f"USER PROMPT: {prompt}\nUSER FILE(S) CONTENT: {file}\nCONVERSATION HISTORY: {history_text}"}
            ]
        )

        history['prompt'] = prompt
        history['file'] = file
        history['response'] = response.choices[0].message.content

        return history['response']

    except RateLimitError:
        print("Rate limit exceeded. Please wait and try again later.")
        return "Error: Rate limit exceeded. Try again later."
    except Timeout:
        print("The request timed out. Please try again.")
        return "Error: Request timed out. Try again."
    except APIError as e:
        print(f"OpenAI API returned an error: {e}")
        return f"Error: OpenAI API error: {e}"
    except OpenAIError as e:
        print(f"Error communicating with OpenAI API: {e}")
        return "Error: Unable to retrieve response from OpenAI."



if __name__ == "__main__":
    history = {
        "prompt": "",
        "file": "",
        "response": ""
    }

    while True:
        print("Select an option:")
        print("1. Query file contents")
        print("2. Query directory contents")
        print("3. Raw query")
        print("4. Exit")
        user_input = input("Enter: ")

        if user_input == "1":
            print("\n--------------------------------------------------\n")
            file_path = input("Enter the file path: ")
            file_content = read_file(file_path)
            if file_content:
                
                print(f"File content:\n{file_content}")
                prompt = input("Enter your prompt for the chatbot: ")
                response = gpt_response(prompt, file_content, history)
                print(f"Chatbot response:\n{response}")
                print("\n--------------------------------------------------\n")

        elif user_input == "2":
            print("\n--------------------------------------------------\n")
            directory_path = input("Enter the directory path: ")
            dir_content = read_directory(directory_path)
            if dir_content:
                print(f"Directory content:\n{dir_content}")
                prompt = input("Enter your prompt for the chatbot: ")
                response = gpt_response(prompt, dir_content, history)
                print(f"Chatbot response:\n{response}")
                print("\n--------------------------------------------------\n")
                
        elif user_input == "3":
            print("\n--------------------------------------------------\n")
            prompt = input("Enter your prompt for the chatbot: ")
            response = gpt_response(prompt, "", history)
            print(f"Chatbot response:\n{response}")
            print("\n--------------------------------------------------\n")
            
        # End loop
        elif user_input == "4":
            print("Exiting...")
            break
        
        else:
            print("Invalid option. Please choose either 1, 2, or 3.")

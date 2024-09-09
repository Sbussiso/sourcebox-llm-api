import logging
import os
import shutil
import openai
import requests
from flask import Flask, request, jsonify, session
from flask_restful import Resource, Api
from dotenv import load_dotenv
from uuid import uuid4
from vector import project_to_vector
from query import perform_query
from langchain_community.vectorstores import DeepLake
from custom_embedding import CustomEmbeddingFunction
import hashlib
import hashlib
import re

# Load environment variables
load_dotenv()

# Initialize Flask and Flask-RESTful
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY') or 'your_very_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
api = Api(app)

client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Ensure the upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Utility Functions

def get_user_folder(access_token):
    """Create a user-specific folder using a hashed version of the access token."""
    hashed_token = hashlib.sha256(access_token.encode()).hexdigest()
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], hashed_token)
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def sanitize_filename(url):
    """Generate a safe and valid filename for URLs by using a hash."""
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    return f"{url_hash}.txt"

def upload_and_process_pack(pack_id, access_token, route):
    logging.info("Uploading and processing pack with pack_id: %s", pack_id)

    # Fetch the pack details from the external API
    auth_base_url = 'https://sourcebox-central-auth-8396932a641c.herokuapp.com'
    get_pack_url = f'{auth_base_url}/packman/{route}/{pack_id}'

    if not access_token:
        logging.error("Access token missing. User is not authenticated.")
        raise ValueError("User not authenticated")

    headers = {'Authorization': f'Bearer {access_token}'}

    try:
        pack_response = requests.get(get_pack_url, headers=headers)
        pack_response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Error fetching pack details: {str(e)}")
        raise ValueError(f"Failed to retrieve pack details: {str(e)}")

    # Extract pack contents
    try:
        pack_data = pack_response.json()
        contents = pack_data.get('contents', [])
        logging.info(f"Successfully retrieved pack contents. Number of entries: {len(contents)}")
    except ValueError as e:
        logging.error(f"Error parsing pack data: {str(e)}")
        raise ValueError(f"Error parsing pack data: {str(e)}")

    # Create a folder for this user using their access token hash
    user_folder = get_user_folder(access_token)
    logging.info(f"Created upload folder for user with hashed token at path: {user_folder}")

    # Ensure the user folder exists
    os.makedirs(user_folder, exist_ok=True)

    # Save each file or link content from the pack to the user's folder
    for content in contents:
        data_type = content.get('data_type')
        file_content = content.get('content')
        filename = content.get('filename')

        # If this is a link, generate a valid filename using a hash
        if data_type == 'link':
            filename = sanitize_filename(file_content)

        # Ensure we have a valid filename for saving files
        if not filename:
            filename = f"data_{data_type}.txt"

        # Save the content for both files and links as text files in the user's folder
        file_path = os.path.join(user_folder, filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            logging.info(f"Saved {data_type} content to file: {filename}")
        except IOError as e:
            logging.error(f"Error saving {data_type} to {filename}: {str(e)}")
            raise IOError(f"Failed to save {data_type} content to file: {filename}: {str(e)}")

    # Process files and save embeddings
    try:
        project_to_vector(user_folder)  # Pass the folder path to the vectorization function
        logging.info("Processed pack and saved embeddings for user folder: %s", user_folder)
    except Exception as e:
        logging.error(f"Error processing files for user folder: {user_folder}. Error: {str(e)}")
        raise Exception(f"Error processing files for user folder: {str(e)}")

    return {"message": "Pack uploaded and processed successfully", "folder": user_folder}

# ChatGPT Response Function
def chatgpt_response(prompt, history=None, vector_results=None):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful code comprehension assistant. Analyze and respond based on the given context."},
            {"role": "user", "content": f"USER PROMPT: {prompt}\nVECTOR SEARCH RESULTS: {vector_results}\nCONVERSATION HISTORY: {history}"}
        ]
    )
    return response.choices[0].message.content

# DeepQueryCode Resource
class DeepQueryCode(Resource):
    def post(self):
        try:
            # Extract data from the request
            data = request.json
            user_message = data.get('user_message')
            pack_id = data.get('pack_id', None)
            history = data.get('history', '')

            logging.info("Received POST request with user_message: %s, pack_id: %s", user_message, pack_id)

            # Extract access token from the request headers
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logging.error("Authorization token missing or invalid")
                return {"error": "User not authenticated"}, 401

            # Extract the token by stripping the 'Bearer ' part
            access_token = auth_header.split(' ')[1]

            # Process the pack if a pack_id is provided
            if pack_id:
                logging.info("Processing pack with pack_id: %s", pack_id)
                route = 'code/details'
                upload_and_process_pack(pack_id, access_token, route)  # Pass the token to the function

            # Get the user-specific folder for vector querying
            user_folder = get_user_folder(access_token)

            # Set the correct dataset path for DeepLake
            deeplake_folder_path = os.path.join("my_deeplake", os.path.basename(user_folder))

            if os.path.exists(deeplake_folder_path) and os.path.isdir(deeplake_folder_path):
                logging.info("The my_deeplake folder exists for user folder: %s", user_folder)
            else:
                logging.info("The my_deeplake folder does not exist. Running project_to_vector.")
                project_to_vector(user_folder)

            # Perform vector query
            logging.info("Performing vector query with user_message: %s", user_message)
            embedding_function = CustomEmbeddingFunction(client)
            db = DeepLake(dataset_path=deeplake_folder_path, embedding=embedding_function, read_only=True)
            vector_results = perform_query(db, user_message)
            logging.info("Vector query results: %s", vector_results)

            # Generate a response using GPT, integrating history and vector results
            logging.info("Generating response using GPT with history: %s and vector_results: %s", history, vector_results)
            assistant_message = chatgpt_response(user_message, history=history, vector_results=vector_results)

            logging.info("Response generated successfully: %s", assistant_message)

            return {"message": assistant_message}, 200

        except ValueError as ve:
            logging.error("ValueError occurred: %s", str(ve))
            return {"error": str(ve)}, 400
        except Exception as e:
            logging.error("Exception occurred: %s", str(e))
            return {"error": str(e)}, 500


#regular deepquery Resource
class DeepQuery(Resource):
    def post(self):
        try:
            # Extract data from the request
            data = request.json
            user_message = data.get('user_message')
            pack_id = data.get('pack_id', None)
            history = data.get('history', '')

            logging.info("Received POST request with user_message: %s, pack_id: %s", user_message, pack_id)

            # Extract access token from the request headers
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logging.error("Authorization token missing or invalid")
                return {"error": "User not authenticated"}, 401

            # Extract the token by stripping the 'Bearer ' part
            access_token = auth_header.split(' ')[1]

            # Process the pack if a pack_id is provided
            if pack_id:
                logging.info("Processing pack with pack_id: %s", pack_id)
                route = 'pack/details'
                upload_and_process_pack(pack_id, access_token, route)  # Pass the token to the function

            # Get the user-specific folder for vector querying
            user_folder = get_user_folder(access_token)

            # Set the correct dataset path for DeepLake
            deeplake_folder_path = os.path.join("my_deeplake", os.path.basename(user_folder))

            if os.path.exists(deeplake_folder_path) and os.path.isdir(deeplake_folder_path):
                logging.info("The my_deeplake folder exists for user folder: %s", user_folder)
            else:
                logging.info("The my_deeplake folder does not exist. Running project_to_vector.")
                project_to_vector(user_folder)

            # Perform vector query
            logging.info("Performing vector query with user_message: %s", user_message)
            embedding_function = CustomEmbeddingFunction(client)
            db = DeepLake(dataset_path=deeplake_folder_path, embedding=embedding_function, read_only=True)
            vector_results = perform_query(db, user_message)
            logging.info("Vector query results: %s", vector_results)

            # Generate a response using GPT, integrating history and vector results
            logging.info("Generating response using GPT with history: %s and vector_results: %s", history, vector_results)
            assistant_message = chatgpt_response(user_message, history=history, vector_results=vector_results)

            logging.info("Response generated successfully: %s", assistant_message)

            return {"message": assistant_message}, 200

        except ValueError as ve:
            logging.error("ValueError occurred: %s", str(ve))
            return {"error": str(ve)}, 400
        except Exception as e:
            logging.error("Exception occurred: %s", str(e))
            return {"error": str(e)}, 500


#raw deepquery code resource
class DeepQueryCodeRaw(Resource):
    def post(self):
        try:
            # Extract data from the request
            data = request.json
            user_message = data.get('user_message')
            pack_id = data.get('pack_id', None)

            logging.info("Received POST request for raw vector search with user_message: %s, pack_id: %s", user_message, pack_id)

            # Extract access token from the request headers
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logging.error("Authorization token missing or invalid")
                return {"error": "User not authenticated"}, 401

            # Extract the token by stripping the 'Bearer ' part
            access_token = auth_header.split(' ')[1]
            
            # Process the pack if a pack_id is provided
            if pack_id:
                logging.info("Processing pack with pack_id: %s", pack_id)
                route = 'code/details'
                upload_and_process_pack(pack_id, access_token, route)
                
            # Get the user-specific folder for vector querying
            user_folder = get_user_folder(access_token)

            # Set the correct dataset path for DeepLake
            deeplake_folder_path = os.path.join("my_deeplake", os.path.basename(user_folder))

            if os.path.exists(deeplake_folder_path) and os.path.isdir(deeplake_folder_path):
                logging.info("The my_deeplake folder exists for user folder: %s", user_folder)
            else:
                logging.info("The my_deeplake folder does not exist. Running project_to_vector.")
                project_to_vector(user_folder)

            # Perform vector query
            logging.info("Performing vector query with user_message: %s", user_message)
            embedding_function = CustomEmbeddingFunction(client)
            db = DeepLake(dataset_path=deeplake_folder_path, embedding=embedding_function, read_only=True)
            vector_results = perform_query(db, user_message)
            
            # Check if results are empty
            if not vector_results:
                logging.info("No vector results found.")
                return {"vector_results": None}, 200

            logging.info("Vector query results: %s", vector_results)
            return {"vector_results": vector_results}, 200

        except ValueError as ve:
            logging.error("ValueError occurred: %s", str(ve))
            return {"error": str(ve)}, 400
        except Exception as e:
            logging.error("Exception occurred: %s", str(e))
            return {"error": str(e)}, 500

#raw deepquery resource

class DeepQueryRaw(Resource):
    def post(self):
        try:
            # Extract data from the request
            data = request.json
            user_message = data.get('user_message')
            pack_id = data.get('pack_id', None)

            logging.info("Received POST request for raw vector search with user_message: %s, pack_id: %s", user_message, pack_id)

            # Extract access token from the request headers
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logging.error("Authorization token missing or invalid")
                return {"error": "User not authenticated"}, 401

            # Extract the token by stripping the 'Bearer ' part
            access_token = auth_header.split(' ')[1]
            
            # Process the pack if a pack_id is provided
            if pack_id:
                logging.info("Processing pack with pack_id: %s", pack_id)
                route = 'pack/details'
                upload_and_process_pack(pack_id, access_token, route)
                
            # Get the user-specific folder for vector querying
            user_folder = get_user_folder(access_token)

            # Set the correct dataset path for DeepLake
            deeplake_folder_path = os.path.join("my_deeplake", os.path.basename(user_folder))

            if os.path.exists(deeplake_folder_path) and os.path.isdir(deeplake_folder_path):
                logging.info("The my_deeplake folder exists for user folder: %s", user_folder)
            else:
                logging.info("The my_deeplake folder does not exist. Running project_to_vector.")
                project_to_vector(user_folder)

            # Perform vector query
            logging.info("Performing vector query with user_message: %s", user_message)
            embedding_function = CustomEmbeddingFunction(client)
            db = DeepLake(dataset_path=deeplake_folder_path, embedding=embedding_function, read_only=True)
            vector_results = perform_query(db, user_message)
            
            # Check if results are empty
            if not vector_results:
                logging.info("No vector results found.")
                return {"vector_results": None}, 200

            logging.info("Vector query results: %s", vector_results)
            return {"vector_results": vector_results}, 200

        except ValueError as ve:
            logging.error("ValueError occurred: %s", str(ve))
            return {"error": str(ve)}, 400
        except Exception as e:
            logging.error("Exception occurred: %s", str(e))
            return {"error": str(e)}, 500



# Login Resource
class Login(Resource):
    def post(self):
        try:
            auth_base_url = 'https://sourcebox-central-auth-8396932a641c.herokuapp.com'
            login_url = f'{auth_base_url}/login'

            email = request.json.get('email')
            password = request.json.get('password')
            login_payload = {
                'email': email,
                'password': password
            }

            login_response = requests.post(login_url, json=login_payload)

            if login_response.status_code == 200:
                access_token = login_response.json().get('access_token')
                session['access_token'] = access_token  # Save access token to session
                logging.info("Login successful for user: %s", email)
                return {"message": "Login successful", "access_token": access_token}, 200
            else:
                logging.error("Login failed: %s", login_response.text)
                return {"error": f"Login failed: {login_response.text}"}, login_response.status_code

        except Exception as e:
            logging.error("Exception occurred during login: %s", str(e))
            return {"error": str(e)}, 500

# Delete Session Resource
class DeleteSession(Resource):
    def delete(self):
        if 'access_token' not in session:
            return {"message": "No session started"}, 400

        user_folder = get_user_folder(session['access_token'])
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)
            session.pop('access_token', None)
            logging.info("Session and all associated files deleted successfully")
            return {"message": "Session and all associated files deleted successfully"}, 200
        else:
            logging.info("No files found for this user")
            return {"message": "No files found for this session"}, 404

# Flask-RESTful Resource Routing
api.add_resource(DeepQueryCode, '/deepquery-code')
api.add_resource(DeepQuery, '/deepquery')
api.add_resource(Login, '/login')
api.add_resource(DeleteSession, '/delete-session')
api.add_resource(DeepQueryCodeRaw, '/deepquery-code-raw')
api.add_resource(DeepQueryRaw, '/deepquery-raw')


# Run the Flask Application
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)

import logging
import os
import shutil
import openai
import requests
from flask import Flask, request, jsonify, session
from flask_restful import Resource, Api
from dotenv import load_dotenv
from vector import project_to_vector
from query import perform_query
from langchain_community.vectorstores import DeepLake
from custom_embedding import CustomEmbeddingFunction
import hashlib
import hashlib
import re
import logging
import tiktoken
from langchain_community.document_loaders import WebBaseLoader   
import pandas as pd


# Configure logging (if not already configured elsewhere in your application)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)


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

def get_user_folder(user_id):
    """Create a user-specific folder using the user_id."""
    logger = logging.getLogger(__name__)
    
    logger.debug('Received user_id: %s', user_id)
    
    # Define the user folder path using user_id
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], user_id)
    logger.debug('User folder path: %s', user_folder)
    
    try:
        # Create the user-specific folder
        os.makedirs(user_folder, exist_ok=True)
        logger.info('Successfully created or verified folder: %s', user_folder)
    except Exception as e:
        logger.error('Failed to create folder %s due to: %s', user_folder, e)
        raise
    
    return user_folder


def sanitize_filename(url):
    """Generate a safe and valid filename for URLs by using a hash."""
    logger = logging.getLogger(__name__)
    
    logger.debug('Received URL: %s', url)
    
    try:
        # Hash the URL
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        logger.debug('Generated hash: %s', url_hash)
        
        # Generate the filename
        filename = f"{url_hash}.txt"
        logger.debug('Sanitized filename: %s', filename)
        
    except Exception as e:
        logger.error('Failed to sanitize filename for URL %s due to: %s', url, e)
        raise
    
    return filename

# data processing
def upload_and_process_pack(user_id, pack_id, route, pack_type, access_token):
    """
    This function uploads and processes a given pack for a user, identified by their user_id and pack_id.
    The `pack_type` distinguishes between different types of packs (e.g., 'pack' or 'code_pack').
    """
    logger = logging.getLogger(__name__)

    if not pack_id:
        logger.error("No pack_id provided, skipping pack processing.")
        return

    # Log the initiation of the upload and processing action
    logger.info("Uploading and processing %s with pack_id: %s for user_id: %s", pack_type, pack_id, user_id)

    # Define the base URL of the external API and the specific endpoint to retrieve the pack details
    auth_base_url = 'https://sourcebox-central-auth-8396932a641c.herokuapp.com'
    get_pack_url = f'{auth_base_url}/packman/{route}/{pack_id}'

    # Set the Authorization header with the Bearer token for the API request
    headers = {'Authorization': f'Bearer {access_token}'}

    # Fetch the pack details from the external API using the access token for authentication
    try:
        logger.debug("Sending request to fetch pack details from URL: %s", get_pack_url)
        pack_response = requests.get(get_pack_url, headers=headers)
        pack_response.raise_for_status()
        logger.debug("Received response with status code: %d", pack_response.status_code)
    except requests.RequestException as e:
        logger.error("Error fetching pack details from %s: %s", get_pack_url, str(e))
        raise ValueError(f"Failed to retrieve pack details: {str(e)}")

    # Extract and parse the contents of the pack from the response
    try:
        pack_data = pack_response.json()
        contents = pack_data.get('contents', [])
        logger.info("Successfully retrieved pack contents. Number of entries: %d", len(contents))
    except ValueError as e:
        logger.error("Error parsing pack data from response: %s", str(e))
        raise ValueError(f"Error parsing pack data: {str(e)}")

    # Create a folder for the user using their user ID
    user_folder = get_user_folder(user_id)
    logger.info("Created or verified upload folder for user with ID %s at path: %s", user_id, user_folder)

    # Ensure the user folder exists; if not, create it
    try:
        os.makedirs(user_folder, exist_ok=True)
        logger.debug("Ensured user folder exists at path: %s", user_folder)
    except OSError as e:
        logger.error("Error creating user folder at %s: %s", user_folder, str(e))
        raise OSError(f"Failed to create user folder: {str(e)}")

    # Iterate through the contents of the pack (links, files, etc.)
    for content in contents:
        # Determine the data type (e.g., 'link' or 'file') and retrieve the content and filename
        data_type = content.get('data_type')
        file_content = content.get('content')
        filename = content.get('filename')

        # If the content is a link, sanitize the URL to generate a valid filename
        if data_type == 'link':
            filename = sanitize_filename(file_content)
            logger.debug("Generated filename for link content: %s", filename)

        # If the filename is not provided, generate a default filename based on the data type
        if not filename:
            filename = f"data_{data_type}.txt"
            logger.debug("No filename provided; using default filename: %s", filename)

        # Define the file path where the content will be saved
        file_path = os.path.join(user_folder, filename)

        # Save the content (either file or link) to the user's folder
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            logger.info("Saved %s content to file: %s", data_type, filename)
        except IOError as e:
            logger.error("Error saving %s content to %s: %s", data_type, filename, str(e))
            raise IOError(f"Failed to save {data_type} content to file: {filename}: {str(e)}")

    # Process the uploaded files and save embeddings using the project_to_vector function
    try:
        logger.info("Running project_to_vector for user folder: %s", user_folder)
        project_to_vector(user_folder, user_id, pack_id, pack_type, access_token)
        logger.info("Processed %s and saved embeddings for user folder: %s", pack_type, user_folder)
    except Exception as e:
        logger.error("Error processing files for user folder %s: %s", user_folder, str(e))
        raise Exception(f"Error processing files for user folder: {str(e)}")

    # Return a success message along with the path to the user folder
    return {"message": f"{pack_type} uploaded and processed successfully", "folder": user_folder}


# token count
def token_count(access_token, prompt, history=None, vector_results=None, response=None):
    encoding = tiktoken.get_encoding("cl100k_base")  # Assuming GPT-4 encoding, adapt as necessary

    # Encode prompt, history, vector_results, and response
    prompt_tokens = len(encoding.encode(prompt)) if prompt else 0
    history_tokens = len(encoding.encode(history)) if history else 0
    vector_results_tokens = len(encoding.encode(vector_results)) if vector_results else 0
    response_tokens = len(encoding.encode(response)) if response else 0

    # Total token count
    total_tokens = prompt_tokens + history_tokens + vector_results_tokens + response_tokens
    logging.info(f"Token usage: Prompt={prompt_tokens}, History={history_tokens}, Vector Results={vector_results_tokens}, Response={response_tokens}, Total={total_tokens}")

    # Send the total tokens to the API to record it in the database
    BASE_URL = os.getenv('AUTH_API')
    #send total_tokens to the API
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


# ChatGPT Response Function
def chatgpt_response(access_token, prompt, history=None, vector_results=None):
    try:
        # Ensure that history and vector_results are strings
        if not isinstance(history, str):
            history = str(history)
        
        if not isinstance(vector_results, str):
            vector_results = str(vector_results)

        # Call GPT API with formatted history and vector results
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful code comprehension assistant. Analyze and respond based on the given context."},
                {"role": "user", "content": f"USER PROMPT: {prompt}\nVECTOR SEARCH RESULTS: {vector_results}\nCONVERSATION HISTORY: {history}"}
            ]
        )

        response_content = response.choices[0].message.content

        # Calculate and print token usage (assuming token_count is another function)
        token_count(access_token, prompt, history, vector_results, response_content)

        return response_content

    except Exception as e:
        logging.error(f"Error generating GPT response: {e}")
        return f"Error: {e}"


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

            # Validate user_message input
            if not isinstance(user_message, str) or not user_message:
                logging.error("Invalid user_message provided: %s", user_message)
                return {"error": "Invalid user_message provided"}, 400

            # Extract access token from the request headers
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logging.error("Authorization token missing or invalid")
                return {"error": "User not authenticated"}, 401

            # Extract the token by stripping the 'Bearer ' part
            access_token = auth_header.split(' ')[1]

            try:
                # Fetch the user ID using the external API with the access token
                auth_base_url = 'https://sourcebox-central-auth-8396932a641c.herokuapp.com'
                get_user_id_url = f'{auth_base_url}/user/id'
                headers = {'Authorization': f'Bearer {access_token}'}
                user_id_response = requests.get(get_user_id_url, headers=headers)
                user_id_response.raise_for_status()  # Raise an exception for bad HTTP responses

                user_id = user_id_response.json().get('user_id')
                if not user_id:
                    logging.error("User ID not found in the response")
                    return {"error": "Failed to retrieve user ID"}, 500
            except requests.exceptions.RequestException as e:
                logging.error(f"Failed to retrieve user ID: {str(e)}")
                return {"error": f"Failed to retrieve user ID: {str(e)}"}, 500

            # Ensure user_id and pack_id are strings to prevent errors during file path generation
            try:
                user_id = str(user_id)
                if pack_id:
                    pack_id = str(pack_id)
            except Exception as e:
                logging.error(f"Error converting user_id/pack_id to string: {str(e)}")
                return {"error": "Error processing user_id or pack_id"}, 500

            # Set the pack type to "code_pack"
            pack_type = "code_pack"

            # Process the pack if a pack_id is provided
            if pack_id:
                try:
                    logging.info("Processing code pack with pack_id: %s", pack_id)
                    route = 'code/details'
                    upload_and_process_pack(user_id, pack_id, route, pack_type, access_token)
                except Exception as e:
                    logging.error(f"Error processing pack: {str(e)}")
                    return {"error": "Error processing pack"}, 500

                # Get the user-specific folder for vector querying
                try:
                    user_folder = get_user_folder(user_id)
                except Exception as e:
                    logging.error(f"Error retrieving user folder: {str(e)}")
                    return {"error": "Error retrieving user folder"}, 500

                # Set the correct dataset path for DeepLake based on user_id, pack_id, and pack_type
                try:
                    deeplake_folder_path = os.path.join("my_deeplake", user_id, pack_type, pack_id or "", "actual_deeplake_name")

                    if os.path.exists(deeplake_folder_path) and os.path.isdir(deeplake_folder_path):
                        logging.info("The my_deeplake folder exists for user folder: %s", user_folder)
                    else:
                        logging.info("The my_deeplake folder does not exist. Running project_to_vector.")
                        project_to_vector(user_folder, user_id, pack_id, pack_type, access_token)
                except Exception as e:
                    logging.error(f"Error setting or accessing dataset path: {str(e)}")
                    return {"error": "Error processing dataset path"}, 500

                # Perform vector query
                try:
                    logging.info("Performing vector query with user_message: %s", user_message)
                    embedding_function = CustomEmbeddingFunction(client)
                    db = DeepLake(dataset_path=deeplake_folder_path, embedding=embedding_function, read_only=True)
                    vector_results = perform_query(db, user_message)
                    logging.info("Vector query results: %s", vector_results)
                except Exception as e:
                    logging.error(f"Error performing vector query: {str(e)}")
                    return {"error": "Error during vector query"}, 500

                # Generate a response using GPT, integrating history and vector results
                try:
                    logging.info("Generating response using GPT with history: %s and vector_results: %s", history, vector_results)
                    assistant_message = chatgpt_response(access_token, user_message, history=history, vector_results=vector_results)
                except Exception as e:
                    logging.error(f"Error generating GPT response: {str(e)}")
                    return {"error": "Error generating GPT response"}, 500
            else:
                try:
                    # No pack_id provided, perform non-vector GPT response
                    logging.info("No pack id provided. Performing non-vector GPT response.")
                    assistant_message = chatgpt_response(access_token, user_message, history=history)
                except Exception as e:
                    logging.error(f"Error generating non-vector GPT response: {str(e)}")
                    return {"error": "Error generating non-vector GPT response"}, 500

            logging.info("Response generated successfully: %s", assistant_message)

            return {"message": assistant_message}, 200

        except ValueError as ve:
            logging.error("ValueError occurred: %s", str(ve))
            return {"error": str(ve)}, 400
        except Exception as e:
            logging.error("Exception occurred: %s", str(e))
            return {"error": str(e)}, 500


class DeepQuery(Resource):
    def post(self):
        try:
            # Extract data from the request
            try:
                data = request.json
                user_message = data.get('user_message')
                pack_id = data.get('pack_id', None)
                history = data.get('history', '')
                logging.info("Extracted user_message: %s, pack_id: %s, history: %s", user_message, pack_id, history)
            except Exception as e:
                logging.error("Error extracting data from request: %s", str(e))
                return {"error": "Error extracting data from request"}, 400

            # Validate the user_message input
            try:
                if not isinstance(user_message, str) or not user_message:
                    logging.error("Invalid user_message provided: %s", user_message)
                    return {"error": "Invalid user_message provided"}, 400
            except Exception as e:
                logging.error("Error validating user_message: %s", str(e))
                return {"error": "Error validating user_message"}, 400

            # Extract access token from the request headers
            try:
                auth_header = request.headers.get('Authorization')
                if not auth_header or not auth_header.startswith('Bearer '):
                    logging.error("Authorization token missing or invalid")
                    return {"error": "User not authenticated"}, 401

                access_token = auth_header.split(' ')[1]
                logging.info("Access token extracted successfully")
            except Exception as e:
                logging.error("Error extracting access token: %s", str(e))
                return {"error": "Error extracting access token"}, 401

            # Fetch the user ID using the external API with the access token
            try:
                auth_base_url = 'https://sourcebox-central-auth-8396932a641c.herokuapp.com'
                get_user_id_url = f'{auth_base_url}/user/id'
                headers = {'Authorization': f'Bearer {access_token}'}

                user_id_response = requests.get(get_user_id_url, headers=headers)
                if user_id_response.status_code == 200:
                    user_id = user_id_response.json().get('user_id')
                    if not user_id:
                        logging.error("User ID not found in the response")
                        return {"message": "Failed to retrieve user ID"}, 500
                    logging.info("User ID retrieved: %s", user_id)
                else:
                    logging.error("Failed to retrieve user ID: %s", user_id_response.text)
                    return {"error": f"Failed to retrieve user ID: {user_id_response.text}"}, user_id_response.status_code
            except Exception as e:
                logging.error("Error fetching user ID: %s", str(e))
                return {"error": "Error fetching user ID"}, 500

            # Ensure user_id and pack_id are strings
            try:
                user_id = str(user_id)
                if pack_id:
                    if not isinstance(pack_id, str):
                        logging.error("Invalid pack_id provided: %s", pack_id)
                        return {"error": "Invalid pack_id provided"}, 400
                    pack_id = str(pack_id)
                logging.info("User ID and Pack ID are valid: user_id=%s, pack_id=%s", user_id, pack_id)
            except Exception as e:
                logging.error("Error processing user_id and pack_id: %s", str(e))
                return {"error": "Error processing user_id and pack_id"}, 400

            # Process the pack if a pack_id is provided
            if pack_id:
                try:
                    logging.info("Processing regular pack with pack_id: %s", pack_id)
                    route = 'pack/details'
                    upload_and_process_pack(user_id, pack_id, route, 'pack', access_token)
                except Exception as e:
                    logging.error("Error processing pack: %s", str(e))
                    return {"error": "Error processing pack"}, 500

            # Get the user-specific folder for vector querying
            try:
                user_folder = get_user_folder(user_id)
                logging.info("User folder: %s", user_folder)
            except Exception as e:
                logging.error("Error getting user folder: %s", str(e))
                return {"error": "Error getting user folder"}, 500

            # Set the correct dataset path for DeepLake based on user_id, pack_id, and pack_type
            if pack_id:
                try:
                    logging.info("Processing DeepLake for pack_id: %s", pack_id)
                    deeplake_folder_path = os.path.join("my_deeplake", user_id, 'pack', pack_id, "actual_deeplake_name")

                    if os.path.exists(deeplake_folder_path) and os.path.isdir(deeplake_folder_path):
                        logging.info("DeepLake folder exists: %s", deeplake_folder_path)
                    else:
                        logging.info("DeepLake folder does not exist, running project_to_vector")
                        project_to_vector(user_folder, user_id, pack_id, 'pack', access_token)
                except Exception as e:
                    logging.error("Error with DeepLake folder: %s", str(e))
                    return {"error": "Error with DeepLake folder"}, 500

                # Perform vector query
                try:
                    logging.info("Performing vector query")
                    embedding_function = CustomEmbeddingFunction(client)
                    db = DeepLake(dataset_path=deeplake_folder_path, embedding=embedding_function, read_only=True)
                    vector_results = perform_query(db, user_message)
                except Exception as e:
                    logging.error("Error during vector query: %s", str(e))
                    return {"error": "Error during vector query"}, 500

                # Check if the vector query returned results
                if not vector_results:
                    logging.error("Vector query returned no results")
                    return {"error": "No vector results found"}, 400

                logging.info("Vector query results: %s", vector_results)

                # Generate a response using GPT, integrating history and vector results
                try:
                    logging.info("Generating GPT response with vector results")
                    assistant_message = chatgpt_response(access_token, user_message, history=history, vector_results=vector_results)
                except Exception as e:
                    logging.error("Error generating GPT response: %s", str(e))
                    return {"error": "Error generating GPT response"}, 500
            else:
                try:
                    logging.info("No pack id provided, performing non-vector GPT response")
                    assistant_message = chatgpt_response(access_token, user_message, history=history)
                except Exception as e:
                    logging.error("Error generating non-vector GPT response: %s", str(e))
                    return {"error": "Error generating non-vector GPT response"}, 500

            logging.info("Response generated successfully: %s", assistant_message)

            return {"message": assistant_message}, 200

        except ValueError as ve:
            logging.error("ValueError occurred: %s", str(ve))
            return {"error": str(ve)}, 400
        except Exception as e:
            logging.error("Unhandled exception occurred: %s", str(e))
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

            # Fetch the user ID using the external API with the access token
            auth_base_url = 'https://sourcebox-central-auth-8396932a641c.herokuapp.com'
            get_user_id_url = f'{auth_base_url}/user/id'
            headers = {'Authorization': f'Bearer {access_token}'}
            
            user_id_response = requests.get(get_user_id_url, headers=headers)
            if user_id_response.status_code == 200:
                user_id = user_id_response.json().get('user_id')
                if not user_id:
                    logging.error("User ID not found in the response")
                    return {"message": "Failed to retrieve user ID"}, 500
            else:
                logging.error(f"Failed to retrieve user ID: {user_id_response.text}")
                return {"error": f"Failed to retrieve user ID: {user_id_response.text}"}, user_id_response.status_code

            # Ensure user_id and pack_id are strings
            user_id = str(user_id)
            if pack_id:
                pack_id = str(pack_id)

            # Set the pack type to "code_pack" for code-specific packs
            pack_type = "code_pack"
            
            # Process the pack if a pack_id is provided
            if pack_id:
                logging.info("Processing code pack with pack_id: %s", pack_id)
                route = 'code/details'
                upload_and_process_pack(user_id, pack_id, route, pack_type, access_token)  # Pass user_id, pack_id, route, and pack_type
                
            # Get the user-specific folder for vector querying
            user_folder = get_user_folder(user_id)

            # Set the correct dataset path for DeepLake based on user_id, pack_id, and pack_type
            deeplake_folder_path = os.path.join("my_deeplake", user_id, pack_type, pack_id or "", "actual_deeplake_name")

            if os.path.exists(deeplake_folder_path) and os.path.isdir(deeplake_folder_path):
                logging.info("The my_deeplake folder exists for user folder: %s", user_folder)
            else:
                logging.info("The my_deeplake folder does not exist. Running project_to_vector.")
                project_to_vector(user_folder, user_id, pack_id, pack_type, access_token)  # Pass the pack_type to project_to_vector

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

            # Fetch the user ID using the external API with the access token
            auth_base_url = 'https://sourcebox-central-auth-8396932a641c.herokuapp.com'
            get_user_id_url = f'{auth_base_url}/user/id'
            headers = {'Authorization': f'Bearer {access_token}'}
            
            user_id_response = requests.get(get_user_id_url, headers=headers)
            if user_id_response.status_code == 200:
                user_id = user_id_response.json().get('user_id')
                if not user_id:
                    logging.error("User ID not found in the response")
                    return {"message": "Failed to retrieve user ID"}, 500
            else:
                logging.error(f"Failed to retrieve user ID: {user_id_response.text}")
                return {"error": f"Failed to retrieve user ID: {user_id_response.text}"}, user_id_response.status_code

            # Ensure user_id and pack_id are strings
            user_id = str(user_id)
            if pack_id:
                pack_id = str(pack_id)

            # Set the pack type to "pack"
            pack_type = "pack"
            
            # Process the pack if a pack_id is provided
            if pack_id:
                logging.info("Processing pack with pack_id: %s", pack_id)
                route = 'pack/details'
                upload_and_process_pack(user_id, pack_id, route, pack_type, access_token)

            # Get the user-specific folder for vector querying
            user_folder = get_user_folder(user_id)

            # Set the correct dataset path for DeepLake based on user_id, pack_id, and pack_type
            deeplake_folder_path = os.path.join("my_deeplake", user_id, pack_type, pack_id or "", "actual_deeplake_name")

            if os.path.exists(deeplake_folder_path) and os.path.isdir(deeplake_folder_path):
                logging.info("The my_deeplake folder exists for user folder: %s", user_folder)
            else:
                logging.info("The my_deeplake folder does not exist. Running project_to_vector.")
                project_to_vector(user_folder, user_id, pack_id, pack_type, access_token)

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
        logger = logging.getLogger(__name__)
        logger.info("Entered UserLogin post method")
        try:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                logger.error("Email and password are required")
                return {"message": "Email and password are required"}, 400

            auth_base_url = 'https://sourcebox-central-auth-8396932a641c.herokuapp.com'
            login_url = f'{auth_base_url}/login'
            get_user_id_url = f'{auth_base_url}/user/id'
            payload = {'email': email, 'password': password}

            # Authenticate and retrieve access token
            response = requests.post(login_url, json=payload)
            if response.status_code == 200:
                access_token = response.json().get('access_token')
                if not access_token:
                    logger.error("Access token not found in the response")
                    return {"message": "Failed to retrieve access token"}, 500

                # Fetch the user ID using the access token
                headers = {'Authorization': f'Bearer {access_token}'}
                user_id_response = requests.get(get_user_id_url, headers=headers)

                if user_id_response.status_code == 200:
                    user_id = user_id_response.json().get('user_id')
                    if not user_id:
                        logger.error("User ID not found in the response")
                        return {"message": "Failed to retrieve user ID"}, 500

                    logger.info(f"User {email} logged in successfully with user ID {user_id}")
                    return {"access_token": access_token, "user_id": user_id}, 200
                else:
                    logger.error(f"Failed to retrieve user ID: {user_id_response.text}")
                    return {"error": f"Failed to retrieve user ID: {user_id_response.text}"}, user_id_response.status_code
            else:
                logger.error(f"Login failed: {response.text}")
                return {"error": f"Login failed: {response.text}"}, response.status_code

        except Exception as e:
            logger.error(f"Unexpected error during user login: {str(e)}", exc_info=True)
            return {"error": "Something went wrong"}, 500


# Delete Session Resource
class DeleteSession(Resource):
    def delete(self):
        logger = logging.getLogger(__name__)
        try:
            # Extract user_id from request data
            data = request.get_json()
            user_id = data.get('user_id')
            if not user_id:
                return {"message": "user_id is required"}, 400

            logger.info(f"Deleting session and associated files for user: {user_id}")
            
            # Retrieve the user's folder using the user_id
            user_folder = get_user_folder(user_id)
            
            # Delete user's upload folder
            if os.path.exists(user_folder):
                shutil.rmtree(user_folder)
                logger.info("User's upload folder deleted successfully for user: %s", user_id)
            else:
                logger.info("No upload files found for this user with user_id: %s", user_id)

            # Path to the user's DeepLake folder (all packs associated with this user)
            deeplake_user_folder = os.path.join("my_deeplake", user_id)

            # Delete the user's DeepLake folder and its contents
            if os.path.exists(deeplake_user_folder):
                shutil.rmtree(deeplake_user_folder)
                logger.info("User's DeepLake folder deleted successfully for user: %s", user_id)
            else:
                logger.info("No DeepLake files found for this user with user_id: %s", user_id)

            logger.info("Session and all associated files deleted successfully for user: %s", user_id)
            return {"message": "Session and all associated files deleted successfully"}, 200
        except Exception as e:
            logger.error(f"Unexpected error during session deletion: {str(e)}", exc_info=True)
            return {"error": "Something went wrong"}, 500



# _____________landing page example usage resources_______________

#rag example
class LandingRagExample(Resource):
    def post(self):
        try:
            # Get current working directory and the CSV file path
            cwd = os.getcwd()
            file_path = os.path.join(cwd, 'landing-examples', 'customers.csv')

            # Extract the prompt from the request
            data = request.get_json()
            prompt = data.get('prompt')

            # Validate the prompt
            if not isinstance(prompt, str) or not prompt.strip():
                logging.error("Invalid or missing prompt")
                return {"error": "Invalid or missing prompt"}, 400

            # Read the file content
            try:
                with open(file_path, 'r') as file:
                    file_content = file.read()
                logging.info("Successfully read the file content")
            except Exception as e:
                logging.error(f"Error reading file content: {e}")
                return {"error": "Error reading file content"}, 500

            # Function to generate GPT response
            def chatgpt_response(prompt, file_content):
                try:
                    # Call GPT API with formatted history and vector results
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant. Analyze and respond based on the given context."},
                            {"role": "user", "content": f"USER PROMPT: {prompt}\nFILE CONTENT: {file_content}"}
                        ]
                    )
                    logging.info("GPT response generated successfully")
                    return response.choices[0].message.content

                except Exception as e:
                    logging.error(f"Error generating GPT response: {e}")
                    return f"Error: {e}"

            # Generate GPT response
            result = chatgpt_response(prompt, file_content)

            # Return the result
            return {"result": result}, 200

        except ValueError as ve:
            logging.error(f"ValueError occurred: {ve}")
            return {"error": str(ve)}, 400
        except Exception as e:
            logging.error(f"Unhandled exception occurred: {e}")
            return {"error": str(e)}, 500



class LandingSentimentExample(Resource):
    def post(self):
        try:
           
            # Extract the prompt from the request
            data = request.get_json()
            prompt = data.get('prompt')

            # Validate the prompt
            if not isinstance(prompt, str) or not prompt.strip():
                logging.error("Invalid or missing prompt")
                return {"error": "Invalid or missing prompt"}, 400


            # Function to generate GPT response
            def chatgpt_response(prompt):
                try:
                    # Call GPT API with formatted history and vector results
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": """You are a sentiment analyst.
                                                            Analyze the sentiment of the given text and provide a sentiment score based on the context.
                                                            Describe the overall sentiment as positive, negative, or neutral.
                                                            Break down exactly what is being said and why it is positive, negative, or neutral."""},   

                            {"role": "user", "content": f"USER PROMPT: {prompt}"}
                        ]
                    )
                    logging.info("GPT response generated successfully")
                    return response.choices[0].message.content

                except Exception as e:
                    logging.error(f"Error generating GPT response: {e}")
                    return f"Error: {e}"

            # Generate GPT response
            result = chatgpt_response(prompt)

            # Return the result
            return {"result": result}, 200

        except ValueError as ve:
            logging.error(f"ValueError occurred: {ve}")
            return {"error": str(ve)}, 400
        except Exception as e:
            logging.error(f"Unhandled exception occurred: {e}")
            return {"error": str(e)}, 500



class LandingWebScrapeExample(Resource):
    def post(self):
        try:
            # Extract the prompt from the request
            data = request.get_json()
            prompt = data.get('prompt')

            # Path to the webscraped file
            save_path = os.path.join(os.getcwd(), 'landing-examples', 'webscraped_reviews.txt')

            # Check if the webscraped file exists
            if os.path.exists(save_path):
                logging.info(f"File found at {save_path}. Skipping scraping and loading the file contents.")
                
                # Read the content of the file
                with open(save_path, 'r') as f:
                    webscrape_data = f.read()
            else:
                # File doesn't exist, scrape the content
                logging.info(f"File not found at {save_path}. Scraping the content from the web.")
                
                # Link to the Amazon product reviews page
                link = "https://www.amazon.com/product-reviews/B07SK575G9/ref=pd_bap_d_grid_rp_0_31_d_sccl_31_cr/141-2834517-6684030?pd_rd_i=B07SK575G9"
                
                # Load the data from the link
                loader = WebBaseLoader(link)
                docs = loader.load()

                # Convert the docs to a string
                docs_content = " ".join([doc.page_content for doc in docs])

                # Regular expression pattern to match the reviews
                pattern = r'(?P<reviewer>[\w\s]+)(?P<rating>\d\.\d) out of 5 stars(?P<review>[\w\s,]+)Reviewed in the United States on (?P<date>[\w\s\d,]+)'

                # Apply regex to the content
                matches = re.finditer(pattern, docs_content)

                # Prepare the extracted data for a DataFrame
                reviews = []

                for match in matches:
                    reviewer = match.group('reviewer').strip()
                    rating = float(match.group('rating'))
                    review = match.group('review').strip()
                    date = match.group('date').strip()

                    reviews.append({
                        'Reviewer': reviewer,
                        'Rating': rating,
                        'Review': review,
                        'Date': date
                    })

                # Create a DataFrame
                df = pd.DataFrame(reviews)

                # Convert the full DataFrame to a string to pass to the GPT model
                webscrape_data = df.to_string(index=False)

                # Save the DataFrame content as a text file
                with open(save_path, 'w') as f:
                    f.write(webscrape_data)

                logging.info(f"Webscraped reviews saved at: {save_path}")

            # Function to generate GPT response
            def chatgpt_response(review_data, prompt):
                try:
                    # Call GPT API with formatted history and vector results
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": """You are a helpful assistant for analyzing product reviews."""},
                            {"role": "user", "content": f"USER PROMPT: {prompt} Reviews: {review_data}"}
                        ]
                    )
                    logging.info("GPT response generated successfully")
                    return response.choices[0].message.content

                except Exception as e:
                    logging.error(f"Error generating GPT response: {e}")
                    return f"Error: {e}"

            # Generate GPT response using the file content (whether scraped or loaded)
            result = chatgpt_response(webscrape_data, prompt)

            # Return the result
            return {"result": result}, 200

        except ValueError as ve:
            logging.error(f"ValueError occurred: {ve}")
            return {"error": str(ve)}, 400
        except Exception as e:
            logging.error(f"Unhandled exception occurred: {e}")
            return {"error": str(e)}, 500



class LandingImageGenExample(Resource):
    def post(self):
        try:
            # Extract the prompt from the request
            data = request.get_json()
            prompt = data.get('prompt')

            try:
                def image_generator(prompt):
                    response = client.images.generate(
                        model="dall-e-3",
                        prompt=prompt,
                        size="1024x1024",
                        quality="standard",
                        n=1,
                        )
                    
                    image_url = response.data[0].url
                    return image_url
                    
            
                result = image_generator(prompt)
                # Return the result
                return {"result": result}, 200
            
            except Exception as e:
                logging.error(f"Error generating image: {e}")
                return {"error": "Error generating image"}, 500

        except ValueError as ve:
            logging.error(f"ValueError occurred: {ve}")
            return {"error": str(ve)}, 400
        except Exception as e:
            logging.error(f"Unhandled exception occurred: {e}")
            return {"error": str(e)}, 500



# Flask-RESTful Resource Routing
api.add_resource(DeepQueryCode, '/deepquery-code')
api.add_resource(DeepQuery, '/deepquery')
api.add_resource(Login, '/login')
api.add_resource(DeleteSession, '/delete-session')
api.add_resource(DeepQueryCodeRaw, '/deepquery-code-raw')
api.add_resource(DeepQueryRaw, '/deepquery-raw')
api.add_resource(LandingRagExample, '/landing-rag-example')
api.add_resource(LandingSentimentExample, '/landing-sentiment-example')
api.add_resource(LandingWebScrapeExample, '/landing-webscrape-example')
api.add_resource(LandingImageGenExample, '/landing-imagegen-example')

# Run the Flask Application
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)

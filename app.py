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
import logging


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


def upload_and_process_pack(user_id, pack_id, route, pack_type):
    """
    This function uploads and processes a given pack for a user, identified by their user_id and pack_id. 
    The `pack_type` distinguishes between different types of packs (e.g., 'pack' or 'code_pack').
    """
    logger = logging.getLogger(__name__)

    # Log the initiation of the upload and processing action
    logger.info("Uploading and processing %s with pack_id: %s for user_id: %s", pack_type, pack_id, user_id)

    # Define the base URL of the external API and the specific endpoint to retrieve the pack details
    auth_base_url = 'https://sourcebox-central-auth-8396932a641c.herokuapp.com'
    get_pack_url = f'{auth_base_url}/packman/{route}/{pack_id}'

    # Retrieve the access token from the session to authenticate the API request
    access_token = session.get('access_token')
    if not access_token:
        logger.error("Access token not found in session. User not authenticated.")
        raise ValueError("User not authenticated")

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
        # Pass the user folder path, user ID, pack ID, and pack type to the vectorization function
        project_to_vector(user_folder, user_id, pack_id, pack_type)
        logger.info("Processed %s and saved embeddings for user folder: %s", pack_type, user_folder)
    except Exception as e:
        logger.error("Error processing files for user folder %s: %s", user_folder, str(e))
        raise Exception(f"Error processing files for user folder: {str(e)}")

    # Return a success message along with the path to the user folder
    return {"message": f"{pack_type} uploaded and processed successfully", "folder": user_folder}


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

            # Convert user_id and pack_id to strings to prevent any join() errors
            user_id = str(user_id)
            if pack_id:
                pack_id = str(pack_id)

            # Set the pack type to "code_pack"
            pack_type = "code_pack"

            # Process the pack if a pack_id is provided
            if pack_id:
                logging.info("Processing code pack with pack_id: %s", pack_id)
                route = 'code/details'
                upload_and_process_pack(user_id, pack_id, route, pack_type)  # Pass user_id, pack_id, route, and pack_type

            # Get the user-specific folder for vector querying
            user_folder = get_user_folder(user_id)

            # Set the correct dataset path for DeepLake based on user_id, pack_id, and pack_type
            deeplake_folder_path = os.path.join("my_deeplake", user_id, pack_type, pack_id or "", "actual_deeplake_name")

            if os.path.exists(deeplake_folder_path) and os.path.isdir(deeplake_folder_path):
                logging.info("The my_deeplake folder exists for user folder: %s", user_folder)
            else:
                logging.info("The my_deeplake folder does not exist. Running project_to_vector.")
                project_to_vector(user_folder, user_id, pack_id, pack_type)

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
                logging.info("Processing regular pack with pack_id: %s", pack_id)
                route = 'pack/details'
                upload_and_process_pack(user_id, pack_id, route, pack_type)  # Pass user_id, pack_id, route, and pack_type

            # Get the user-specific folder for vector querying
            user_folder = get_user_folder(user_id)

            # Set the correct dataset path for DeepLake based on user_id, pack_id, and pack_type
            deeplake_folder_path = os.path.join("my_deeplake", user_id, pack_type, pack_id or "", "actual_deeplake_name")

            if os.path.exists(deeplake_folder_path) and os.path.isdir(deeplake_folder_path):
                logging.info("The my_deeplake folder exists for user folder: %s", user_folder)
            else:
                logging.info("The my_deeplake folder does not exist. Running project_to_vector.")
                project_to_vector(user_folder, user_id, pack_id, pack_type)

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
                upload_and_process_pack(user_id, pack_id, route, pack_type)  # Pass user_id, pack_id, route, and pack_type
                
            # Get the user-specific folder for vector querying
            user_folder = get_user_folder(user_id)

            # Set the correct dataset path for DeepLake based on user_id, pack_id, and pack_type
            deeplake_folder_path = os.path.join("my_deeplake", user_id, pack_type, pack_id or "", "actual_deeplake_name")

            if os.path.exists(deeplake_folder_path) and os.path.isdir(deeplake_folder_path):
                logging.info("The my_deeplake folder exists for user folder: %s", user_folder)
            else:
                logging.info("The my_deeplake folder does not exist. Running project_to_vector.")
                project_to_vector(user_folder, user_id, pack_id, pack_type)  # Pass the pack_type to project_to_vector

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
                upload_and_process_pack(user_id, pack_id, route, pack_type)

            # Get the user-specific folder for vector querying
            user_folder = get_user_folder(user_id)

            # Set the correct dataset path for DeepLake based on user_id, pack_id, and pack_type
            deeplake_folder_path = os.path.join("my_deeplake", user_id, pack_type, pack_id or "", "actual_deeplake_name")

            if os.path.exists(deeplake_folder_path) and os.path.isdir(deeplake_folder_path):
                logging.info("The my_deeplake folder exists for user folder: %s", user_folder)
            else:
                logging.info("The my_deeplake folder does not exist. Running project_to_vector.")
                project_to_vector(user_folder, user_id, pack_id, pack_type)

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
            get_user_id_url = f'{auth_base_url}/user/id'  # New endpoint to get user ID
            payload = {'email': email, 'password': password}

            # Authenticate and retrieve access token
            response = requests.post(login_url, json=payload)
            if response.status_code == 200:
                access_token = response.json().get('access_token')
                if not access_token:
                    logger.error("Access token not found in the response")
                    return {"message": "Failed to retrieve access token"}, 500

                session['access_token'] = access_token

                # Now fetch the user ID using the access token
                headers = {'Authorization': f'Bearer {access_token}'}
                user_id_response = requests.get(get_user_id_url, headers=headers)

                if user_id_response.status_code == 200:
                    user_id = user_id_response.json().get('user_id')
                    if not user_id:
                        logger.error("User ID not found in the response")
                        return {"message": "Failed to retrieve user ID"}, 500

                    # Store the user_id in the session
                    session['user_id'] = user_id

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
        # Check if 'user_id' exists in session instead of 'access_token'
        if 'user_id' not in session:
            return {"message": "No session started"}, 400

        # Retrieve the user's folder using the user_id from the session
        user_id = session['user_id']
        user_folder = get_user_folder(user_id)
        
        # Delete user's upload folder
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)
            logging.info("User's upload folder deleted successfully for user: %s", user_id)
        else:
            logging.info("No upload files found for this user with user_id: %s", user_id)

        #convert to strings
        user_id = str(user_id)
        
        # Path to the user's DeepLake folder (all packs associated with this user)
        deeplake_user_folder = os.path.join("my_deeplake", user_id)

        # Delete the user's DeepLake folder and its contents
        if os.path.exists(deeplake_user_folder):
            shutil.rmtree(deeplake_user_folder)
            logging.info("User's DeepLake folder deleted successfully for user: %s", user_id)
        else:
            logging.info("No DeepLake files found for this user with user_id: %s", user_id)

        # Remove 'user_id' from the session to log the user out
        session.pop('user_id', None)

        logging.info("Session and all associated files deleted successfully for user: %s", user_id)
        return {"message": "Session and all associated files deleted successfully"}, 200


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

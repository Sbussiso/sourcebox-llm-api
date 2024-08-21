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





def upload_and_process_pack(pack_id, access_token):
    logging.info("Uploading and processing pack with pack_id: %s", pack_id)

    # Fetch the pack details from the external API
    auth_base_url = 'https://sourcebox-central-auth-8396932a641c.herokuapp.com'
    get_code_pack_url = f'{auth_base_url}/packman/code/details/{pack_id}'

    if not access_token:
        logging.error("Access token missing. User is not authenticated.")
        raise ValueError("User not authenticated")

    # Prepare the request headers
    headers = {'Authorization': f'Bearer {access_token}'}

    logging.debug(f"Using access token: {access_token}")

    # Send the request to fetch the code pack details
    try:
        pack_response = requests.get(get_code_pack_url, headers=headers)
    except requests.RequestException as e:
        logging.error(f"Error fetching code pack details: {str(e)}")
        raise ValueError(f"Failed to retrieve code pack details due to network issue: {str(e)}")

    if pack_response.status_code != 200:
        logging.error(f"Failed to retrieve code pack details: {pack_response.text}")
        raise ValueError(f"Failed to retrieve code pack details: {pack_response.text}")

    # Extract pack contents
    try:
        pack_data = pack_response.json()
        contents = pack_data.get('contents', [])
        logging.info(f"Successfully retrieved pack contents. Number of files: {len(contents)}")
    except ValueError as e:
        logging.error(f"Error parsing pack data: {str(e)}")
        raise ValueError(f"Error parsing pack data: {str(e)}")

    # Create the folder for this pack (using pack_id instead of session_id)
    upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(pack_id))
    os.makedirs(upload_folder, exist_ok=True)
    logging.info("Created upload folder for pack_id: %s at path: %s", pack_id, upload_folder)

    # Save each file from the pack to the upload folder
    for content in contents:
        filename = content.get('filename')
        file_content = content.get('content')

        if filename and file_content:
            file_path = os.path.join(upload_folder, filename)
            try:
                with open(file_path, 'w') as f:
                    f.write(file_content)
                logging.info("Saved file: %s to pack folder", filename)
            except IOError as e:
                logging.error(f"Error saving file {filename}: {str(e)}")
                raise IOError(f"Failed to save file {filename} to pack folder: {str(e)}")

    # Process files and save embeddings
    try:
        project_to_vector(upload_folder)  # Pass the folder path instead of session_id
        logging.info("Processed pack and saved embeddings for pack_id: %s", pack_id)
    except Exception as e:
        logging.error(f"Error processing files for pack_id: {pack_id}. Error: {str(e)}")
        raise Exception(f"Error processing files for pack_id: {pack_id}. Error: {str(e)}")

    return {"message": "Pack uploaded and processed successfully", "pack_id": pack_id}





def chatgpt_response(prompt, history=None, vector_results=None):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful code comprehension assistant. Analyze and respond based on the given context."},
            {"role": "user", "content": f"USER PROMPT: {prompt}\nVECTOR SEARCH RESULTS: {vector_results}\nCONVERSATION HISTORY: {history}"}
        ]
    )
    return response.choices[0].message.content


# Resources
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
                upload_and_process_pack(pack_id, access_token)  # Pass the token to the function

            # Check if the `my_deeplake` folder exists for the pack
            folder_path = os.path.join("my_deeplake", str(pack_id))

            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                logging.info("The my_deeplake folder exists for pack_id: %s", pack_id)
            else:
                logging.info("The my_deeplake folder does not exist. Running project_to_vector.")
                project_to_vector(folder_path)  # Use folder path instead of session_id

            # Perform vector query if a pack_id is provided
            if pack_id:
                logging.info("Performing vector query with user_message: %s", user_message)
                # Initialize the embedding function
                embedding_function = CustomEmbeddingFunction(client)
                db = DeepLake(dataset_path=folder_path, embedding=embedding_function, read_only=True)
                vector_results = perform_query(db, user_message)
                logging.info("Vector query results: %s", vector_results)
            else:
                vector_results = None

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

class DeleteSession(Resource):
    def delete(self):
        if 'session_id' not in session:
            return {"message": "No session started"}, 400

        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session['session_id'])
        if os.path.exists(session_folder):
            shutil.rmtree(session_folder)
            session.pop('session_id', None)
            logging.info("Session and all associated files deleted successfully")
            return {"message": "Session and all associated files deleted successfully"}, 200
        else:
            logging.info("No files found for session_id: %s", session['session_id'])
            return {"message": "No files found for this session"}, 404

# Flask-RESTful Resource routing
api.add_resource(DeepQueryCode, '/deepquery-code')
api.add_resource(Login, '/login')
api.add_resource(DeleteSession, '/delete-session')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)

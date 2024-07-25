from flask import Flask, request, jsonify, session
import os, shutil
import openai
from transformers import pipeline
import openpyxl
from dotenv import load_dotenv
from uuid import uuid4
import process_files as pf

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')  # Replace with a real secret key
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure the upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Upload file for RAG
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    
    if file:
        if 'session_id' not in session:
            session['session_id'] = str(uuid4())
        
        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session['session_id'])
        os.makedirs(session_folder, exist_ok=True)
        
        filename = file.filename
        filepath = os.path.join(session_folder, filename)
        file.save(filepath)
        
        # Process files and save embeddings
        pf.process_and_save_embeddings(session_folder)
        
        return jsonify({'message': 'File uploaded successfully', 'filename': filename}), 201

# Retrieve uploaded files for RAG in user session
@app.route('/retrieve-files', methods=['GET'])
def retrieve_files():
    if 'session_id' not in session:
        return jsonify({'message': 'No session started'}), 400
    
    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session['session_id'])
    if not os.path.exists(session_folder):
        return jsonify({'message': 'No files found for this session'}), 404
    
    files = os.listdir(session_folder)
    if not files:
        return jsonify({'message': 'No files found in the session folder'}), 404
    
    file_list = [{'filename': file} for file in files if file != 'embeddings.npy']
    return jsonify({'files': file_list})


# GPT RAG response 
@app.route('/gpt-response', methods=['POST'])
def gpt_response():
    data = request.json
    user_message = data.get('user_message')

    if 'session_id' not in session:
        return jsonify({'message': 'No session started'}), 400
    
    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session['session_id'])
    embeddings_file = os.path.join(session_folder, 'embeddings.npy')
    if not os.path.exists(embeddings_file):
        return jsonify({'message': 'No embeddings found for this session'}), 404
    
    embeddings = pf.load_embeddings(embeddings_file)
    relevant_files = pf.query_embeddings(embeddings, user_message)

    # Get the content of the most relevant file
    if relevant_files:
        top_file = relevant_files[0]
        top_content = pf.read_file(top_file)
        print(f"Top file content: {top_content}")  # Debug statement
    else:
        top_content = "No relevant documents found."

    client = openai.OpenAI(
        api_key=os.getenv('OPENAI_API_KEY')
    )

    chat_completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": f"You are to answer all Queries using the provided context"
            },
            {
                "role": "user",
                "content": f"Query: {user_message}\n Context: {top_content}",
            }
        ]
    )

    assistant_message = chat_completion.choices[0].message.content
    print(f"Assistant message: {assistant_message}")  # Debug statement
    return jsonify({"message": assistant_message})



#sentiment analysis pipeline
def sentiment_analysis(text: str) -> str:
    model_name = "distilbert-base-uncased-finetuned-sst-2-english"
    classifier = pipeline("sentiment-analysis", model=model_name)
    result = classifier(text)
    return result[0]

#!sentiment analysis route
@app.route('/sentiment-pipe', methods=['POST'])
def sentiment_pipe():
    data = request.json
    user_message = data.get('user_message')

    result = sentiment_analysis(user_message)
    return jsonify({"message": result})





# Delete session and all associated files
@app.route('/delete-session', methods=['DELETE'])
def delete_session():
    if 'session_id' not in session:
        return jsonify({'message': 'No session started'}), 400
    
    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session['session_id'])
    if os.path.exists(session_folder):
        shutil.rmtree(session_folder)
        session.pop('session_id', None)
        return jsonify({'message': 'Session and all associated files deleted successfully'}), 200
    else:
        return jsonify({'message': 'No files found for this session'}), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"Binding to port {port}")
    app.run(host='0.0.0.0', port=port)


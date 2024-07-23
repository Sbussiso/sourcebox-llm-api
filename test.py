import requests

# Initialize the session
session = requests.Session()

# Define the base URL
#base_url = 'http://127.0.0.1:8000'
base_url = 'https://sb-general-llm-api-1d86f3b698a2.herokuapp.com'

# 1. Upload the file
upload_url = f'{base_url}/upload'
file_path = '/workspaces/python-10/test/example.csv'

with open(file_path, 'rb') as f:
    files = {'file': f}
    response = session.post(upload_url, files=files)
    print("Upload response:", response.json())

# 2. Retrieve the list of uploaded files
retrieve_files_url = f'{base_url}/retrieve-files'
response = session.get(retrieve_files_url)
print("Retrieve files response:", response.json())

# 3. Get GPT-3 response
gpt_response_url = f'{base_url}/gpt-response'
data = {'user_message': 'Explain the content of the uploaded file'}
response = session.post(gpt_response_url, json=data)
print("GPT response:", response.json())

# 4. Delete the session and all associated files
delete_session_url = f'{base_url}/delete-session'
response = session.delete(delete_session_url)
print("Delete session response:", response.json())

# 5. Test the sentiment analysis pipeline
sentiment_pipe_url = f'{base_url}/sentiment-pipe'
data = {'user_message': 'I love this product!'}
response = session.post(sentiment_pipe_url, json=data)
print("Sentiment analysis response:", response.json())

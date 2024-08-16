import requests
import os, sys

# Initialize the session
session = requests.Session()

# Define the base URLs
base_url = 'http://127.0.0.1:8000'
auth_base_url = 'https://sourcebox-central-auth-8396932a641c.herokuapp.com'  # Replace with your external auth API URL

# 1. Log in the user and obtain the access token
login_url = f'{auth_base_url}/login'
login_data = {
    'email': 'sbussiso321@gmail.com',  # Replace with actual credentials
    'password': 'Sbu1234567'
}

login_response = session.post(login_url, json=login_data)
login_data = login_response.json()

if login_response.status_code != 200:
    print(f"Login failed: {login_data}")
    exit(1)

access_token = login_data.get('access_token')
session.headers.update({'Authorization': f'Bearer {access_token}'})
print("Login successful")

# 2. Start a new session to obtain the session_id
start_session_url = f'{base_url}/start-session'
start_session_response = session.post(start_session_url)
session_data = start_session_response.json()

if start_session_response.status_code != 200:
    print(f"Failed to start session: {session_data}")
    exit(1)

session_id = session_data.get('session_id')
if not session_id:
    print("Session ID not found")
    exit(1)

print(f"Session started with ID: {session_id}")

# 3. List the user's code packs and get the first code pack ID
list_code_packs_url = f'{auth_base_url}/packman/code/list_code_packs'
list_response = session.get(list_code_packs_url)

if list_response.status_code != 200:
    print(f"Failed to retrieve code packs: {list_response.text}")
    exit(1)

code_packs = list_response.json()
if not code_packs:
    print("No code packs found")
    exit(1)

first_code_pack = code_packs[0]
first_code_pack_id = first_code_pack.get('id')
print(f"First code pack ID: {first_code_pack_id}")

# 4. Retrieve the contents of the first code pack using the GetCodePackById route
get_code_pack_url = f'{auth_base_url}/packman/code/details/{first_code_pack_id}'
pack_response = session.get(get_code_pack_url)

if pack_response.status_code != 200:
    print(f"Failed to retrieve code pack details: {pack_response.text}")
    exit(1)

pack_data = pack_response.json()
contents = pack_data.get('contents', [])

# 5. Save the pack contents to the uploads folder using session ID
upload_folder = f'uploads/{session_id}'
os.makedirs(upload_folder, exist_ok=True)

for content in contents:
    filename = content.get('filename')
    file_content = content.get('content')

    if filename and file_content:
        file_path = os.path.join(upload_folder, filename)
        try:
            # Ensure that file content is handled correctly (assuming content is text)
            with open(file_path, 'w') as f:
                f.write(file_content)  # Write the actual content, not the filename
            print(f"Saved {filename} to {file_path}")
        except Exception as e:
            print(f"Failed to save {filename}: {e}")
    else:
        print(f"Invalid content or filename: {content}")

# 6. Perform the deep query with the first code pack ID
deep_query_url = f'{base_url}/deepquery-code'
deepquery_payload = {
    'user_message': 'What is the status of my project?',
    'pack_id': first_code_pack_id  # Use the first code pack ID
}

response = session.post(deep_query_url, json=deepquery_payload)

# Check if the response was successful and print the result
if response.status_code == 200:
    try:
        deepquery_response = response.json()
        print("DeepQuery code response:", deepquery_response)
    except ValueError:
        print("Response content is not valid JSON:", response.text)
else:
    print(f"DeepQuery failed with status code {response.status_code}: {response.text}")

sys.exit()


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
#delete_session_url = f'{base_url}/delete-session'
#response = session.delete(delete_session_url)
#print("Delete session response:", response.json())

# 5. Test the sentiment analysis pipeline
sentiment_pipe_url = f'{base_url}/sentiment-pipe'
data = {'user_message': 'I love this product!'}
response = session.post(sentiment_pipe_url, json=data)
print("Sentiment analysis response:", response.json())


# 6. Test DeepQuery code response
deep_query_url = f'{base_url}/deepquery-code'

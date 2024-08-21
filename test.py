import requests

# Base URL for the Flask API
base_url = 'http://127.0.0.1:8000'

# Initialize a session object to maintain the session state across requests
session = requests.Session()

# Global variable to store the access token
access_token = None

# Log in the user and obtain the access token
def login():
    global access_token
    login_url = f'{base_url}/login'
    payload = {
        'email': 'sbussiso321@gmail.com',  # Use actual credentials
        'password': 'Sbu1234567'  # Use actual credentials
    }
    
    response = session.post(login_url, json=payload)
    if response.status_code == 200:
        print("Login successful!")
        access_token = response.json().get('access_token')
        if not access_token:
            print("Error: Access token not found.")
    else:
        print("Login failed:", response.text)

# Test DeepQueryCode with user_message only
def test_deepquery_code_message():
    if not access_token:
        print("Error: No access token available.")
        return

    url = f'{base_url}/deepquery-code'
    payload = {
        'user_message': 'What is the meaning of life?',
        'history': 'Previous conversation: What is AI?',
        'pack_id': '1'  # Assuming pack ID 1
    }

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = session.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Response Data:", response.json())
    else:
        print("Error:", response.text)

# Test DeepQueryCode with pack data
def test_deepquery_code_with_pack():
    if not access_token:
        print("Error: No access token available.")
        return

    url = f'{base_url}/deepquery-code'
    payload = {
        'user_message': 'Where is the database being used?',
        'history': 'Previous conversation: User requested code analysis before.',
        'pack_id': '1'  # Use a valid pack ID
    }

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = session.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Response Data:", response.json())
    else:
        print("Error:", response.text)

# Test DeleteSession endpoint
def test_delete_session():
    if not access_token:
        print("Error: No access token available.")
        return

    url = f'{base_url}/delete-session'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = session.delete(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Response Data:", response.json())
    else:
        print("Error:", response.text)

if __name__ == '__main__':
    # Log in and obtain the access token
    login()

    if access_token:
        print("\nTesting /deepquery-code with user_message only...")
        test_deepquery_code_message()

        print("\nTesting /deepquery-code with pack data...")
        test_deepquery_code_with_pack()

        #print("\nTesting /delete-session...")
        #test_delete_session()
    else:
        print("No access token retrieved. Exiting...")

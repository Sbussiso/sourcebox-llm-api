import requests

# Base URL for the Flask API
base_url = 'http://127.0.0.1:8000'  # Replace with the actual base URL of your Flask application

# Initialize a session object to maintain the session state across multiple requests
session = requests.Session()

# Global variable to store the access token once the user is logged in
access_token = None

# Log in the user and obtain the access token for future requests
def login():
    global access_token  # Access the global variable to store the token
    login_url = f'{base_url}/login'

    payload = {
        'email': 'sbussiso321@gmail.com',  # Replace with actual email
        'password': 'Sbu1234567'  # Replace with actual password
    }
    
    response = session.post(login_url, json=payload)
    if response.status_code == 200:
        print("Login successful!")
        access_token = response.json().get('access_token')
        if not access_token:
            print("Error: Access token not found.")
    else:
        print("Login failed:", response.text)

# Test the /deepquery-code endpoint with and without pack_id
def test_deepquery_code(user_message, pack_id=None):
    if not access_token:
        print("Error: No access token available.")
        return

    url = f'{base_url}/deepquery-code'
    payload = {
        'user_message': user_message,
        'pack_id': pack_id,
        'history': 'User message history'
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

# Test the /deepquery endpoint with and without pack_id
def test_deepquery(user_message, pack_id=None):
    if not access_token:
        print("Error: No access token available.")
        return

    url = f'{base_url}/deepquery'
    payload = {
        'user_message': user_message,
        'pack_id': pack_id,
        'history': 'User message history'
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

# Test the /deepquery-code-raw endpoint
def test_deepquery_code_raw(user_message, pack_id=None):
    if not access_token:
        print("Error: No access token available.")
        return

    url = f'{base_url}/deepquery-code-raw'
    payload = {
        'user_message': user_message,
        'pack_id': pack_id
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

# Test the /deepquery-raw endpoint
def test_deepquery_raw(user_message, pack_id=None):
    if not access_token:
        print("Error: No access token available.")
        return

    url = f'{base_url}/deepquery-raw'
    payload = {
        'user_message': user_message,
        'pack_id': pack_id
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

# Test /delete-session endpoint
def test_delete_session(user_id):
    if not access_token:
        print("Error: No access token available.")
        return

    url = f'{base_url}/delete-session'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    payload = {'user_id': user_id}
    response = session.delete(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Response Data:", response.json())
    else:
        print("Error:", response.text)

# Main execution block
if __name__ == '__main__':
    login()

    if access_token:
        # Test deepquery-code with and without pack_id
        user_message = input("Enter user message for deepquery-code: ")
        pack_id = input("Enter pack ID for deepquery-code (optional): ")
        print("\nTesting /deepquery-code with user_message and pack_id...")
        test_deepquery_code(user_message, pack_id)
        print("\nTesting /deepquery-code without pack_id...")
        test_deepquery_code(user_message)

        # Test deepquery with and without pack_id
        user_message = input("Enter user message for deepquery: ")
        pack_id = input("Enter pack ID for deepquery (optional): ")
        print("\nTesting /deepquery with user_message and pack_id...")
        test_deepquery(user_message, pack_id)
        print("\nTesting /deepquery without pack_id...")
        test_deepquery(user_message)

        # Test deepquery-code-raw with and without pack_id
        user_message = input("Enter user message for deepquery-code-raw: ")
        pack_id = input("Enter pack ID for deepquery-code-raw (optional): ")
        print("\nTesting /deepquery-code-raw with user_message and pack_id...")
        test_deepquery_code_raw(user_message, pack_id)
        print("\nTesting /deepquery-code-raw without pack_id...")
        test_deepquery_code_raw(user_message)

        # Test deepquery-raw with and without pack_id
        user_message = input("Enter user message for deepquery-raw: ")
        pack_id = input("Enter pack ID for deepquery-raw (optional): ")
        print("\nTesting /deepquery-raw with user_message and pack_id...")
        test_deepquery_raw(user_message, pack_id)
        print("\nTesting /deepquery-raw without pack_id...")
        test_deepquery_raw(user_message)

        # Test /delete-session
        user_id = input("Enter user ID to delete session: ")
        print("\nTesting /delete-session...")
        test_delete_session(user_id)
    else:
        print("No access token retrieved. Exiting...")

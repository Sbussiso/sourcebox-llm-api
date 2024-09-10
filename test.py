import requests

# Base URL for the Flask API
base_url = 'http://127.0.0.1:8000'  # Replace with the actual base URL of your Flask application

# Initialize a session object to maintain the session state across multiple requests
session = requests.Session()

# Global variable to store the access token once the user is logged in
access_token = None

# Log in the user and obtain the access token for future requests
def login():
    """
    Authenticates the user by sending a login request to the server and retrieves an access token.
    
    This function sends the user's email and password to the login endpoint.
    If the login is successful, the access token is stored globally for use in subsequent API requests.
    """
    global access_token  # Access the global variable to store the token
    login_url = f'{base_url}/login'  # Login endpoint

    # Payload containing the user's credentials. Replace these values with actual credentials for production.
    payload = {
        'email': 'sbussiso321@gmail.com',  # Replace with the actual email
        'password': 'Sbu1234567'  # Replace with the actual password
    }
    
    # Send a POST request to the login endpoint with the user's credentials
    response = session.post(login_url, json=payload)
    
    # Check if the login was successful by inspecting the status code
    if response.status_code == 200:
        print("Login successful!")
        access_token = response.json().get('access_token')  # Extract the access token from the response
        if not access_token:
            print("Error: Access token not found.")
    else:
        print("Login failed:", response.text)  # Print the error message if login failed

# Test DeepQueryCodeRaw with dynamic user_message and pack_id
def test_deepquery_code_raw_message(user_message, pack_id):
    """
    Sends a request to the /deepquery-code-raw endpoint with a user-provided message and pack ID.

    Args:
        user_message (str): The user's query message.
        pack_id (str): The ID of the pack to be queried.
    """
    if not access_token:
        print("Error: No access token available.")
        return

    # Construct the URL for the deepquery-code-raw endpoint
    url = f'{base_url}/deepquery-code-raw'
    
    # Prepare the payload with the user's message and pack ID
    payload = {
        'user_message': user_message,
        'pack_id': pack_id
    }

    # Set the headers with the access token for authentication
    headers = {
        'Authorization': f'Bearer {access_token}',  # Bearer token for authentication
        'Content-Type': 'application/json'  # Specify that the content type is JSON
    }

    # Send the POST request to the API
    response = session.post(url, json=payload, headers=headers)
    
    # Print the status code and the response data (or error) based on the API's response
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Response Data:", response.json())
    else:
        print("Error:", response.text)

# Test DeepQueryRaw with dynamic user_message and pack_id
def test_deepquery_raw_message(user_message, pack_id):
    """
    Sends a request to the /deepquery-raw endpoint with a user-provided message and pack ID.

    Args:
        user_message (str): The user's query message.
        pack_id (str): The ID of the pack to be queried.
    """
    if not access_token:
        print("Error: No access token available.")
        return

    # Construct the URL for the deepquery-raw endpoint
    url = f'{base_url}/deepquery-raw'
    
    # Prepare the payload with the user's message and pack ID
    payload = {
        'user_message': user_message,
        'pack_id': pack_id
    }

    # Set the headers with the access token for authentication
    headers = {
        'Authorization': f'Bearer {access_token}',  # Bearer token for authentication
        'Content-Type': 'application/json'  # Specify that the content type is JSON
    }

    # Send the POST request to the API
    response = session.post(url, json=payload, headers=headers)
    
    # Print the status code and the response data (or error) based on the API's response
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Response Data:", response.json())
    else:
        print("Error:", response.text)

# Test DeepQueryCodeRaw with dynamic user_message and pack_id (assuming this tests code-related pack)
def test_deepquery_code_raw_with_pack(user_message, pack_id):
    """
    Sends a request to the /deepquery-code-raw endpoint with a user-provided message and pack ID, 
    specifically for analyzing code-related packs.

    Args:
        user_message (str): The user's query message.
        pack_id (str): The ID of the pack to be queried.
    """
    if not access_token:
        print("Error: No access token available.")
        return

    # Construct the URL for the deepquery-code-raw endpoint
    url = f'{base_url}/deepquery-code-raw'
    
    # Prepare the payload with the user's message and pack ID
    payload = {
        'user_message': user_message,
        'pack_id': pack_id
    }

    # Set the headers with the access token for authentication
    headers = {
        'Authorization': f'Bearer {access_token}',  # Bearer token for authentication
        'Content-Type': 'application/json'  # Specify that the content type is JSON
    }

    # Send the POST request to the API
    response = session.post(url, json=payload, headers=headers)
    
    # Print the status code and the response data (or error) based on the API's response
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Response Data:", response.json())
    else:
        print("Error:", response.text)

# Test DeepQueryRaw with dynamic user_message and pack_id (assuming this tests data-related pack)
def test_deepquery_raw_with_pack(user_message, pack_id):
    """
    Sends a request to the /deepquery-raw endpoint with a user-provided message and pack ID, 
    specifically for analyzing data-related packs.

    Args:
        user_message (str): The user's query message.
        pack_id (str): The ID of the pack to be queried.
    """
    if not access_token:
        print("Error: No access token available.")
        return

    # Construct the URL for the deepquery-raw endpoint
    url = f'{base_url}/deepquery-raw'
    
    # Prepare the payload with the user's message and pack ID
    payload = {
        'user_message': user_message,
        'pack_id': pack_id
    }

    # Set the headers with the access token for authentication
    headers = {
        'Authorization': f'Bearer {access_token}',  # Bearer token for authentication
        'Content-Type': 'application/json'  # Specify that the content type is JSON
    }

    # Send the POST request to the API
    response = session.post(url, json=payload, headers=headers)
    
    # Print the status code and the response data (or error) based on the API's response
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Response Data:", response.json())
    else:
        print("Error:", response.text)

# Test DeleteSession endpoint
def test_delete_session():
    """
    Sends a request to the /delete-session endpoint to terminate the user's session.

    This function is used to test the session deletion functionality by sending a DELETE request.
    """
    if not access_token:
        print("Error: No access token available.")
        return

    # Construct the URL for the delete-session endpoint
    url = f'{base_url}/delete-session'

    # Set the headers with the access token for authentication
    headers = {
        'Authorization': f'Bearer {access_token}',  # Bearer token for authentication
        'Content-Type': 'application/json'  # Specify that the content type is JSON
    }

    # Send the DELETE request to the API
    response = session.delete(url, headers=headers)
    
    # Print the status code and the response data (or error) based on the API's response
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Response Data:", response.json())
    else:
        print("Error:", response.text)

# Main execution block
if __name__ == '__main__':
    # Log in and obtain the access token
    login()

    if access_token:
        # Separate inputs for deepquery-code tests
        user_message_code = input("Enter user message for deepquery-code: ")
        pack_id_code = input("Enter pack ID for deepquery-code: ")

        # deepquery-code tests
        print("\nTesting /deepquery-code-raw with user_message only...")
        test_deepquery_code_raw_message(user_message_code, pack_id_code)
        print("\n\n")

        print("\nTesting /deepquery-code-raw with pack data...")
        test_deepquery_code_raw_with_pack(user_message_code, pack_id_code)
        print("\n\n\n")


        # Separate inputs for deepquery tests
        user_message_data = input("Enter user message for deepquery: ")
        pack_id_data = input("Enter pack ID for deepquery: ")

        # deepquery tests
        print("\nTesting /deepquery-raw with user_message only...")
        test_deepquery_raw_message(user_message_data, pack_id_data)
        print("\n\n")


        print("\nTesting /deepquery-raw with pack data...")
        test_deepquery_raw_with_pack(user_message_data, pack_id_data)
        print("\n\n")


        # Uncomment this to test session deletion
        # print("\nTesting /delete-session...")
        # test_delete_session()
    else:
        print("No access token retrieved. Exiting...")

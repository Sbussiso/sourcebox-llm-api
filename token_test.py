import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Base URL of your API (make sure AUTH_API is set in the environment or you can hardcode it here)
AUTH_API = os.getenv('AUTH_API')
print(AUTH_API)

def login_and_get_token(email, password):
    """Logs in the user and returns the access token."""
    login_url = f'{AUTH_API}/login'
    payload = {'email': email, 'password': password}

    try:
        response = requests.post(login_url, json=payload)
        if response.status_code == 200:
            access_token = response.json().get('access_token')
            print(f"Login successful. Access token: {access_token}")
            return access_token
        else:
            print(f"Login failed. Status code: {response.status_code}, Response: {response.text}")
            return None
    except requests.RequestException as e:
        print(f"Error logging in: {e}")
        return None

def get_token_count(access_token):
    """Fetches the current token count for the user."""
    token_count_url = f'{AUTH_API}/user/token_usage'
    headers = {'Authorization': f'Bearer {access_token}'}

    try:
        response = requests.get(token_count_url, headers=headers)
        if response.status_code == 200:
            token_data = response.json()
            print(f"Current token count: {token_data.get('total_tokens')}")
        else:
            print(f"Failed to get token count. Status code: {response.status_code}, Response: {response.text}")
    except requests.RequestException as e:
        print(f"Error fetching token count: {e}")

if __name__ == '__main__':
    # Replace with your test email and password
    email = 'sbussiso321@gmail.com'
    password = 'Sbu1234567'

    # Step 1: Login and get the access token
    access_token = login_and_get_token(email, password)

    # Step 2: If login was successful, fetch the current token count
    if access_token:
        get_token_count(access_token)

import requests
import json

# Define the URL of the sentiment analysis API
url = 'http://localhost:8000/landing-sentiment-example'

# Define the payload with the prompt
payload = {
    "prompt": "The service was excellent, and I had a great experience!"
}

# Define headers for JSON content
headers = {
    'Content-Type': 'application/json'
}

# Make the POST request to the sentiment analysis API
response = requests.post(url, headers=headers, data=json.dumps(payload))

# Print the status code and the response content
print("Status Code:", response.status_code)
print("Response Content:", response.json())

# Test without a prompt to check error handling
print("\nTesting with missing prompt...")
response = requests.post(url, headers=headers, data=json.dumps({"prompt": ""}))
print("Status Code:", response.status_code)
print("Response Content:", response.json())

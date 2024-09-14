import requests
import json

# Define the URL for the local API endpoint you want to test
url = 'http://localhost:8000/landing-webscrape-example'

# Define the payload with the prompt to send to the API
payload = {
    "prompt": "Analyze the sentiment of the following reviews for this product."
}

# Set the headers to send JSON content
headers = {
    'Content-Type': 'application/json'
}

# Make the POST request to the API with the prompt
response = requests.post(url, headers=headers, data=json.dumps(payload))

# Print the status code and the response content from the API
print("Status Code:", response.status_code)
print("Response Content:", response.json())


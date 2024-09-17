import requests
import json

# Define the URL for the local API endpoint for image generation
url = 'http://localhost:8000/landing-imagegen-example'

# Define the payload with the prompt to generate an image
payload = {
    "prompt": "A futuristic city skyline at sunset with flying cars"
}

# Set the headers to send JSON content
headers = {
    'Content-Type': 'application/json'
}

# Make the POST request to the API with the image generation prompt
response = requests.post(url, headers=headers, data=json.dumps(payload))

# Print the status code and the response content from the API
print("Status Code:", response.status_code)
print("Response Content:", response.json())

# Test with another prompt
print("\nTesting with another prompt...")
payload = {
    "prompt": "A fantasy dragon flying over a mountain range"
}

response = requests.post(url, headers=headers, data=json.dumps(payload))
print("Status Code:", response.status_code)
print("Response Content:", response.json())

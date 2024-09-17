import requests
import os

# Define the URL for the local API endpoint you want to test
url = 'http://localhost:8000/landing-transcript-example'

# Function to simulate a GET request to the transcription resource
def test_transcription():
    try:
        # Send the GET request to the API
        response = requests.get(url)

        # Check the response status code
        if response.status_code == 200:
            # Print the transcription result
            print("Transcription Result:", response.json())
        else:
            # Print error details
            print(f"Error: {response.status_code}, {response.json()}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Run the test
if __name__ == "__main__":
    test_transcription()

## SourceBox LLM API

<br/>
<br/>

> The SourceBox LLM API provides a powerful platform for managing, querying, and analyzing a wide variety of data and code packs using AI-based techniques. It allows users to upload structured data or code repositories, process them into vector embeddings, and perform in-depth queries using natural language or raw search modes. The platform leverages state-of-the-art tools such as OpenAI's GPT models, DeepLake for vector storage, and custom embeddings to support both document search and advanced code analysis.

<br/>
<br/>

### AI Chatbot Integration

> Query your processed data packs using natural language and interact with a chatbot for context-specific responses.

<br/>

### Vector Search and Analysis

> Perform vector-based similarity searches on uploaded content using deep learning models.

<br/>

### Retrieval Augmented Generation with PackMan

> Upload, and process different types of data packs, including CSV files, text documents, code repositories, and more.

<br/>

### Token Usage Tracking

> Monitor and limit token usage to manage costs and prevent overuse.

<br/>
<br/>
<br/>
<br/>

# Installation

### Clone the Repository
```
git clone https://github.com/Sbussiso/sourcebox-llm-api.git
cd sourcebox-llm-api
```

<br/>

### Set Up a Virtual Environment
```
python3 -m venv venv
source venv/bin/activate   # On Windows, use `venv\Scripts\activate`
```

<br/>

### Install Dependencies
```
pip install -r requirements.txt
```

<br/>

### Running Application
```
flask run
```
### or
```
flask run --port=8000
```

<br/>
<br/>
<br/>
<br/>

## API Endpoints

The SourceBox LLM API exposes several RESTful endpoints for interacting with your data and executing code analysis.

<br/>

### Login

- Endpoint: /login
- Description: Authenticates the user and retrieves an access token.
- Method: POST

Payload Example:
```
{
  "email": "user@example.com",
  "password": "password123"
}
```

<br/>

### DeepQuery

- Endpoint: /deepquery
- Description: Used for querying general data packs with an AI chatbot.
- Method: POST

Payload Example:
```
{
  "user_message": "Summarize the key findings",
  "pack_id": "1",
  "history": ""
}
```

<br/>

### DeepQuery Code

- Endpoint: /deepquery-code
- Description: Used for querying code packs, providing context-based responses for code repositories.
- Method: POST
  
Payload Example:
```
{
  "user_message": "Explain the purpose of this function.",
  "pack_id": "6",
  "history": ""
}
```
<br/>

### Delete Session

- Endpoint: /delete-session
- Description: Deletes user sessions and associated files.
- Method: DELETE

Payload Example:
```
{
  "user_id": "user123"
}
```

<br/>


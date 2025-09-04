import os
from dotenv import load_dotenv
import requests

load_dotenv()

# Test if API key is loaded
api_key = os.getenv('GROQ_API_KEY')
print(f"API Key loaded: {'Yes' if api_key else 'No'}")
if api_key:
    print(f"API Key starts with: {api_key[:10]}...")

# Test direct API call
if api_key:
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'llama3-8b-8192',
        'messages': [{'role': 'user', 'content': 'Hello'}],
        'max_tokens': 10
    }
    
    try:
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=10
        )
        print(f"API Response Status: {response.status_code}")
        print(f"API Response: {response.text[:200]}...")
    except Exception as e:
        print(f"API Test Error: {e}")

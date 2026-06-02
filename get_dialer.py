import os
import requests
from dotenv import load_dotenv

# Load the environment variables from the local .env file
load_dotenv()

# Fetch the URL dynamically; fall back to None if it isn't set
API_URL = os.getenv("DIALER_API_URL")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Referer": "https://clientdialer.callengine.org/",
}

def fetch_dialer_data():
    if not API_URL:
        print("[-] Error: DIALER_API_URL is not set in the environment.")
        return []
        
    try:
        print(f"Sending GET request to secure API endpoint...")
        response = requests.get(API_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []
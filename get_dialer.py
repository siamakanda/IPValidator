import json
import requests

API_URL = "https://clientdialer.callengine.org/api/dialers"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://clientdialer.callengine.org/",
}


def fetch_dialer_data():
    try:
        print(f"Sending GET request to {API_URL}...")
        response = requests.get(API_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()

        dialer_data = response.json()
        print(f"Success! Retrieved {len(dialer_data)} dialer configurations.\n")

        # --- THIS IS THE PART WE MODIFIED ---
        # Return the data so validator.py can read it
        return dialer_data

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []  # Return an empty list if it fails


if __name__ == "__main__":
    fetch_dialer_data()
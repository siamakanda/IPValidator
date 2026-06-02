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
        
        # --- VALIDATION: ensure it's a list and each item has required fields ---
        if not isinstance(dialer_data, list):
            print(f"[-] API did not return a list. Got {type(dialer_data)}. Aborting.")
            return []
        
        required_keys = {"dialer_url", "admin_username", "admin_password"}
        valid_dialers = []
        for idx, dialer in enumerate(dialer_data):
            if not isinstance(dialer, dict):
                print(f"[-] Item {idx} is not a dictionary, skipping.")
                continue
            missing = required_keys - dialer.keys()
            if missing:
                print(f"[-] Dialer {idx} missing keys {missing}, skipping.")
                continue
            valid_dialers.append(dialer)
        
        print(f"Success! Retrieved {len(valid_dialers)} valid dialer configurations out of {len(dialer_data)} total.")
        return valid_dialers

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []


if __name__ == "__main__":
    fetch_dialer_data()
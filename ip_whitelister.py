import sys
import time
from urllib.parse import urlparse, urlunparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
import urllib3

# Disable SSL warnings (since we are using verify=False)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= CONFIGURATION =================
API_URL = "https://clientdialer.callengine.org/api/dialers"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://clientdialer.callengine.org/",
}
MAX_WORKERS = 12
REQUEST_TIMEOUT = 15
RETRY_TRIES = 2
RETRY_DELAY = 1
# =================================================


def fetch_dialer_data():
    """Fetch and validate dialer configurations from API."""
    try:
        print(f"Sending GET request to {API_URL}...")
        # IMPORTANT: verify=False disables SSL certificate checking
        response = requests.get(API_URL, headers=HEADERS, timeout=10, verify=False)
        response.raise_for_status()

        dialer_data = response.json()

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


def build_validation_url(dialer_url: str) -> str:
    """Construct the correct valid8.php URL using proper port/scheme logic."""
    base = dialer_url.rstrip('/')
    parsed = urlparse(base)

    if "callengine.org" in parsed.netloc:
        current_port = parsed.port
        if current_port not in (446, 81):
            netloc = parsed.hostname + ":446"
            parsed = parsed._replace(scheme="https", netloc=netloc)

    validation_path = "/valid8.php"
    return urlunparse(parsed) + validation_path


def retry_request(func, *args, **kwargs):
    """Simple retry decorator for network calls."""
    # Force verify=False for all requests
    kwargs['verify'] = False
    last_exception = None
    for attempt in range(RETRY_TRIES + 1):
        try:
            return func(*args, **kwargs)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_exception = e
            if attempt < RETRY_TRIES:
                time.sleep(RETRY_DELAY)
                continue
            raise
    raise last_exception


def validate_ip_on_server(dialer_url, username, password, name):
    validation_url = build_validation_url(dialer_url)

    with requests.Session() as session:
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        session.verify = False  # Disable SSL verification for this session

        try:
            get_response = retry_request(session.get, validation_url, timeout=REQUEST_TIMEOUT)
            get_response.raise_for_status()

            soup = BeautifulSoup(get_response.text, "html.parser")
            form = soup.find("form")
            if not form:
                return f"[-] {name}: No authentication form found."

            text_input = form.find("input", {"type": "text"})
            pass_input = form.find("input", {"type": "password"})
            if not text_input or not pass_input:
                return f"[-] {name}: Could not identify login fields."

            user_field_name = text_input.get("name")
            pass_field_name = pass_input.get("name")

            payload = {
                user_field_name: username,
                pass_field_name: password,
                "submit": "Submit",
            }

            post_response = retry_request(session.post, validation_url, data=payload, timeout=REQUEST_TIMEOUT)

            if "Login Validated" in post_response.text or "Redirecting" in post_response.text:
                return f"[+] {name}: Successfully whitelisted!"
            else:
                return f"[-] {name}: Validation failed or response changed."

        except requests.exceptions.Timeout:
            return f"[-] {name}: Connection timed out after retries (Server offline?)"
        except requests.exceptions.HTTPError as http_err:
            return f"[-] {name}: HTTP Error {http_err.response.status_code}"
        except Exception as e:
            return f"[-] {name}: Connection error: {e}"


def main():
    dialers = fetch_dialer_data()
    if not dialers:
        print("[-] No valid dialer data collected. Exiting.")
        input("Press Enter to exit...")
        return

    print(f"[*] Starting parallel IP validation across {len(dialers)} hosts using {MAX_WORKERS} threads...\n")

    success_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for dialer in dialers:
            url = dialer.get("dialer_url")
            user = dialer.get("admin_username")
            pwd = dialer.get("admin_password")
            name = dialer.get("name", "Unknown Dialer")
            future = executor.submit(validate_ip_on_server, url, user, pwd, name)
            futures[future] = name

        for future in as_completed(futures):
            result_message = future.result()
            print(result_message)
            if "[+]" in result_message:
                success_count += 1
            else:
                fail_count += 1

    print(f"\n[+] Validation loop complete. Success: {success_count} | Failed/Skipped: {fail_count}")
    input("Press Enter to exit...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[-] Process interrupted by user. Exiting safely.")
        sys.exit(0)
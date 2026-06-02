import sys
import time
from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup
import requests
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed

from get_dialer import fetch_dialer_data

# Suppress SSL warnings only if you re-enable verify=False – we have enabled verification,
# so we no longer need to disable warnings. Remove the next line.
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MAX_WORKERS = 12
REQUEST_TIMEOUT = 15          # seconds
RETRY_TRIES = 2               # extra attempts after first failure
RETRY_DELAY = 1               # seconds between retries


def build_validation_url(dialer_url: str) -> str:
    """Construct the correct valid8.php URL using proper port/scheme logic."""
    base = dialer_url.rstrip('/')
    parsed = urlparse(base)
    
    # If domain contains "callengine.org" and no explicit port is set to 446 or 81,
    # force HTTPS and port 446.
    if "callengine.org" in parsed.netloc:
        # Get current port (None means default for scheme)
        current_port = parsed.port
        if current_port not in (446, 81):
            # Replace scheme with https and set port to 446
            netloc = parsed.hostname + ":446"
            parsed = parsed._replace(scheme="https", netloc=netloc)
    # For all other domains, keep scheme as is, append /valid8.php
    validation_path = "/valid8.php"
    return urlunparse(parsed) + validation_path


def retry_request(func, *args, **kwargs):
    """Simple retry decorator for network calls."""
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
    
    # Use a session inside a context manager
    with requests.Session() as session:
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        # No verify=False – SSL verification is now enabled
        
        try:
            # Fetch form – with retry
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
            
            # Submit credentials – with retry
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
            # All required keys are guaranteed by validation in fetch_dialer_data()
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


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[-] Process interrupted by user. Exiting safely.")
        sys.exit(0)
import sys
from bs4 import BeautifulSoup
import requests
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import the function from your get_dialer.py file
from get_dialer import fetch_dialer_data

# Suppress SSL warnings since we are using verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Max number of parallel connections. 10-15 is a sweet spot for network tasks.
MAX_WORKERS = 12 

def validate_ip_on_server(dialer_url, username, password, name):
    base_url = dialer_url.rstrip("/")

    # Handle HTTP vs HTTPS scheme adjustments cleanly
    if ".callengine.org" in base_url and not (base_url.endswith(":446") or ":81" in base_url):
        if base_url.startswith("http://"):
            base_url = base_url.replace("http://", "https://")
        validation_url = f"{base_url}:446/valid8.php"
    else:
        validation_url = f"{base_url}/valid8.php"

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    try:
        # Fetch form tokens
        get_response = session.get(validation_url, timeout=5, verify=False)
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

        # Build payload
        payload = {
            user_field_name: username,
            pass_field_name: password,
            "submit": "Submit",
        }

        # Submit credentials
        post_response = session.post(validation_url, data=payload, timeout=5, verify=False)

        if "Login Validated" in post_response.text or "Redirecting" in post_response.text:
            return f"[+] {name}: Successfully whitelisted!"
        else:
            return f"[-] {name}: Validation failed or response changed."

    except requests.exceptions.Timeout:
        return f"[-] {name}: Connection timed out (Server offline?)"
    except requests.exceptions.HTTPError as http_err:
        return f"[-] {name}: HTTP Error {http_err.response.status_code}"
    except Exception as e:
        return f"[-] {name}: Connection error: {e}"


def main():
    dialers = fetch_dialer_data()

    if not dialers:
        print("[-] No dialer data collected. Exiting.")
        return

    print(f"[*] Starting parallel IP validation across {len(dialers)} hosts using {MAX_WORKERS} threads...\n")

    success_count = 0
    fail_count = 0

    # Using ThreadPoolExecutor to handle network requests concurrently
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks to the executor queue
        futures = {}
        for dialer in dialers:
            url = dialer.get("dialer_url")
            user = dialer.get("admin_username")
            pwd = dialer.get("admin_password")
            name = dialer.get("name", "Unknown Dialer")

            if url and user and pwd:
                # Kick off the thread task
                future = executor.submit(validate_ip_on_server, url, user, pwd, name)
                futures[future] = name

        # As each thread completes its execution, grab and print the output immediately
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
import requests
import datetime
import json

# List of URLs to check
URLS = [
    "https://www.google.com",
    "https://www.github.com"
]

def check_url(url):
    """Check if a URL is up or down"""
    try:
        response = requests.get(url, timeout=5)
        status = "UP" if response.status_code == 200 else f"DOWN ({response.status_code})"
    except requests.exceptions.RequestException as e:
        status = f"DOWN (Error: {str(e)})"
    return status

def log_result(url, status):
    """Create structured log entry"""
    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "url": url,
        "status": status
    }
    print(json.dumps(log_entry))  # Print as JSON (works well with cloud logs)

def main():
    for url in URLS:
        status = check_url(url)
        log_result(url, status)
        if "DOWN" in status:
            print(json.dumps({"ALERT": f"⚠️ {url} is {status}"}))

if __name__ == "__main__":
    main()
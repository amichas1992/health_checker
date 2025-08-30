#!/usr/bin/env python3
import os
import requests
import datetime
import json
import smtplib
from email.message import EmailMessage
from typing import List
import sys

# ---- CONFIG ----
DEFAULT_URLS = [
    "https://www.google.com",
    "https://www.github.com"
]

LOG_FILE = os.getenv("LOG_FILE", "")  # optional path
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK", "").strip()
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "").strip()
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "health-checker@example.com").strip()
SMTP_SERVER = os.getenv("SMTP_SERVER", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "0")) if os.getenv("SMTP_PORT") else None
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip()

# --- helpers ---
def parse_urls() -> List[str]:
    env = os.getenv("URLS", "")
    if env.strip():
        return [u.strip() for u in env.split(",") if u.strip()]
    return DEFAULT_URLS

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

# --- core check ---
def check_url(url: str) -> str:
    try:
        response = requests.get(url, timeout=5)
        status = "UP" if response.status_code == 200 else f"DOWN ({response.status_code})"
    except requests.exceptions.RequestException as e:
        status = f"DOWN (Error: {str(e)})"
    return status

# --- logging & alerts ---
def emit_log(entry: dict):
    line = json.dumps(entry, ensure_ascii=False)
    print(line, flush=True)
    if LOG_FILE:
        try:
            os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
            with open(LOG_FILE, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception as e:
            print(json.dumps({"error": f"failed to write log file: {e}"}), flush=True)

def send_slack_alert(webhook: str, text: str) -> bool:
    try:
        payload = {"text": text}
        r = requests.post(webhook, json=payload, timeout=5)
        return r.status_code == 200
    except Exception as e:
        emit_log({"error": f"slack send failed: {e}"})
        return False

def send_email_alert(to_addr: str, from_addr: str, subject: str, body: str) -> bool:
    if not (SMTP_SERVER and SMTP_PORT and SMTP_USER is not None):
        emit_log({"error": "SMTP not configured, skipping email alert"})
        return False
    try:
        msg = EmailMessage()
        msg["From"] = from_addr
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.set_content(body)
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10) as s:
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as s:
                s.ehlo()
                s.starttls()
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        return True
    except Exception as e:
        emit_log({"error": f"email send failed: {e}"})
        return False

def log_result(url: str, status: str):
    entry = {
        "timestamp": now_iso(),
        "url": url,
        "status": status
    }
    emit_log(entry)
    if status.startswith("DOWN"):
        alert_text = f"⚠️ {url} is {status}"
        emit_log({"ALERT": alert_text})
        if SLACK_WEBHOOK:
            send_slack_alert(SLACK_WEBHOOK, alert_text)
        if ALERT_EMAIL_TO:
            send_email_alert(ALERT_EMAIL_TO, ALERT_EMAIL_FROM,
                             f"Health alert: {url}", alert_text)

# --- runtimes: CLI single-run or Flask web ---
def run_checks_once():
    urls = parse_urls()
    results = []
    for url in urls:
        status = check_url(url)
        log_result(url, status)
        results.append({"url": url, "status": status})
    return results

# If user wants Flask, we import Flask lazily (so non-web runs don't need it)
def run_flask(host="0.0.0.0", port=5000):
    from flask import Flask, jsonify
    app = Flask(__name__)

    @app.get("/health")
    def health():
        results = run_checks_once()
        return jsonify({"timestamp": now_iso(), "results": results})

    @app.get("/")
    def home():
        return jsonify({"message": "Health Checker", "routes": ["/health"]})

    app.run(host=host, port=port)

# ---- entrypoint ----
def usage():
    return "Usage: python health_checker.py [cli|web]\nOr set environment variable MODE=web to run web mode."

if __name__ == "__main__":
    # priority: CLI arg, then MODE env var, else default cli
    mode = None
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        mode = os.getenv("MODE", "cli").lower()

    if mode == "web":
        run_flask()
    elif mode == "cli":
        run_checks_once()
    else:
        print(usage())
        sys.exit(2)

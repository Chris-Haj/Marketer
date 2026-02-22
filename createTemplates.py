import requests
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
WABA_ID = os.getenv("WHATSAPP_ID")
API_VERSION = os.getenv("API_VERSION", "v19.0")

BASE_URL = f"https://graph.facebook.com/{API_VERSION}/{WABA_ID}/message_templates"

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

JSON_PATH = "original.json"

RATE_DELAY = 0.5  # seconds between requests
MAX_RETRIES = 5

import re


def extract_variable_count(text: str):
    matches = re.findall(r"\{\{(\d+)\}\}", text)
    if not matches:
        return 0
    return max(int(n) for n in matches)


def build_body_component(text: str, sample_values: list):
    variable_count = extract_variable_count(text)

    component = {"type": "BODY", "text": text}

    if variable_count > 0:
        # Ensure correct number of samples
        samples = sample_values[:variable_count]

        # Pad if fewer provided
        while len(samples) < variable_count:
            samples.append("sample")

        component["example"] = {"body_text": [samples]}

    return component


def build_templates(row):
    base_name = row["message_key"].lower()
    variables = row.get("variables", [])

    templates = []

    language_map = {"content_en": "en_US", "content_ar": "ar", "content_he": "he"}

    for content_key, lang_code in language_map.items():
        text = row.get(content_key)
        if not text:
            continue

        body_component = build_body_component(text, variables)

        templates.append(
            {
                "name": base_name,
                "language": lang_code,
                "category": "UTILITY",
                "components": [body_component],
            }
        )

    return templates


def create_template(template: dict):
    retries = 0
    print(BASE_URL)

    while retries <= MAX_RETRIES:
        response = requests.post(BASE_URL, headers=HEADERS, json=template)

        if response.status_code == 200:
            print(f"[SUCCESS] Created template: {template.get('name')}")
            print("Response:", response.json())
            return True

        # Rate limit handling
        if response.status_code == 429:
            wait_time = 2**retries
            print(f"[RATE LIMIT] Retrying in {wait_time}s...")
            time.sleep(wait_time)
            retries += 1
            continue

        # Other errors
        try:
            error_data = response.json()
        except Exception:
            error_data = response.text

        print(f"[FAILED] {template.get('name')} -> {error_data}")
        return False

    print(f"[ERROR] Max retries exceeded for {template.get('name')}")
    return False


def main():
    if not ACCESS_TOKEN or not WABA_ID:
        raise ValueError("ACCESS_TOKEN or WABA_ID missing in .env")

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        templates = json.load(f)

    print(f"Loaded {len(templates)} templates")

    success_count = 0

    for row in templates:
        if row["id"] != 35:
            continue

        payloads = build_templates(row)

        for payload in payloads:
            create_template(payload)
            time.sleep(RATE_DELAY)

    print("\n========== SUMMARY ==========")
    print(f"Total: {len(templates)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(templates) - success_count}")


if __name__ == "__main__":
    main()

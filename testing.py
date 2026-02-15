import requests
import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import os
from dotenv import load_dotenv
from fastapi import Query
import time
from queue import Queue
import uuid


audio_queue = Queue()

import subprocess
import os


def audio_worker():
    print("Audio worker started")
    while True:
        filepath = audio_queue.get()
        try:
            print("Playing:", filepath)

            subprocess.run(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", filepath]
            )

            os.remove(filepath)

        except Exception as e:
            print("Playback error:", e)

        audio_queue.task_done()


def download_media_file(media_url):
    print("Downloading from:", media_url)

    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(media_url, headers=headers)

    print("Download status:", response.status_code)

    if response.status_code != 200:
        print("Download failed:", response.text)
        return None

    filename = f"voice_{uuid.uuid4().hex}.ogg"

    with open(filename, "wb") as f:
        f.write(response.content)

    print("Saved file:", filename)
    return filename


def download_and_queue_audio(media_id):
    print("Fetching media URL...")
    media_url = get_media_url(media_id)

    if media_url:
        file_path = download_media_file(media_url)
        print("Queueing file:", file_path)
        audio_queue.put(file_path)
    else:
        print("No media URL returned")


load_dotenv()
phone_id = os.getenv("PHONE_ID")
whatsapp_id = os.getenv("WHATSAPP_ID")
access_token = os.getenv("ACCESS_TOKEN")
port = int(os.environ.get("PORT", 8000))
app = FastAPI()

RECIPIENT = "+972527553195"  # recipient phone number in international format

VERIFY_TOKEN = "9P0CPkoVQaDULkdtd7PU"  # same value you put in Meta


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge)
    return PlainTextResponse(content="Verification failed", status_code=403)


@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()
    print(json.dumps(data, indent=2))

    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        if "messages" in value:
            message = value["messages"][0]
            sender = message["from"]
            msg_type = message["type"]

            print("Message from:", sender)
            print("Type:", msg_type)

            if msg_type == "text":
                text = message["text"]["body"]
                print("Text:", text)

            elif msg_type == "audio":
                media_id = message["audio"]["id"]
                print("Audio ID:", media_id)
                download_and_queue_audio(media_id)

    except Exception as e:
        print("Webhook handling error:", e)

    return "OK"


def get_media_url(media_id):
    url = f"https://graph.facebook.com/v22.0/{media_id}"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(url, headers=headers)
    print("MEDIA URL RESPONSE:", response.status_code, response.text)

    return response.json().get("url")


def send_custom_message(text: str):
    url = f"https://graph.facebook.com/v22.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    data = {
        "messaging_product": "whatsapp",
        "to": RECIPIENT,
        "type": "text",
        "text": {"body": text},
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()


import threading


def terminal_sender():
    while True:
        try:
            message = input("Type message to send (or 'exit'): ")

            if message.lower() == "exit":
                print("Stopping sender...")
                break

            result = send_custom_message(message)
            print("Response:", result)

        except Exception as e:
            print("Send error:", e)


def send_message():
    url = f"https://graph.facebook.com/v22.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    data = {
        "messaging_product": "whatsapp",
        "to": RECIPIENT,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "Choose an option:"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "opt1", "title": "Option 1"}},
                    {"type": "reply", "reply": {"id": "opt2", "title": "Option 2"}},
                ]
            },
        },
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response.json()


if __name__ == "__main__":
    sender_thread = threading.Thread(target=terminal_sender, daemon=True)
    sender_thread.start()

    audio_thread = threading.Thread(target=audio_worker, daemon=True)
    audio_thread.start()

    uvicorn.run(app, host="0.0.0.0", port=port)

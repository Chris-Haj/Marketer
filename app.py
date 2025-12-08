import requests
import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import os
from dotenv import load_dotenv

load_dotenv()
phone_id = os.getenv("PHONE_ID")
access_token = os.getenv("ACCESS_TOKEN")
port = int(os.environ.get("PORT", 8000))
app = FastAPI()

RECIPIENT = "+972527553195"  # recipient phone number in international format

VERIFY_TOKEN = "9P0CPkoVQaDULkdtd7PU"  # same value you put in Meta


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = None, hub_verify_token: str = None, hub_challenge: str = None
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge)
    return PlainTextResponse(content="Verification failed", status_code=403)


@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()
    print("Incoming webhook:", data)

    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        if "messages" in value:
            message = value["messages"][0]
            sender = message["from"]
            text = message.get("text", {}).get("body", "")

            print("Message from:", sender)
            print("Text:", text)

    except Exception as e:
        print("Webhook handling error:", e)

    return "OK"


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
    uvicorn.run(app, host="0.0.0.0", port=port)

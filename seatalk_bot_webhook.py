"""
SeaTalk Webhook Bot — TH L3 Growth Campaigns PIC Tagger
"""

import hashlib
import hmac
import json
import os
import time

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

SIGNING_SECRET = os.getenv("SEATALK_SIGNING_SECRET", "")
INCOMING_WEBHOOK_URL = "https://openapi.seatalk.io/webhook/group/BXvjOgfJRTKi3wOGt5Emfw"
TRIGGER_NAME = "TH - L3 - Growth Campaigns"

PICS = [
    {"email": "cgame.kaphuakn@shopee.com",  "seatalk_id": "1432124319"},
    {"email": "lyn.tantrasu@shopee.com",     "seatalk_id": "9511836011"},
    {"email": "fang.klinmale@shopee.com",    "seatalk_id": "9184696428"},
    {"email": "mod.limsirap@shopee.com",     "seatalk_id": "1243337925"},
    {"email": "game.aumkhant@shopee.com",    "seatalk_id": "9482491714"},
]


def verify_signature(request):
    """ตรวจสอบ Signing Secret จาก SeaTalk"""
    if not SIGNING_SECRET:
        return True
    try:
        timestamp = request.headers.get("x-seatalk-timestamp", "")
        signature = request.headers.get("x-seatalk-signature", "")
        body = request.get_data(as_text=True)
        message = f"{timestamp}\n{body}"
        expected = hmac.new(
            SIGNING_SECRET.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception as e:
        print(f"[verify] error: {e}")
        return True  # ถ้า verify ไม่ได้ให้ผ่านไปก่อน


def send_reply(thread_id):
    mention_parts = []
    mention_list = []
    for pic in PICS:
        mention_parts.append(f"<at:{pic['seatalk_id']}>{pic['email']}</at>")
        mention_list.append({"seatalk_id": pic["seatalk_id"]})

    text = "📌 PIC for TH - L3 - Growth Campaigns:\n" + "  ".join(mention_parts)

    payload = {
        "tag": "text",
        "text": {
            "content": text,
            "mentioned_list": mention_list,
        },
    }
    if thread_id:
        payload["thread_id"] = thread_id

    headers = {"Content-Type": "application/json"}
    resp = requests.post(INCOMING_WEBHOOK_URL, json=payload, headers=headers, timeout=10)
    print(f"[send_reply] status={resp.status_code} body={resp.text}")
    return resp.ok


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"status": "ok"}), 200

    data = request.get_json(silent=True) or {}
    print(f"[webhook] received: {json.dumps(data, ensure_ascii=False)}")

    # Challenge verification
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    event = data.get("event", {})
    event_type = event.get("type", "")

    message = event.get("message", {})
    content = message.get("content", "") or message.get("text", "") or ""
    thread_id = message.get("thread_id", "") or event.get("thread_id", "")

    print(f"[webhook] type={event_type} content={content!r}")

    if TRIGGER_NAME.lower() not in content.lower():
        return jsonify({"status": "ignored"}), 200

    send_reply(thread_id=thread_id)
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Bot running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

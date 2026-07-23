"""
SeaTalk Webhook Bot — TH L3 Growth Campaigns PIC Tagger
========================================================
เมื่อมีคนแท็ก @TH - L3 - Growth Campaigns ในกลุ่ม
บอทจะ Reply ใน Thread เดิม โดยแท็ก PIC ทุกคนพร้อมกัน

Requirements:
    pip install flask requests

Run:
    python seatalk_bot_webhook.py
"""

import hashlib
import hmac
import json
import os

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────

# SeaTalk Outgoing Webhook verification token (ตั้งใน SeaTalk Bot settings)
VERIFICATION_TOKEN = os.getenv("SEATALK_VERIFICATION_TOKEN", "YOUR_VERIFICATION_TOKEN")

# SeaTalk Incoming Webhook URL (สำหรับส่งข้อความกลับเข้ากลุ่ม)
INCOMING_WEBHOOK_URL = "https://openapi.seatalk.io/webhook/group/BXvjOgfJRTKi3wOGt5Emfw"

# Keyword ที่ trigger บอท (ชื่อบอทที่คนแท็ก)
TRIGGER_NAME = "TH - L3 - Growth Campaigns"

# PIC list: {email: seatalk_id}
# ดึงมาจาก Google Sheets:
# https://docs.google.com/spreadsheets/d/1gWCZ03AMXPx3eWSPIiszEUrhYGINNuUwcSBdsEut-hk
PICS = [
    {"email": "cgame.kaphuakn@shopee.com",  "seatalk_id": "1432124319"},
    {"email": "lyn.tantrasu@shopee.com",     "seatalk_id": "9511836011"},
    {"email": "fang.klinmale@shopee.com",    "seatalk_id": "9184696428"},
    {"email": "mod.limsirap@shopee.com",     "seatalk_id": "1243337925"},
    {"email": "game.aumkhant@shopee.com",    "seatalk_id": "9482491714"},
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def verify_token(token: str) -> bool:
    """ตรวจสอบ verification token จาก SeaTalk"""
    return hmac.compare_digest(token, VERIFICATION_TOKEN)


def build_mention_text() -> tuple[str, list]:
    """
    สร้าง mention text และ mention list สำหรับแท็ก PIC ทุกคน
    Returns (message_text, mention_list)
    """
    mention_parts = []
    mention_list = []

    for pic in PICS:
        # SeaTalk mention format: <at:seatalk_id>display_text</at>
        mention_parts.append(f"<at:{pic['seatalk_id']}>{pic['email']}</at>")
        mention_list.append({"seatalk_id": pic["seatalk_id"]})

    text = "📌 Tagging PIC for TH - L3 - Growth Campaigns:\n" + "  ".join(mention_parts)
    return text, mention_list


def send_reply(thread_id: str, group_id: str) -> bool:
    """
    ส่ง reply กลับเข้า thread เดิมใน SeaTalk group
    """
    text, mention_list = build_mention_text()

    payload = {
        "tag": "text",
        "text": {
            "content": text,
            "mentioned_list": mention_list,
        },
        # thread_id ทำให้ reply เข้า thread เดิม (ถ้า SeaTalk รองรับ)
        "thread_id": thread_id,
    }

    headers = {"Content-Type": "application/json"}
    resp = requests.post(INCOMING_WEBHOOK_URL, json=payload, headers=headers, timeout=10)

    print(f"[send_reply] status={resp.status_code} body={resp.text}")
    return resp.ok


# ─── Webhook Endpoint ─────────────────────────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}
    print(f"[webhook] received: {json.dumps(data, ensure_ascii=False)}")

    # ── 1. URL Verification challenge (SeaTalk ส่งมาตอน setup) ──────────────
    if "challenge" in data:
        token = data.get("token", "")
        if not verify_token(token):
            return jsonify({"error": "invalid token"}), 403
        return jsonify({"challenge": data["challenge"]})

    # ── 2. ตรวจ token ────────────────────────────────────────────────────────
    token = data.get("token", "")
    if not verify_token(token):
        return jsonify({"error": "invalid token"}), 403

    # ── 3. ดึงข้อมูล event ──────────────────────────────────────────────────
    event = data.get("event", {})
    event_type = event.get("type", "")

    # รองรับทั้ง group_message และ bot_mention
    if event_type not in ("group_message", "bot_mention", "message"):
        return jsonify({"status": "ignored", "reason": f"event_type={event_type}"}), 200

    message = event.get("message", {})
    content: str = message.get("content", "") or message.get("text", "")
    thread_id: str = message.get("thread_id", "") or event.get("thread_id", "")
    group_id: str = event.get("group_id", "") or message.get("group_id", "")

    print(f"[webhook] content={content!r} thread_id={thread_id} group_id={group_id}")

    # ── 4. ตรวจว่าแท็ก @TH - L3 - Growth Campaigns หรือเปล่า ───────────────
    if TRIGGER_NAME.lower() not in content.lower():
        return jsonify({"status": "ignored", "reason": "trigger not found"}), 200

    # ── 5. ส่ง reply แท็ก PIC ทุกคนใน thread เดิม ───────────────────────────
    success = send_reply(thread_id=thread_id, group_id=group_id)

    if success:
        return jsonify({"status": "ok"}), 200
    else:
        return jsonify({"status": "error", "reason": "failed to send reply"}), 500


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"🚀 SeaTalk PIC-Tagger Bot running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

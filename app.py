
import os
import hmac
import hashlib
import requests

from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "change-this-token")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
APP_SECRET = os.environ.get("APP_SECRET", "")

DEFAULT_REPLY = (
    "أنا مجرد بوت برمجني براهيمي يوسف، "
    "اترك رسالتك وسوف يرد عليك عن قريب."
)

KEYWORD_REPLIES = {
    "السلام": "وعليكم السلام ورحمة الله وبركاته!",
    "سلام": "أهلًا بك! أنا مجرد بوت برمجني براهيمي يوسف، اترك رسالتك وسوف يرد عليك عن قريب.",
    "شكرا": "العفو! أنا مجرد بوت برمجني براهيمي يوسف، اترك رسالتك وسوف يرد عليك عن قريب.",
    "شكراً": "العفو! أنا مجرد بوت برمجني براهيمي يوسف، اترك رسالتك وسوف يرد عليك عن قريب."
}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/status")
def status():
    return jsonify({
        "connected": bool(PAGE_ACCESS_TOKEN),
        "default_reply": DEFAULT_REPLY
    })


@app.route("/api/settings", methods=["POST"])
def save_settings():
    global DEFAULT_REPLY, KEYWORD_REPLIES

    data = request.get_json(silent=True) or {}

    reply = str(data.get("default_reply", "")).strip()
    if reply:
        DEFAULT_REPLY = reply[:2000]

    keywords = data.get("keywords", [])
    if isinstance(keywords, list):
        updated = {}
        for item in keywords[:40]:
            if not isinstance(item, dict):
                continue

            keyword = str(item.get("keyword", "")).strip()
            answer = str(item.get("reply", "")).strip()

            if keyword and answer:
                updated[keyword[:80]] = answer[:1000]

        if updated:
            KEYWORD_REPLIES = updated

    return jsonify({
        "ok": True,
        "message": "تم تحديث الإعدادات."
    })


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode", "")
    token = request.args.get("hub.verify_token", "")
    challenge = request.args.get("hub.challenge", "")

    if mode == "subscribe" and hmac.compare_digest(
        token, VERIFY_TOKEN
    ):
        return challenge, 200

    return "Verification failed", 403


def verify_signature(raw_body):
    if not APP_SECRET:
        return True

    signature = request.headers.get("X-Hub-Signature-256", "")

    if not signature.startswith("sha256="):
        return False

    digest = hmac.new(
        APP_SECRET.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature[7:], digest)


def get_reply(message):
    text = (message or "").strip().lower()

    for keyword, reply in KEYWORD_REPLIES.items():
        if keyword.lower() in text:
            return reply

    return DEFAULT_REPLY


def send_message(recipient_id, text):
    if not PAGE_ACCESS_TOKEN:
        app.logger.error("PAGE_ACCESS_TOKEN is missing")
        return False

    url = "https://graph.facebook.com/v22.0/me/messages"

    try:
        response = requests.post(
            url,
            params={"access_token": PAGE_ACCESS_TOKEN},
            json={
                "recipient": {"id": recipient_id},
                "messaging_type": "RESPONSE",
                "message": {"text": text[:2000]}
            },
            timeout=15
        )

        if not response.ok:
            app.logger.error(
                "Messenger error: %s",
                response.text[:500]
            )

        return response.ok

    except requests.RequestException:
        app.logger.exception("Could not send reply")
        return False


@app.route("/webhook", methods=["POST"])
def receive_message():
    raw_body = request.get_data()

    if not verify_signature(raw_body):
        return "Invalid signature", 403

    payload = request.get_json(silent=True) or {}

    if payload.get("object") != "page":
        return "Ignored", 200

    for entry in payload.get("entry", []):
        for event in entry.get("messaging", []):
            sender = event.get("sender", {}).get("id")
            message = event.get("message", {})

            # تجاهل الرسائل التي أرسلتها الصفحة نفسها
            if message.get("is_echo"):
                continue

            text = message.get("text")

            # هذا النموذج يعالج الرسائل النصية فقط
            if not sender or not text:
                continue

            reply = get_reply(text)
            send_message(sender, reply)

    return "EVENT_RECEIVED", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)

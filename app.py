import os
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "brahimi2026")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
APP_SECRET = os.environ.get("APP_SECRET", "")

DEFAULT_REPLY = (
    "أنا مجرد بوت برمجني براهيمي يوسف، "
    "اترك رسالتك وسوف يرد عليك عن قريب."
)

KEYWORD_REPLIES = {
    "سلام": "وعليكم السلام ورحمة الله وبركاته.",
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته.",
    "شكرا": "العفو، مرحبًا بك.",
    "شكراً": "العفو، مرحبًا بك."
}

GRAPH_API_URL = "https://graph.facebook.com/v22.0/me/messages"


@app.route("/")
def home():
    # index.html بجانب app.py مباشرة
    return send_file(
        os.path.join(os.path.dirname(__file__), "index.html")
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/status")
def status():
    return jsonify({
        "page_token_configured": bool(PAGE_ACCESS_TOKEN),
        "app_secret_configured": bool(APP_SECRET),
        "default_reply": DEFAULT_REPLY
    })


def choose_reply(message):
    text = (message or "").strip().lower()

    for keyword, reply in KEYWORD_REPLIES.items():
        if keyword.lower() in text:
            return reply

    return DEFAULT_REPLY


@app.route("/api/test-reply", methods=["POST"])
def test_reply():
    data = request.get_json(silent=True) or {}
    message = str(data.get("text", ""))
    return jsonify({"reply": choose_reply(message)})


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode", "")
    token = request.args.get("hub.verify_token", "")
    challenge = request.args.get("hub.challenge", "")

    if mode == "subscribe" and hmac.compare_digest(
        token, VERIFY_TOKEN
    ):
        return challenge, 200

    return "Webhook verification failed", 403


def valid_signature(raw_body):
    if not APP_SECRET:
        return False

    signature = request.headers.get(
        "X-Hub-Signature-256", ""
    )

    if not signature.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(
        APP_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


def send_message(recipient_id, message_text):
    if not PAGE_ACCESS_TOKEN:
        app.logger.error("PAGE_ACCESS_TOKEN is missing.")
        return False

    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }

    try:
        response = requests.post(
            GRAPH_API_URL,
            params={"access_token": PAGE_ACCESS_TOKEN},
            json=payload,
            timeout=20
        )

        if not response.ok:
            app.logger.error(
                "Meta API error: %s",
                response.text[:1000]
            )

        return response.ok

    except requests.RequestException:
        app.logger.exception("Facebook message sending failed.")
        return False


@app.route("/webhook", methods=["POST"])
def receive_message():
    raw_body = request.get_data()

    # رفض الأحداث التي لا تحمل توقيع Meta الصحيح
    if not valid_signature(raw_body):
        return "Invalid signature", 403

    data = request.get_json(silent=True) or {}

    if data.get("object") != "page":
        return "Ignored", 200

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            message = event.get("message") or {}

            # تجاهل الرسائل التي أرسلها البوت نفسه
            if message.get("is_echo"):
                continue

            sender_id = (event.get("sender") or {}).get("id")
            text = message.get("text")

            if sender_id and text:
                reply = choose_reply(text)
                send_message(sender_id, reply)

    return "EVENT_RECEIVED", 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=False
    )

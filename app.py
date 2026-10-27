from flask import Flask, render_template, request, jsonify
from urllib.parse import urlparse
from pathlib import Path
import json
from datetime import datetime, timezone

app = Flask(__name__)
DATA_FILE = Path(__file__).with_name("stats.json")

def read_stats():
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid stats")
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        data = {"visits": 0, "video_opens": 0, "shares": 0}
    return data

def write_stats(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def is_tiktok_url(value):
    try:
        parsed = urlparse(value.strip())
        host = (parsed.hostname or "").lower()
        return parsed.scheme in ("http", "https") and (
            host == "tiktok.com" or host.endswith(".tiktok.com")
        )
    except ValueError:
        return False

@app.get("/")
def home():
    stats = read_stats()
    stats["visits"] += 1
    write_stats(stats)
    return render_template("index.html", stats=stats)

@app.post("/api/event")
def event():
    body = request.get_json(silent=True) or {}
    event_name = body.get("event")
    mapping = {
        "video_open": "video_opens",
        "share": "shares",
    }
    if event_name not in mapping:
        return jsonify({"ok": False, "error": "حدث غير معروف"}), 400
    stats = read_stats()
    stats[mapping[event_name]] += 1
    write_stats(stats)
    return jsonify({"ok": True, "stats": stats})

@app.post("/api/validate")
def validate():
    body = request.get_json(silent=True) or {}
    url = str(body.get("url", "")).strip()
    if not is_tiktok_url(url):
        return jsonify({"ok": False, "error": "أدخل رابطًا صحيحًا من TikTok."}), 400
    return jsonify({"ok": True, "url": url})

if __name__ == "__main__":
    # For local testing only. For deployment, use a production WSGI server.
    app.run(host="127.0.0.1", port=5000, debug=False)

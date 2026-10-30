
import os
import json
import urllib.request
import urllib.error
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

API_KEY = os.environ.get("FREE_AI_API_KEY", "")
API_BASE = "https://api.free.ai"

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

def api_request(endpoint, data):
    if not API_KEY:
        return {"error": "مفتاح API غير موجود في Render"}

    req = urllib.request.Request(
        API_BASE + endpoint,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + API_KEY,
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return {"error": e.read().decode("utf-8")}
        except Exception:
            return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

@app.route("/api/video", methods=["POST"])
def video():
    prompt = (request.json or {}).get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "اكتب وصف الفيديو"})

    result = api_request("/v1/video/generate/", {
        "prompt": prompt,
        "duration": 5,
        "model": "cogvideox"
    })
    return jsonify(result)

@app.route("/api/image", methods=["POST"])
def image():
    prompt = (request.json or {}).get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "اكتب وصف الصورة"})

    result = api_request("/v1/image/generate/", {
        "prompt": prompt,
        "model": "sdxl",
        "width": 1024,
        "height": 1024
    })
    return jsonify(result)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )

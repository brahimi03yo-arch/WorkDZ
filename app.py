
import os
import json
import urllib.request
import urllib.error

from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

API_KEY = os.environ.get("FREE_AI_API_KEY", "").strip()
API_BASE = "https://api.free.ai"


def free_ai_request(path, method="POST", data=None):
    if not API_KEY:
        return None, "FREE_AI_API_KEY غير موجود في Render"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(
        API_BASE + path,
        data=body,
        headers=headers,
        method=method
    )

    try:
        with urllib.request.urlopen(req, timeout=240) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw), None

    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            details = json.loads(raw)
            message = details.get("error", details)
        except Exception:
            message = raw

        return None, f"HTTP {e.code}: {message}"

    except Exception as e:
        return None, str(e)


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/test", methods=["GET"])
def test():
    result, error = free_ai_request(
        "/v1/models",
        method="GET"
    )

    if error:
        return jsonify({
            "ok": False,
            "message": error
        }), 400

    return jsonify({
        "ok": True,
        "message": "الاتصال بـ Free.ai ناجح",
        "models_count": len(result.get("data", []))
            if isinstance(result, dict) else None
    })


@app.route("/api/video", methods=["POST"])
def generate_video():
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("prompt", "")).strip()

    if not prompt:
        return jsonify({"error": "اكتب وصف الفيديو أولاً"}), 400

    payload = {
        "prompt": prompt,
        "duration": 5,
        "model": "cogvideox-2b"
    }

    result, error = free_ai_request(
        "/v1/video/generate/",
        data=payload
    )

    if error:
        return jsonify({"error": error}), 502

    return jsonify(result)


@app.route("/api/image", methods=["POST"])
def generate_image():
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("prompt", "")).strip()

    if not prompt:
        return jsonify({"error": "اكتب وصف الصورة أولاً"}), 400

    payload = {
        "prompt": prompt,
        "model": "sdxl",
        "aspect_ratio": "1:1"
    }

    result, error = free_ai_request(
        "/v1/image/generate/",
        data=payload
    )

    if error:
        return jsonify({"error": error}), 502

    return jsonify(result)


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "الصفحة غير موجودة"}), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

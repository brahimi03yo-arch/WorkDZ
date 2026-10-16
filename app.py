
from flask import Flask, send_file
import os

app = Flask(__name__)

@app.route("/")
def home():
    return send_file(
        os.path.join(os.path.dirname(__file__), "index.html")
    )

@app.route("/health")
def health():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

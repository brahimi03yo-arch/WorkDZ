
import os
import random

from flask import Flask, jsonify, send_from_directory, session

app = Flask(__name__, static_folder="static")
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "Youssef-Brahimi-Change-This-Key-2026"
)

DUAS = [
    "اللهم ارزقه راحة البال وسعة الرزق.",
    "اللهم افتح له أبواب الخير والتوفيق.",
    "اللهم اجعل أيامه فرحًا وسعادة.",
    "اللهم احفظه ووفقه لكل خير.",
    "اللهم ارزقه من حيث لا يحتسب.",
    "اللهم اجعل له من كل هم فرجًا.",
    "اللهم اكتب له الخير أينما كان.",
    "اللهم حقق له ما يتمنى إن كان خيرًا له.",
    "اللهم املأ قلبه نورًا وطمأنينة.",
    "اللهم اجعل القادم من حياته أجمل."
]

GIFTS = [
    "🎁 هدية الفرح",
    "👑 تاج التميز",
    "💎 جوهرة الأمل",
    "🌟 نجمة التوفيق",
    "🌹 وردة المحبة",
    "🏆 كأس الإنجاز",
    "🕊️ هدية الطمأنينة",
    "✨ نجمة الحظ الجميل"
]


def prepare_visit():
    if "dua" not in session:
        session["dua"] = random.choice(DUAS)
        session["gift"] = random.choice(GIFTS)
        session["claimed"] = False


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/data")
def data():
    prepare_visit()

    return jsonify({
        "dua": session["dua"],
        "gift": session["gift"],
        "claimed": session["claimed"]
    })


@app.route("/claim", methods=["POST"])
def claim():
    prepare_visit()

    if session.get("claimed", False):
        return jsonify({
            "success": False,
            "message": "لقد استلمت هديتك الرمزية من قبل."
        }), 409

    session["claimed"] = True
    session.modified = True

    return jsonify({
        "success": True,
        "message": "تم استلام هديتك الرمزية بنجاح! 🎉"
    })


@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000"))
    )

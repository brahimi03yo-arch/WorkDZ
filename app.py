import os
import sqlite3
import secrets
import hashlib
import datetime
from functools import wraps

from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory,
    session
)

try:
    import requests
except ImportError:
    requests = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


# =========================================================
# إعداد التطبيق
# =========================================================

app = Flask(__name__, static_folder=".")

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key-in-production"
)

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATA_DIR = os.path.join(BASE_DIR, "youssef_data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

DB_PATH = os.path.join(
    DATA_DIR,
    "kutub_link.db"
)

MAX_UPLOAD = 100 * 1024 * 1024

app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD


# =========================================================
# قاعدة البيانات
# =========================================================

def db():

    con = sqlite3.connect(DB_PATH)

    con.row_factory = sqlite3.Row

    return con


def init_db():

    con = db()

    con.executescript("""
    
    CREATE TABLE IF NOT EXISTS users(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL,

        phone TEXT NOT NULL UNIQUE,

        email TEXT UNIQUE,

        wilaya TEXT,

        password_hash TEXT NOT NULL,

        created_at TEXT NOT NULL

    );


    CREATE TABLE IF NOT EXISTS books(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_id INTEGER,

        title TEXT NOT NULL,

        author TEXT,

        isbn TEXT,

        year TEXT,

        wilaya TEXT,

        category TEXT,

        condition TEXT,

        rarity TEXT,

        deal_type TEXT,

        price REAL DEFAULT 0,

        description TEXT,

        cover TEXT,

        pdf TEXT,

        created_at TEXT NOT NULL,

        FOREIGN KEY(user_id)
            REFERENCES users(id)

    );


    CREATE TABLE IF NOT EXISTS favorites(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_id INTEGER NOT NULL,

        book_id INTEGER NOT NULL,

        UNIQUE(user_id,book_id)

    );


    CREATE TABLE IF NOT EXISTS orders(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        order_code TEXT UNIQUE NOT NULL,

        user_id INTEGER NOT NULL,

        name TEXT NOT NULL,

        phone TEXT NOT NULL,

        wilaya TEXT NOT NULL,

        commune TEXT,

        address TEXT,

        delivery TEXT,

        payment TEXT,

        total REAL DEFAULT 0,

        status TEXT NOT NULL,

        created_at TEXT NOT NULL,

        FOREIGN KEY(user_id)
            REFERENCES users(id)

    );


    CREATE TABLE IF NOT EXISTS order_items(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        order_id INTEGER NOT NULL,

        book_id INTEGER,

        title TEXT NOT NULL,

        price REAL NOT NULL,

        quantity INTEGER DEFAULT 1,

        FOREIGN KEY(order_id)
            REFERENCES orders(id)

    );


    CREATE TABLE IF NOT EXISTS exchanges(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        exchange_code TEXT UNIQUE NOT NULL,

        user_id INTEGER NOT NULL,

        book_id INTEGER,

        offer TEXT NOT NULL,

        note TEXT,

        status TEXT NOT NULL,

        created_at TEXT NOT NULL,

        FOREIGN KEY(user_id)
            REFERENCES users(id)

    );

    """)

    con.commit()

    con.close()


init_db()


# =========================================================
# مساعدات
# =========================================================

def now():

    return datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def hash_password(password):

    salt = secrets.token_hex(16)

    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000
    ).hex()

    return salt + ":" + hashed


def check_password(password, stored):

    try:

        salt, hashed = stored.split(":", 1)

        test = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            120000
        ).hex()

        return secrets.compare_digest(
            test,
            hashed
        )

    except Exception:

        return False


def current_user():

    uid = session.get("user_id")

    if not uid:
        return None

    con = db()

    user = con.execute(
        "SELECT * FROM users WHERE id=?",
        (uid,)
    ).fetchone()

    con.close()

    return user


def login_required(fn):

    @wraps(fn)
    def wrapper(*args, **kwargs):

        if not current_user():

            return jsonify({
                "error": "يجب تسجيل الدخول أولًا"
            }), 401

        return fn(*args, **kwargs)

    return wrapper


def row_book(row, user_id=None):

    item = dict(row)

    item["source"] = "كتب لينك"

    item["favorite"] = False

    if user_id:

        con = db()

        fav = con.execute(
            """
            SELECT id
            FROM favorites
            WHERE user_id=? AND book_id=?
            """,
            (user_id, row["id"])
        ).fetchone()

        con.close()

        item["favorite"] = bool(fav)

    if item.get("cover"):

        item["image"] = "/uploads/" + item["cover"]

    else:

        item["image"] = ""

    if item.get("pdf"):

        item["pdf"] = "/uploads/" + item["pdf"]

    else:

        item["pdf"] = ""

    return item


# =========================================================
# الصفحة
# =========================================================

@app.route("/")
def index():

    return send_from_directory(
        BASE_DIR,
        "index.html"
    )


@app.route("/uploads/<path:name>")
def uploads(name):

    return send_from_directory(
        UPLOAD_DIR,
        name
    )


# =========================================================
# الحساب
# =========================================================

@app.post("/api/register")
def register():

    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    email = str(data.get("email", "")).strip()
    wilaya = str(data.get("wilaya", "")).strip()
    password = str(data.get("password", ""))

    if not name or not phone or not password:

        return jsonify({
            "error": "الاسم والهاتف وكلمة المرور مطلوبة"
        }), 400

    if len(password) < 6:

        return jsonify({
            "error": "كلمة المرور يجب أن تكون 6 أحرف على الأقل"
        }), 400

    con = db()

    try:

        cur = con.execute(
            """
            INSERT INTO users
            (name,phone,email,wilaya,password_hash,created_at)
            VALUES(?,?,?,?,?,?)
            """,
            (
                name,
                phone,
                email or None,
                wilaya,
                hash_password(password),
                now()
            )
        )

        con.commit()

        uid = cur.lastrowid

        session["user_id"] = uid

        user = con.execute(
            "SELECT id,name,phone,email,wilaya FROM users WHERE id=?",
            (uid,)
        ).fetchone()

        return jsonify({
            "message": "تم إنشاء الحساب",
            "user": dict(user)
        })

    except sqlite3.IntegrityError:

        return jsonify({
            "error": "رقم الهاتف أو البريد الإلكتروني مسجل مسبقًا"
        }), 409

    finally:

        con.close()


@app.post("/api/login")
def login():

    data = request.get_json(silent=True) or {}

    identifier = str(
        data.get("identifier", "")
    ).strip()

    password = str(
        data.get("password", "")
    )

    con = db()

    user = con.execute(
        """
        SELECT *
        FROM users
        WHERE phone=?
           OR email=?
        """,
        (identifier, identifier)
    ).fetchone()

    con.close()

    if not user or not check_password(
        password,
        user["password_hash"]
    ):

        return jsonify({
            "error": "بيانات الدخول غير صحيحة"
        }), 401

    session["user_id"] = user["id"]

    return jsonify({
        "message": "تم الدخول",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "phone": user["phone"],
            "email": user["email"],
            "wilaya": user["wilaya"]
        }
    })


@app.post("/api/logout")
def logout():

    session.clear()

    return jsonify({
        "message": "تم تسجيل الخروج"
    })


# =========================================================
# الكتب
# =========================================================

@app.get("/api/books")
def books():

    q = request.args.get(
        "q",
        ""
    ).strip()

    author = request.args.get(
        "author",
        ""
    ).strip()

    year = request.args.get(
        "year",
        ""
    ).strip()

    uid = session.get("user_id")

    con = db()

    sql = """
        SELECT *
        FROM books
        WHERE 1=1
    """

    params = []

    if q:

        sql += """
        AND (
            title LIKE ?
            OR author LIKE ?
            OR isbn LIKE ?
            OR category LIKE ?
            OR wilaya LIKE ?
        )
        """

        x = "%" + q + "%"

        params.extend([
            x,x,x,x,x
        ])

    if author:

        sql += """
        AND author LIKE ?
        """

        params.append(
            "%" + author + "%"
        )

    if year:

        sql += """
        AND year LIKE ?
        """

        params.append(
            "%" + year + "%"
        )

    sql += """
        ORDER BY id DESC
        LIMIT 100
    """

    rows = con.execute(
        sql,
        params
    ).fetchall()

    con.close()

    result = [
        row_book(x, uid)
        for x in rows
    ]


    # Google Books

    google_items = []

    if q and requests:

        try:

            response = requests.get(
                "https://www.googleapis.com/books/v1/volumes",
                params={
                    "q": q,
                    "maxResults": 12,
                    "printType": "books"
                },
                timeout=8
            )

            if response.ok:

                data = response.json()

                for x in data.get(
                    "items",
                    []
                ):

                    info = x.get(
                        "volumeInfo",
                        {}
                    )

                    image = (
                        info.get("imageLinks", {})
                        .get("thumbnail", "")
                    )

                    google_items.append({

                        "id":
                            "google-" + str(x.get("id")),

                        "title":
                            info.get(
                                "title",
                                "بدون عنوان"
                            ),

                        "author":
                            ", ".join(
                                info.get(
                                    "authors",
                                    []
                                )
                            ),

                        "year":
                            info.get(
                                "publishedDate",
                                ""
                            ),

                        "description":
                            info.get(
                                "description",
                                ""
                            ),

                        "image":
                            image,

                        "link":
                            info.get(
                                "infoLink",
                                ""
                            ),

                        "source":
                            "Google Books",

                        "price": 0

                    })

        except Exception:

            pass


    return jsonify({
        "items": result + google_items
    })


# =========================================================
# رفع كتاب
# =========================================================

@app.post("/api/books")
@login_required
def create_book():

    user = current_user()

    form = request.form

    title = form.get(
        "title",
        ""
    ).strip()

    if not title:

        return jsonify({
            "error": "عنوان الكتاب مطلوب"
        }), 400

    try:

        price = float(
            form.get(
                "price",
                0
            ) or 0
        )

    except Exception:

        price = 0

    cover_file = request.files.get(
        "cover"
    )

    pdf_file = request.files.get(
        "pdf"
    )

    cover_name = None
    pdf_name = None


    if cover_file and cover_file.filename:

        ext = os.path.splitext(
            cover_file.filename
        )[1].lower()

        if ext not in [
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".gif"
        ]:

            return jsonify({
                "error": "صيغة صورة الغلاف غير مدعومة"
            }), 400

        cover_name = (
            secrets.token_hex(12)
            + ext
        )

        cover_file.save(
            os.path.join(
                UPLOAD_DIR,
                cover_name
            )
        )


    if pdf_file and pdf_file.filename:

        ext = os.path.splitext(
            pdf_file.filename
        )[1].lower()

        if ext != ".pdf":

            return jsonify({
                "error": "ملف الكتاب يجب أن يكون PDF"
            }), 400

        pdf_name = (
            secrets.token_hex(12)
            + ".pdf"
        )

        pdf_file.save(
            os.path.join(
                UPLOAD_DIR,
                pdf_name
            )
        )


    con = db()

    cur = con.execute(
        """
        INSERT INTO books
        (
            user_id,
            title,
            author,
            isbn,
            year,
            wilaya,
            category,
            condition,
            rarity,
            deal_type,
            price,
            description,
            cover,
            pdf,
            created_at
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            user["id"],
            title,
            form.get("author", ""),
            form.get("isbn", ""),
            form.get("year", ""),
            form.get("wilaya", ""),
            form.get("category", ""),
            form.get("condition", ""),
            form.get("rarity", ""),
            form.get("deal_type", "بيع"),
            price,
            form.get("description", ""),
            cover_name,
            pdf_name,
            now()
        )
    )

    con.commit()

    book_id = cur.lastrowid

    con.close()

    return jsonify({
        "message": "تم نشر الكتاب",
        "book_id": book_id
    })


@app.get("/api/book/<int:book_id>")
def get_book(book_id):

    con = db()

    row = con.execute(
        """
        SELECT *
        FROM books
        WHERE id=?
        """,
        (book_id,)
    ).fetchone()

    con.close()

    if not row:

        return jsonify({
            "error": "الكتاب غير موجود"
        }), 404

    return jsonify(
        row_book(
            row,
            session.get("user_id")
        )
    )


# =========================================================
# المفضلة
# =========================================================

@app.post("/api/book/<int:book_id>/favorite")
@login_required
def favorite(book_id):

    user = current_user()

    con = db()

    exists = con.execute(
        """
        SELECT id
        FROM favorites
        WHERE user_id=? AND book_id=?
        """,
        (
            user["id"],
            book_id
        )
    ).fetchone()

    if exists:

        con.execute(
            """
            DELETE FROM favorites
            WHERE user_id=? AND book_id=?
            """,
            (
                user["id"],
                book_id
            )
        )

        message = "تم حذف الكتاب من المفضلة"

    else:

        con.execute(
            """
            INSERT OR IGNORE INTO favorites
            (user_id,book_id)
            VALUES(?,?)
            """,
            (
                user["id"],
                book_id
            )
        )

        message = "تمت إضافة الكتاب إلى المفضلة"

    con.commit()

    con.close()

    return jsonify({
        "message": message
    })


# =========================================================
# مكتبتي
# =========================================================

@app.get("/api/library")
@login_required
def library():

    user = current_user()

    con = db()

    rows = con.execute(
        """
        SELECT *
        FROM books
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (user["id"],)
    ).fetchall()

    con.close()

    return jsonify({
        "items":[
            row_book(x,user["id"])
            for x in rows
        ]
    })


# =========================================================
# الطلبات
# =========================================================

def make_code(prefix):

    return (
        prefix
        + "-"
        + datetime.datetime.now().strftime("%Y")
        + "-"
        + secrets.token_hex(4).upper()
    )


@app.post("/api/orders")
@login_required
def create_order():

    user = current_user()

    data = request.get_json(
        silent=True
    ) or {}

    items = data.get(
        "items",
        []
    )

    if not items:

        return jsonify({
            "error": "السلة فارغة"
        }), 400

    name = str(
        data.get("name", "")
    ).strip()

    phone = str(
        data.get("phone", "")
    ).strip()

    wilaya = str(
        data.get("wilaya", "")
    ).strip()

    if not name or not phone or not wilaya:

        return jsonify({
            "error": "بيانات التسليم ناقصة"
        }), 400


    con = db()

    total = 0

    clean_items = []

    for item in items:

        try:

            book_id = int(
                item.get("id")
            )

        except Exception:

            continue

        row = con.execute(
            """
            SELECT id,title,price
            FROM books
            WHERE id=?
            """,
            (book_id,)
        ).fetchone()

        if not row:

            continue

        try:

            quantity = max(
                1,
                int(
                    item.get(
                        "qty",
                        1
                    )
                )
            )

        except Exception:

            quantity = 1

        price = float(
            row["price"] or 0
        )

        total += price * quantity

        clean_items.append({
            "id": row["id"],
            "title": row["title"],
            "price": price,
            "quantity": quantity
        })


    if not clean_items:

        con.close()

        return jsonify({
            "error": "لا توجد كتب صالحة في الطلب"
        }), 400


    code = make_code("KL")

    status = "في انتظار تأكيد الطلب"

    cur = con.execute(
        """
        INSERT INTO orders
        (
            order_code,
            user_id,
            name,
            phone,
            wilaya,
            commune,
            address,
            delivery,
            payment,
            total,
            status,
            created_at
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            code,
            user["id"],
            name,
            phone,
            wilaya,
            data.get("commune", ""),
            data.get("address", ""),
            data.get("delivery", ""),
            data.get("payment", ""),
            total,
            status,
            now()
        )
    )

    order_id = cur.lastrowid


    for item in clean_items:

        con.execute(
            """
            INSERT INTO order_items
            (
                order_id,
                book_id,
                title,
                price,
                quantity
            )
            VALUES(?,?,?,?,?)
            """,
            (
                order_id,
                item["id"],
                item["title"],
                item["price"],
                item["quantity"]
            )
        )


    con.commit()

    con.close()

    return jsonify({
        "message": "تم تسجيل الطلب",
        "order": {
            "id": code,
            "total": total,
            "status": status,
            "name": name,
            "phone": phone,
            "wilaya": wilaya,
            "commune": data.get("commune", ""),
            "address": data.get("address", ""),
            "delivery": data.get("delivery", ""),
            "payment": data.get("payment", ""),
            "created_at": now(),
            "items": clean_items
        }
    })


@app.get("/api/orders")
@login_required
def orders():

    user = current_user()

    con = db()

    rows = con.execute(
        """
        SELECT *
        FROM orders
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (user["id"],)
    ).fetchall()

    result = []

    for row in rows:

        item_rows = con.execute(
            """
            SELECT title,price,quantity
            FROM order_items
            WHERE order_id=?
            """,
            (row["id"],)
        ).fetchall()

        x = dict(row)

        x["id"] = x["order_code"]

        x["items"] = [
            dict(i)
            for i in item_rows
        ]

        result.append(x)

    con.close()

    return jsonify({
        "items": result
    })


# =========================================================
# التبادل
# =========================================================

@app.post("/api/exchanges")
@login_required
def create_exchange():

    user = current_user()

    data = request.get_json(
        silent=True
    ) or {}

    offer = str(
        data.get("offer", "")
    ).strip()

    if not offer:

        return jsonify({
            "error": "اكتب الكتاب الذي ستقدمه مقابلًا"
        }), 400

    code = make_code("EX")

    con = db()

    cur = con.execute(
        """
        INSERT INTO exchanges
        (
            exchange_code,
            user_id,
            book_id,
            offer,
            note,
            status,
            created_at
        )
        VALUES(?,?,?,?,?,?,?)
        """,
        (
            code,
            user["id"],
            data.get("book_id"),
            offer,
            data.get("note", ""),
            "في انتظار رد صاحب الكتاب",
            now()
        )
    )

    con.commit()

    con.close()

    return jsonify({
        "message": "تم تسجيل التبادل",
        "exchange": {
            "id": code,
            "status": "في انتظار رد صاحب الكتاب"
        }
    })


# =========================================================
# أدوات الكتاب والذكاء الاصطناعي
# =========================================================

def extract_pdf_text(path):

    if not PdfReader:
        return ""

    try:

        reader = PdfReader(path)

        chunks = []

        for page in reader.pages[:30]:

            text = page.extract_text()

            if text:
                chunks.append(text)

        return "\n".join(chunks)

    except Exception:

        return ""


def local_book_text(book):

    text = ""

    if book["pdf"]:

        path = os.path.join(
            UPLOAD_DIR,
            book["pdf"]
        )

        if os.path.exists(path):

            text = extract_pdf_text(
                path
            )

    if not text:

        text = (
            "عنوان الكتاب: "
            + str(book["title"])
            + "\n"
            + "المؤلف: "
            + str(book["author"] or "")
            + "\n"
            + "الوصف: "
            + str(book["description"] or "")
        )

    return text[:30000]


def ai_answer(prompt):

    api_key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if api_key and requests:

        try:

            url = (
                "https://generativelanguage.googleapis.com/"
                "v1beta/models/gemini-2.5-flash:generateContent"
            )

            response = requests.post(
                url,
                params={
                    "key": api_key
                },
                json={
                    "contents":[
                        {
                            "parts":[
                                {
                                    "text":prompt
                                }
                            ]
                        }
                    ]
                },
                timeout=40
            )

            if response.ok:

                data = response.json()

                candidates = data.get(
                    "candidates",
                    []
                )

                if candidates:

                    parts = candidates[0] \
                        .get("content", {}) \
                        .get("parts", [])

                    answer = "".join(
                        p.get("text", "")
                        for p in parts
                    )

                    if answer:

                        return answer

        except Exception:

            pass


    mistral_key = os.environ.get(
        "MISTRAL_API_KEY"
    )

    if mistral_key and requests:

        try:

            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization":
                        "Bearer " + mistral_key,
                    "Content-Type":
                        "application/json"
                },
                json={
                    "model":
                        "mistral-small-latest",

                    "messages":[
                        {
                            "role":"user",
                            "content":prompt
                        }
                    ],

                    "temperature":0.3
                },
                timeout=40
            )

            if response.ok:

                data = response.json()

                return data["choices"][0]["message"]["content"]

        except Exception:

            pass


    return (
        "المساعد الذكي غير متصل حاليًا. "
        "أضف GEMINI_API_KEY أو MISTRAL_API_KEY "
        "في متغيرات البيئة حتى يتم تفعيل الإجابات الذكية."
    )


@app.post("/api/book/<int:book_id>/tool")
def book_tool(book_id):

    con = db()

    book = con.execute(
        "SELECT * FROM books WHERE id=?",
        (book_id,)
    ).fetchone()

    con.close()

    if not book:

        return jsonify({
            "error": "الكتاب غير موجود"
        }), 404

    action = (
        request.get_json(
            silent=True
        ) or {}
    ).get(
        "action",
        "summary"
    )

    text = local_book_text(book)

    if action == "stats":

        return jsonify({
            "stats": {
                "words": len(text.split()),
                "characters": len(text),
                "paragraphs": len(
                    [
                        x for x in text.split("\n")
                        if x.strip()
                    ]
                )
            }
        })


    instructions = {

        "summary":
            "لخص الكتاب بالعربية في نقاط واضحة.",

        "ideas":
            "استخرج أهم الأفكار والمحاور في الكتاب.",

        "questions":
            "أنشئ أسئلة وأجوبة تساعد على فهم الكتاب.",

        "simple":
            "اشرح محتوى الكتاب بطريقة بسيطة ومفهومة.",

        "translation":
            "ترجم أهم محتوى الكتاب إلى العربية مع الحفاظ على المعنى."

    }

    instruction = instructions.get(
        action,
        instructions["summary"]
    )

    prompt = f"""
أنت مساعد منصة كتب لينك.

عنوان الكتاب:
{book["title"]}

المؤلف:
{book["author"] or "غير محدد"}

المطلوب:
{instruction}

محتوى الكتاب أو المعلومات المتاحة:
{text}
"""

    answer = ai_answer(prompt)

    return jsonify({
        "answer": answer
    })


@app.post("/api/chat")
def chat():

    data = request.get_json(
        silent=True
    ) or {}

    message = str(
        data.get("message", "")
    ).strip()

    if not message:

        return jsonify({
            "error": "الرسالة فارغة"
        }), 400

    book = data.get(
        "book"
    ) or {}

    context = ""

    if book:

        context = f"""
الكتاب المحدد:
العنوان: {book.get("title","")}
المؤلف: {book.get("author","")}
الوصف: {book.get("description","")}
"""

    prompt = f"""
أنت المساعد الذكي لمنصة كتب لينك.

أجب باللغة العربية بوضوح واختصار مفيد.

{context}

سؤال المستخدم:
{message}
"""

    answer = ai_answer(prompt)

    return jsonify({
        "answer": answer
    })


# =========================================================
# تشغيل
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
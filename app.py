import os
import sqlite3
import uuid
import requests
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


# =========================================================
# الإعدادات
# =========================================================

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "books.db")
UPLOADS = os.path.join(BASE, "uploads")

os.makedirs(UPLOADS, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024


# =========================================================
# مفاتيح الخدمات
# =========================================================

GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)

MISTRAL_MODEL = os.getenv(
    "MISTRAL_MODEL",
    "mistral-small-latest"
)

HF_MODEL = os.getenv(
    "HF_MODEL",
    "Qwen/Qwen2.5-7B-Instruct"
)

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openai/gpt-4o-mini"
)

CEREBRAS_MODEL = os.getenv(
    "CEREBRAS_MODEL",
    "llama-3.3-70b"
)


# =========================================================
# قاعدة البيانات
# =========================================================

def get_db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def add_column(con, table, column, definition):
    try:
        con.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )
    except sqlite3.OperationalError:
        pass


def init_db():

    con = get_db()

    con.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT,
        isbn TEXT,
        year TEXT,
        category TEXT,
        deal_type TEXT,
        price REAL DEFAULT 0,
        rarity TEXT,
        condition TEXT,
        language TEXT,
        description TEXT,
        tags TEXT,
        cover TEXT,
        pdf TEXT,
        extracted_text TEXT,
        views INTEGER DEFAULT 0,
        favorites INTEGER DEFAULT 0,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # دعم قواعد البيانات القديمة
    add_column(con, "books", "condition", "TEXT")
    add_column(con, "books", "language", "TEXT")
    add_column(con, "tags", "dummy", "TEXT") if False else None
    add_column(con, "books", "tags", "TEXT")
    add_column(con, "books", "extracted_text", "TEXT")
    add_column(con, "books", "views", "INTEGER DEFAULT 0")
    add_column(con, "books", "favorites", "INTEGER DEFAULT 0")
    add_column(con, "books", "notes", "TEXT")

    con.execute("""
    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER UNIQUE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER,
        action TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS exchanges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER,
        wanted TEXT,
        message TEXT,
        status TEXT DEFAULT 'مفتوح',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    con.commit()
    con.close()


init_db()


# =========================================================
# الصفحة والملفات
# =========================================================

@app.route("/")
def index():
    return send_from_directory(BASE, "index.html")


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOADS, filename)


# =========================================================
# PDF
# =========================================================

def extract_pdf_text(filename):

    if not filename or PdfReader is None:
        return ""

    path = os.path.join(UPLOADS, filename)

    if not os.path.exists(path):
        return ""

    try:

        reader = PdfReader(path)

        parts = []

        max_pages = min(len(reader.pages), 100)

        for page in reader.pages[:max_pages]:

            try:

                text = page.extract_text() or ""

                if text.strip():
                    parts.append(text)

            except Exception:
                continue

        return "\n\n".join(parts)[:100000]

    except Exception as e:

        print("PDF:", repr(e))
        return ""


# =========================================================
# تحويل الكتاب إلى JSON
# =========================================================

def book_json(b):

    return {
        "id": b["id"],
        "title": b["title"] or "",
        "author": b["author"] or "",
        "isbn": b["isbn"] or "",
        "year": b["year"] or "",
        "category": b["category"] or "",
        "deal_type": b["deal_type"] or "",
        "price": b["price"] or 0,
        "rarity": b["rarity"] or "",
        "condition": b["condition"] or "",
        "language": b["language"] or "",
        "description": b["description"] or "",
        "tags": b["tags"] or "",
        "image": "/uploads/" + b["cover"] if b["cover"] else "",
        "pdf": "/uploads/" + b["pdf"] if b["pdf"] else "",
        "views": b["views"] or 0,
        "favorites": b["favorites"] or 0,
        "has_text": bool(b["extracted_text"]),
        "notes": b["notes"] or "",
        "source": "منصة الكتب"
    }


# =========================================================
# البحث المحلي
# =========================================================

def local_search(
    q="",
    author="",
    year="",
    category=""
):

    con = get_db()

    sql = """
    SELECT *
    FROM books
    WHERE 1=1
    """

    values = []

    if q:

        sql += """
        AND (
            title LIKE ?
            OR author LIKE ?
            OR isbn LIKE ?
            OR description LIKE ?
            OR category LIKE ?
            OR tags LIKE ?
        )
        """

        x = "%" + q + "%"

        values.extend([
            x, x, x, x, x, x
        ])

    if author:

        sql += " AND author LIKE ?"
        values.append("%" + author + "%")

    if year:

        sql += " AND year LIKE ?"
        values.append("%" + year + "%")

    if category:

        sql += " AND category LIKE ?"
        values.append("%" + category + "%")

    sql += """
    ORDER BY created_at DESC
    LIMIT 100
    """

    rows = con.execute(
        sql,
        values
    ).fetchall()

    con.close()

    return [book_json(x) for x in rows]


# =========================================================
# Google Books
# =========================================================

def google_books(
    q,
    author="",
    year=""
):

    query = q or "books"

    if author:
        query += " inauthor:" + author

    if year:
        query += " " + year

    params = {
        "q": query,
        "maxResults": 40,
        "printType": "books"
    }

    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY

    try:

        response = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params=params,
            timeout=20
        )

        if response.status_code != 200:
            return []

        data = response.json()

        results = []

        for item in data.get("items", []):

            info = item.get(
                "volumeInfo",
                {}
            )

            images = info.get(
                "imageLinks",
                {}
            )

            image = (
                images.get("thumbnail")
                or
                images.get("smallThumbnail")
                or
                ""
            )

            image = image.replace(
                "http://",
                "https://"
            )

            isbn = ""

            for identifier in info.get(
                "industryIdentifiers",
                []
            ):

                if identifier.get("type") in (
                    "ISBN_13",
                    "ISBN_10"
                ):

                    isbn = identifier.get(
                        "identifier",
                        ""
                    )

                    break

            authors = info.get(
                "authors",
                []
            )

            categories = info.get(
                "categories",
                []
            )

            results.append({

                "id":
                    item.get("id"),

                "title":
                    info.get(
                        "title",
                        "بدون عنوان"
                    ),

                "author":
                    ", ".join(authors),

                "isbn":
                    isbn,

                "year":
                    info.get(
                        "publishedDate",
                        ""
                    ),

                "language":
                    info.get(
                        "language",
                        ""
                    ),

                "description":
                    info.get(
                        "description",
                        ""
                    ),

                "category":
                    categories[0]
                    if categories
                    else "",

                "image":
                    image,

                "link":
                    info.get(
                        "infoLink",
                        ""
                    ),

                "source":
                    "Google Books"

            })

        return results

    except Exception as e:

        print(
            "Google Books:",
            repr(e)
        )

        return []


# =========================================================
# رفع كتاب
# =========================================================

@app.route(
    "/api/upload",
    methods=["POST"]
)
def upload():

    title = request.form.get(
        "title",
        ""
    ).strip()

    if not title:

        return jsonify({
            "error":
                "عنوان الكتاب مطلوب"
        }), 400

    author = request.form.get(
        "author",
        ""
    ).strip()

    year = request.form.get(
        "year",
        ""
    ).strip()

    isbn = request.form.get(
        "isbn",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    deal_type = request.form.get(
        "deal_type",
        "خاص"
    ).strip()

    rarity = request.form.get(
        "rarity",
        ""
    ).strip()

    condition = request.form.get(
        "condition",
        ""
    ).strip()

    language = request.form.get(
        "language",
        ""
    ).strip()

    tags = request.form.get(
        "tags",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    try:

        price = float(
            request.form.get(
                "price",
                "0"
            ) or 0
        )

    except Exception:

        price = 0

    cover_name = ""
    pdf_name = ""
    extracted_text = ""

    cover = request.files.get(
        "cover"
    )

    pdf = request.files.get(
        "pdf"
    )

    # الغلاف
    if cover and cover.filename:

        original = secure_filename(
            cover.filename
        )

        if "." not in original:

            return jsonify({
                "error":
                    "الغلاف غير صحيح"
            }), 400

        ext = original.rsplit(
            ".",
            1
        )[-1].lower()

        if ext not in {
            "jpg",
            "jpeg",
            "png",
            "webp"
        }:

            return jsonify({
                "error":
                    "صيغة الغلاف غير مدعومة"
            }), 400

        cover_name = (
            uuid.uuid4().hex
            + "."
            + ext
        )

        cover.save(
            os.path.join(
                UPLOADS,
                cover_name
            )
        )

    # PDF
    if pdf and pdf.filename:

        if not pdf.filename.lower().endswith(
            ".pdf"
        ):

            return jsonify({
                "error":
                    "الملف يجب أن يكون PDF"
            }), 400

        pdf_name = (
            uuid.uuid4().hex
            + ".pdf"
        )

        pdf_path = os.path.join(
            UPLOADS,
            pdf_name
        )

        pdf.save(pdf_path)

        extracted_text = extract_pdf_text(
            pdf_name
        )

    con = get_db()

    cur = con.execute("""
    INSERT INTO books (
        title,
        author,
        isbn,
        year,
        category,
        deal_type,
        price,
        rarity,
        condition,
        language,
        description,
        tags,
        cover,
        pdf,
        extracted_text
    )
    VALUES (
        ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
    )
    """, (
        title,
        author,
        isbn,
        year,
        category,
        deal_type,
        price,
        rarity,
        condition,
        language,
        description,
        tags,
        cover_name,
        pdf_name,
        extracted_text
    ))

    con.commit()

    book_id = cur.lastrowid

    con.close()

    return jsonify({
        "ok": True,
        "id": book_id,
        "message": "تمت إضافة الكتاب إلى المنصة"
    })


# =========================================================
# جميع الكتب
# =========================================================

@app.route("/api/books")
def books_api():

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

    category = request.args.get(
        "category",
        ""
    ).strip()

    local = local_search(
        q,
        author,
        year,
        category
    )

    external = google_books(
        q or "books",
        author,
        year
    )

    seen = set()

    combined = []

    for book in local + external:

        key = (
            str(
                book.get("isbn")
                or ""
            )
            or
            str(
                book.get("title")
                or ""
            )
        ).lower().strip()

        if key and key in seen:
            continue

        if key:
            seen.add(key)

        combined.append(book)

    return jsonify({
        "items": combined,
        "local_count": len(local),
        "google_count": len(external)
    })


# =========================================================
# تفاصيل كتاب
# =========================================================

@app.route(
    "/api/book/<int:book_id>"
)
def get_book(book_id):

    con = get_db()

    book = con.execute(
        "SELECT * FROM books WHERE id=?",
        (book_id,)
    ).fetchone()

    if not book:

        con.close()

        return jsonify({
            "error":
                "الكتاب غير موجود"
        }), 404

    con.execute(
        "UPDATE books SET views=views+1 WHERE id=?",
        (book_id,)
    )

    con.execute("""
    INSERT INTO history (
        book_id,
        action
    )
    VALUES (?,?)
    """, (
        book_id,
        "view"
    ))

    con.commit()

    book = con.execute(
        "SELECT * FROM books WHERE id=?",
        (book_id,)
    ).fetchone()

    con.close()

    return jsonify(
        book_json(book)
    )


# =========================================================
# المفضلة
# =========================================================

@app.route(
    "/api/favorite/<int:book_id>",
    methods=["POST"]
)
def favorite(book_id):

    con = get_db()

    exists = con.execute(
        "SELECT id FROM favorites WHERE book_id=?",
        (book_id,)
    ).fetchone()

    if exists:

        con.execute(
            "DELETE FROM favorites WHERE book_id=?",
            (book_id,)
        )

        con.execute(
            """
            UPDATE books
            SET favorites=MAX(favorites-1,0)
            WHERE id=?
            """,
            (book_id,)
        )

        state = False

    else:

        con.execute(
            """
            INSERT OR IGNORE INTO favorites(book_id)
            VALUES (?)
            """,
            (book_id,)
        )

        con.execute(
            """
            UPDATE books
            SET favorites=favorites+1
            WHERE id=?
            """,
            (book_id,)
        )

        state = True

    con.commit()

    con.close()

    return jsonify({
        "ok": True,
        "favorite": state
    })


@app.route("/api/favorites")
def favorites():

    con = get_db()

    rows = con.execute("""
    SELECT books.*
    FROM books
    INNER JOIN favorites
    ON books.id=favorites.book_id
    ORDER BY favorites.created_at DESC
    """).fetchall()

    con.close()

    return jsonify({
        "items":
            [book_json(x) for x in rows]
    })


# =========================================================
# سجل القراءة
# =========================================================

@app.route("/api/history")
def history():

    con = get_db()

    rows = con.execute("""
    SELECT books.*
    FROM history
    INNER JOIN books
    ON books.id=history.book_id
    WHERE history.action='view'
    GROUP BY books.id
    ORDER BY MAX(history.created_at) DESC
    LIMIT 30
    """).fetchall()

    con.close()

    return jsonify({
        "items":
            [book_json(x) for x in rows]
    })


# =========================================================
# ملاحظات
# =========================================================

@app.route(
    "/api/book/<int:book_id>/notes",
    methods=["POST"]
)
def save_notes(book_id):

    data = request.get_json(
        silent=True
    ) or {}

    notes = str(
        data.get(
            "notes",
            ""
        )
    )

    con = get_db()

    con.execute(
        """
        UPDATE books
        SET notes=?
        WHERE id=?
        """,
        (
            notes,
            book_id
        )
    )

    con.commit()
    con.close()

    return jsonify({
        "ok": True
    })


# =========================================================
# الكتب المعروضة للبيع
# =========================================================

@app.route("/api/market")
def market():

    con = get_db()

    rows = con.execute("""
    SELECT *
    FROM books
    WHERE LOWER(deal_type) LIKE '%بيع%'
       OR LOWER(deal_type) LIKE '%sale%'
       OR LOWER(deal_type) LIKE '%عرض للبيع%'
    ORDER BY created_at DESC
    LIMIT 100
    """).fetchall()

    con.close()

    return jsonify({
        "items":
            [book_json(x) for x in rows]
    })


# =========================================================
# كتب التبادل
# =========================================================

@app.route(
    "/api/exchange",
    methods=["POST"]
)
def create_exchange():

    data = request.get_json(
        silent=True
    ) or {}

    book_id = data.get("book_id")

    if not book_id:

        return jsonify({
            "error":
                "معرف الكتاب مطلوب"
        }), 400

    wanted = str(
        data.get(
            "wanted",
            ""
        )
    ).strip()

    message = str(
        data.get(
            "message",
            ""
        )
    ).strip()

    con = get_db()

    con.execute("""
    INSERT INTO exchanges (
        book_id,
        wanted,
        message
    )
    VALUES (?,?,?)
    """, (
        int(book_id),
        wanted,
        message
    ))

    con.commit()
    con.close()

    return jsonify({
        "ok": True,
        "message":
            "تم تسجيل طلب التبادل"
    })


@app.route("/api/exchanges")
def exchanges():

    con = get_db()

    rows = con.execute("""
    SELECT
        exchanges.*,
        books.title,
        books.author,
        books.cover
    FROM exchanges
    LEFT JOIN books
    ON books.id=exchanges.book_id
    ORDER BY exchanges.created_at DESC
    LIMIT 100
    """).fetchall()

    result = []

    for x in rows:

        result.append({
            "id": x["id"],
            "book_id": x["book_id"],
            "title": x["title"] or "",
            "author": x["author"] or "",
            "wanted": x["wanted"] or "",
            "message": x["message"] or "",
            "status": x["status"] or "",
            "image":
                "/uploads/" + x["cover"]
                if x["cover"]
                else ""
        })

    con.close()

    return jsonify({
        "items": result
    })


# =========================================================
# إحصائيات المنصة
# =========================================================

@app.route("/api/stats")
def stats():

    con = get_db()

    total = con.execute(
        "SELECT COUNT(*) c FROM books"
    ).fetchone()["c"]

    sale = con.execute("""
    SELECT COUNT(*) c
    FROM books
    WHERE deal_type LIKE '%بيع%'
    """).fetchone()["c"]

    exchange = con.execute("""
    SELECT COUNT(*) c
    FROM books
    WHERE deal_type LIKE '%تبادل%'
    """).fetchone()["c"]

    rare = con.execute("""
    SELECT COUNT(*) c
    FROM books
    WHERE rarity LIKE '%نادر%'
    """).fetchone()["c"]

    views = con.execute(
        "SELECT COALESCE(SUM(views),0) c FROM books"
    ).fetchone()["c"]

    favorites = con.execute(
        "SELECT COALESCE(SUM(favorites),0) c FROM books"
    ).fetchone()["c"]

    con.close()

    return jsonify({
        "books": total,
        "sale": sale,
        "exchange": exchange,
        "rare": rare,
        "views": views,
        "favorites": favorites
    })


# =========================================================
# Tavily
# =========================================================

def tavily_search(q):

    if not TAVILY_API_KEY:
        return []

    try:

        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": q,
                "search_depth": "basic",
                "max_results": 6,
                "include_answer": True
            },
            timeout=25
        )

        if response.status_code != 200:
            return []

        return response.json().get(
            "results",
            []
        )

    except Exception:

        return []


# =========================================================
# Gemini
# =========================================================

def gemini(prompt):

    if not GEMINI_API_KEY:
        return None

    try:

        url = (
            "https://generativelanguage.googleapis.com/"
            "v1beta/models/"
            + GEMINI_MODEL
            + ":generateContent"
        )

        response = requests.post(
            url,
            params={
                "key":
                    GEMINI_API_KEY
            },
            json={
                "contents": [{
                    "parts": [{
                        "text":
                            prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 4000
                }
            },
            timeout=90
        )

        if response.status_code != 200:
            return None

        data = response.json()

        candidates = data.get(
            "candidates",
            []
        )

        if not candidates:
            return None

        parts = candidates[0].get(
            "content",
            {}
        ).get(
            "parts",
            []
        )

        text = "\n".join(
            p.get("text", "")
            for p in parts
            if isinstance(p, dict)
        ).strip()

        return text or None

    except Exception:

        return None


# =========================================================
# OpenAI Compatible
# =========================================================

def compatible_ai(
    api_key,
    url,
    model,
    prompt,
    extra_headers=None
):

    if not api_key:
        return None

    headers = {
        "Authorization":
            "Bearer " + api_key,
        "Content-Type":
            "application/json"
    }

    if extra_headers:
        headers.update(
            extra_headers
        )

    try:

        response = requests.post(
            url,
            headers=headers,
            json={
                "model":
                    model,
                "messages": [
                    {
                        "role":
                            "system",
                        "content":
                            "أنت مساعد متخصص في الكتب والنصوص. أجب بالعربية عندما يكون السؤال بالعربية. لا تخترع معلومات غير موجودة."
                    },
                    {
                        "role":
                            "user",
                        "content":
                            prompt
                    }
                ],
                "temperature":
                    0.3,
                "max_tokens":
                    4000
            },
            timeout=120
        )

        if response.status_code != 200:
            return None

        data = response.json()

        choices = data.get(
            "choices",
            []
        )

        if not choices:
            return None

        content = (
            choices[0]
            .get("message", {})
            .get("content", "")
        )

        if isinstance(content, list):

            content = "\n".join(
                str(x.get("text", ""))
                for x in content
                if isinstance(x, dict)
            )

        return str(
            content or ""
        ).strip() or None

    except Exception:

        return None


def groq(prompt):

    return compatible_ai(
        GROQ_API_KEY,
        "https://api.groq.com/openai/v1/chat/completions",
        GROQ_MODEL,
        prompt
    )


def openrouter(prompt):

    return compatible_ai(
        OPENROUTER_API_KEY,
        "https://openrouter.ai/api/v1/chat/completions",
        OPENROUTER_MODEL,
        prompt,
        {
            "HTTP-Referer":
                os.getenv(
                    "APP_URL",
                    ""
                ),
            "X-Title":
                "معرض الكتب النادرة والقيمة"
        }
    )


def mistral(prompt):

    return compatible_ai(
        MISTRAL_API_KEY,
        "https://api.mistral.ai/v1/chat/completions",
        MISTRAL_MODEL,
        prompt
    )


def huggingface(prompt):

    return compatible_ai(
        HF_TOKEN,
        "https://router.huggingface.co/v1/chat/completions",
        HF_MODEL,
        prompt
    )


def cerebras(prompt):

    return compatible_ai(
        CEREBRAS_API_KEY,
        "https://api.cerebras.ai/v1/chat/completions",
        CEREBRAS_MODEL,
        prompt
    )


# =========================================================
# الذكاء الاصطناعي الاحتياطي
# =========================================================

def ai_answer(prompt):

    providers = [
        ("gemini", gemini),
        ("cerebras", cerebras),
        ("groq", groq),
        ("openrouter", openrouter),
        ("mistral", mistral),
        ("huggingface", huggingface)
    ]

    for name, provider in providers:

        try:

            answer = provider(prompt)

            if answer:
                return answer.strip(), name

        except Exception as e:

            print(
                name,
                "error:",
                repr(e)
            )

    return None, None


# =========================================================
# المساعد الذكي
# =========================================================

@app.route(
    "/api/chat",
    methods=["POST"]
)
def chat():

    data = request.get_json(
        silent=True
    ) or {}

    message = str(
        data.get(
            "message",
            ""
        )
    ).strip()

    book = data.get(
        "book",
        {}
    ) or {}

    if not message:

        return jsonify({
            "answer":
                "اكتب طلبك."
        }), 400

    title = str(
        book.get(
            "title",
            ""
        )
    )

    author = str(
        book.get(
            "author",
            ""
        )
    )

    description = str(
        book.get(
            "description",
            ""
        )
    )

    book_text = ""

    book_id = book.get("id")

    if book_id:

        try:

            con = get_db()

            row = con.execute(
                """
                SELECT extracted_text
                FROM books
                WHERE id=?
                """,
                (int(book_id),)
            ).fetchone()

            con.close()

            if row:
                book_text = (
                    row["extracted_text"]
                    or ""
                )

        except Exception:
            pass

    book_text = book_text[:60000]

    prompt = f"""
أنت المساعد الذكي داخل منصة
«الكتب النادرة والقيمة».

ساعد القارئ في:
التلخيص، التحليل، استخراج الأفكار،
شرح الكلمات، الترجمة، الأسئلة والأجوبة،
تبسيط المحتوى، ومناقشة الكتاب.

العنوان:
{title}

المؤلف:
{author}

الوصف:
{description}

النص المستخرج من الكتاب:
{book_text}

طلب القارئ:
{message}

قواعد:
- اعتمد على النص عندما يكون متوفرًا.
- لا تدعي أنك قرأت ما ليس موجودًا.
- لا تخترع معلومات عن الكتاب.
- نظم الإجابة بعناوين ونقاط عندما يكون ذلك مفيدًا.
- إذا طلب القارئ ملخصًا، أعطه ملخصًا واضحًا.
- إذا طلب الأفكار، استخرج الأفكار الرئيسية.
"""

    answer, provider = ai_answer(
        prompt
    )

    if not answer:

        web = tavily_search(
            message + " " + title
        )

        if web:

            web_text = "\n\n".join(
                str(
                    x.get(
                        "content",
                        ""
                    )
                )
                for x in web
            )

            fallback = f"""
أجب عن طلب المستخدم اعتمادًا
على نتائج البحث التالية:

الطلب:
{message}

الكتاب:
{title}

النتائج:
{web_text[:30000]}
"""

            answer, provider = ai_answer(
                fallback
            )

    if not answer:

        return jsonify({
            "ok": False,
            "answer":
                "المساعد غير متاح حاليًا. بقية وظائف المنصة تعمل بشكل طبيعي."
        }), 503

    return jsonify({
        "ok": True,
        "answer": answer,
        "provider": provider or ""
    })


# =========================================================
# عمليات ذكية جاهزة
# =========================================================

@app.route(
    "/api/book/<int:book_id>/action",
    methods=["POST"]
)
def book_action(book_id):

    data = request.get_json(
        silent=True
    ) or {}

    action = str(
        data.get(
            "action",
            ""
        )
    ).strip()

    con = get_db()

    book = con.execute(
        "SELECT * FROM books WHERE id=?",
        (book_id,)
    ).fetchone()

    con.close()

    if not book:

        return jsonify({
            "error":
                "الكتاب غير موجود"
        }), 404

    text = book["extracted_text"] or ""

    title = book["title"] or ""
    author = book["author"] or ""
    description = book["description"] or ""

    prompts = {

        "summary": f"""
لخص الكتاب التالي بالعربية.
العنوان: {title}
المؤلف: {author}
الوصف: {description}
النص:
{text[:60000]}
أعطني ملخصًا منظمًا وواضحًا.
""",

        "ideas": f"""
استخرج أهم الأفكار والمحاور من الكتاب.
العنوان: {title}
المؤلف: {author}
النص:
{text[:60000]}
ضع كل فكرة في نقطة مستقلة مع شرح مختصر.
""",

        "questions": f"""
أنشئ أسئلة وأجوبة لفهم الكتاب.
العنوان: {title}
النص:
{text[:60000]}
أنشئ أسئلة متنوعة مع إجاباتها اعتمادًا على النص.
""",

        "simplify": f"""
اشرح محتوى الكتاب بطريقة بسيطة للقارئ.
العنوان: {title}
النص:
{text[:60000]}
""",

        "analysis": f"""
حلل الكتاب من حيث:
الموضوع، الأفكار، الحجج أو الأحداث،
وأبرز النقاط المهمة.
العنوان: {title}
المؤلف: {author}
النص:
{text[:60000]}
"""
    }

    if action not in prompts:

        return jsonify({
            "error":
                "العملية غير معروفة"
        }), 400

    answer, provider = ai_answer(
        prompts[action]
    )

    if not answer:

        return jsonify({
            "ok": False,
            "answer":
                "هذه الوظيفة تحتاج إلى توفر مساعد ذكي."
        }), 503

    return jsonify({
        "ok": True,
        "answer": answer,
        "provider": provider or ""
    })


# =========================================================
# Health
# =========================================================

@app.route("/api/health")
def health():

    return jsonify({

        "status":
            "online",

        "ai":
            bool(
                GEMINI_API_KEY
                or CEREBRAS_API_KEY
                or GROQ_API_KEY
                or OPENROUTER_API_KEY
                or MISTRAL_API_KEY
                or HF_TOKEN
            ),

        "gemini":
            bool(GEMINI_API_KEY),

        "cerebras":
            bool(CEREBRAS_API_KEY),

        "groq":
            bool(GROQ_API_KEY),

        "openrouter":
            bool(OPENROUTER_API_KEY),

        "mistral":
            bool(MISTRAL_API_KEY),

        "huggingface":
            bool(HF_TOKEN),

        "google_books":
            bool(GOOGLE_BOOKS_API_KEY),

        "tavily":
            bool(TAVILY_API_KEY),

        "pdf":
            bool(PdfReader)

    })


# =========================================================
# التشغيل
# =========================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
from flask import Flask, request, redirect, url_for, jsonify, send_from_directory, render_template_string
import sqlite3
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

# ============================================================
# مصلحة المستخدمين - مقر الولاية
# تطوير براهيمي يوسف
# ============================================================

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.join(BASE_DIR, "employees.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
PHOTO_DIR = os.path.join(UPLOAD_DIR, "photos")
DOC_DIR = os.path.join(UPLOAD_DIR, "documents")

os.makedirs(PHOTO_DIR, exist_ok=True)
os.makedirs(DOC_DIR, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024


IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
    "gif"
}

DOCUMENT_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "jpg",
    "jpeg",
    "png",
    "webp"
}


# ============================================================
# قاعدة البيانات
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            employee_number TEXT UNIQUE NOT NULL,

            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,

            rank TEXT DEFAULT '',
            department TEXT DEFAULT 'مصلحة المستخدمين',
            position TEXT DEFAULT '',

            workplace TEXT DEFAULT 'مقر الولاية',

            status TEXT DEFAULT 'نشط',

            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',

            birth_date TEXT DEFAULT '',
            recruitment_date TEXT DEFAULT '',

            grade TEXT DEFAULT '',
            category TEXT DEFAULT '',

            address TEXT DEFAULT '',

            notes TEXT DEFAULT '',

            photo TEXT DEFAULT '',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS employee_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            employee_id INTEGER NOT NULL,

            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,

            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(employee_id)
            REFERENCES employees(id)
            ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_employee_number
        ON employees(employee_number)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_employee_name
        ON employees(first_name, last_name)
    """)

    conn.commit()
    conn.close()


init_database()


# ============================================================
# أدوات
# ============================================================

def allowed_extension(filename, allowed):

    if not filename or "." not in filename:
        return False

    ext = filename.rsplit(".", 1)[1].lower()

    return ext in allowed


def unique_filename(original):

    safe = secure_filename(original)

    ext = ""

    if "." in safe:
        ext = "." + safe.rsplit(".", 1)[1].lower()

    return uuid.uuid4().hex + ext


def clean(value):

    if value is None:
        return ""

    return str(value).strip()


# ============================================================
# الصفحة الرئيسية
# ============================================================

@app.route("/")
def index():

    conn = get_db()

    employees = conn.execute("""
        SELECT *
        FROM employees
        ORDER BY id DESC
    """).fetchall()

    total = conn.execute("""
        SELECT COUNT(*)
        FROM employees
    """).fetchone()[0]

    active = conn.execute("""
        SELECT COUNT(*)
        FROM employees
        WHERE status = 'نشط'
    """).fetchone()[0]

    absent = conn.execute("""
        SELECT COUNT(*)
        FROM employees
        WHERE status IN (
            'في عطلة',
            'في إجازة مرضية'
        )
    """).fetchone()[0]

    conn.close()

    index_file = os.path.join(BASE_DIR, "index.html")

    if not os.path.exists(index_file):

        return """
        <html lang="ar" dir="rtl">
        <meta charset="UTF-8">
        <body style="font-family:Tahoma;text-align:center;padding:60px">
        <h1>تطوير براهيمي يوسف</h1>
        <h2>ملف index.html غير موجود</h2>
        <p>ضع index.html بجانب app.py</p>
        </body>
        </html>
        """

    with open(index_file, "r", encoding="utf-8") as f:
        html = f.read()

    return render_template_string(
        html,
        employees=employees,
        total=total,
        active=active,
        absent=absent
    )


# ============================================================
# إضافة موظف
# ============================================================

@app.route("/add", methods=["POST"])
def add_employee():

    employee_number = clean(
        request.form.get("employee_number")
    )

    first_name = clean(
        request.form.get("first_name")
    )

    last_name = clean(
        request.form.get("last_name")
    )

    if not employee_number:
        return "رقم الموظف مطلوب", 400

    if not first_name:
        return "الاسم مطلوب", 400

    if not last_name:
        return "اللقب مطلوب", 400


    rank = clean(request.form.get("rank"))

    department = clean(
        request.form.get("department")
    ) or "مصلحة المستخدمين"

    position = clean(
        request.form.get("position")
    )

    workplace = clean(
        request.form.get("workplace")
    ) or "مقر الولاية"

    status = clean(
        request.form.get("status")
    ) or "نشط"

    phone = clean(
        request.form.get("phone")
    )

    email = clean(
        request.form.get("email")
    )

    birth_date = clean(
        request.form.get("birth_date")
    )

    recruitment_date = clean(
        request.form.get("recruitment_date")
    )

    grade = clean(
        request.form.get("grade")
    )

    category = clean(
        request.form.get("category")
    )

    address = clean(
        request.form.get("address")
    )

    notes = clean(
        request.form.get("notes")
    )


    photo_name = ""


    # ========================================================
    # صورة الموظف
    # ========================================================

    photo = request.files.get("photo")

    if photo and photo.filename:

        if not allowed_extension(
            photo.filename,
            IMAGE_EXTENSIONS
        ):
            return "صيغة صورة غير مسموحة", 400

        photo_name = unique_filename(
            photo.filename
        )

        photo.save(
            os.path.join(
                PHOTO_DIR,
                photo_name
            )
        )


    conn = get_db()

    try:

        cursor = conn.execute("""
            INSERT INTO employees (

                employee_number,

                first_name,
                last_name,

                rank,
                department,
                position,

                workplace,

                status,

                phone,
                email,

                birth_date,
                recruitment_date,

                grade,
                category,

                address,

                notes,

                photo,

                created_at

            )

            VALUES (
                ?, ?, ?,
                ?, ?, ?,
                ?,
                ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?,
                ?,
                ?,
                ?
            )
        """, (

            employee_number,

            first_name,
            last_name,

            rank,
            department,
            position,

            workplace,

            status,

            phone,
            email,

            birth_date,
            recruitment_date,

            grade,
            category,

            address,

            notes,

            photo_name,

            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ))

        employee_id = cursor.lastrowid


        # ====================================================
        # ملفات الموظف
        # ====================================================

        files = request.files.getlist(
            "documents"
        )

        for uploaded in files:

            if not uploaded:
                continue

            if not uploaded.filename:
                continue

            if not allowed_extension(
                uploaded.filename,
                DOCUMENT_EXTENSIONS
            ):
                continue

            stored_name = unique_filename(
                uploaded.filename
            )

            uploaded.save(
                os.path.join(
                    DOC_DIR,
                    stored_name
                )
            )

            conn.execute("""
                INSERT INTO employee_files (

                    employee_id,
                    filename,
                    original_name,
                    uploaded_at

                )

                VALUES (?, ?, ?, ?)
            """, (

                employee_id,
                stored_name,
                uploaded.filename,

                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ))


        conn.commit()

    except sqlite3.IntegrityError:

        conn.rollback()

        if photo_name:

            path = os.path.join(
                PHOTO_DIR,
                photo_name
            )

            if os.path.exists(path):
                os.remove(path)

        conn.close()

        return """
        <html lang="ar" dir="rtl">
        <meta charset="UTF-8">
        <body style="font-family:Tahoma;text-align:center;padding:50px">
        <h2>⚠️ رقم الموظف موجود مسبقًا</h2>
        <a href="/">العودة</a>
        </body>
        </html>
        """, 409

    except Exception as e:

        conn.rollback()
        conn.close()

        return f"""
        <html lang="ar" dir="rtl">
        <meta charset="UTF-8">
        <body style="font-family:Tahoma;text-align:center;padding:50px">
        <h2>حدث خطأ أثناء الحفظ</h2>
        <p>{e}</p>
        <a href="/">العودة</a>
        </body>
        </html>
        """, 500


    conn.close()

    return redirect(url_for("index"))


# ============================================================
# صورة الموظف
# ============================================================

@app.route("/photos/<path:filename>")
def photos(filename):

    return send_from_directory(
        PHOTO_DIR,
        filename
    )


# ============================================================
# ملفات الموظفين
# ============================================================

@app.route("/documents/<path:filename>")
def documents(filename):

    return send_from_directory(
        DOC_DIR,
        filename,
        as_attachment=False
    )


# ============================================================
# ملف الموظف الكامل
# ============================================================

@app.route("/employee/<int:employee_id>")
def employee(employee_id):

    conn = get_db()

    employee_data = conn.execute("""
        SELECT *
        FROM employees
        WHERE id = ?
    """, (
        employee_id,
    )).fetchone()

    if not employee_data:

        conn.close()

        return "الموظف غير موجود", 404


    files = conn.execute("""
        SELECT *
        FROM employee_files
        WHERE employee_id = ?
        ORDER BY id DESC
    """, (
        employee_id,
    )).fetchall()

    conn.close()


    return render_template_string("""

<!DOCTYPE html>

<html lang="ar" dir="rtl">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width,initial-scale=1">

<title>ملف الموظف</title>

<style>

*{
box-sizing:border-box
}

body{
margin:0;
font-family:Tahoma,Arial;
background:#eef3f8;
color:#172033
}

header{
background:linear-gradient(
135deg,
#062b45,
#075985,
#0ea5e9
);
color:white;
padding:22px
}

.dev{
color:#ffe500;
font-weight:bold
}

.container{
max-width:1100px;
margin:auto;
padding:20px
}

.box{
background:white;
border-radius:18px;
padding:22px;
margin-bottom:18px;
box-shadow:0 5px 20px #0001
}

.profile{
display:flex;
gap:25px;
align-items:center
}

.photo{
width:150px;
height:150px;
object-fit:cover;
border-radius:20px
}

.no-photo{
width:150px;
height:150px;
display:flex;
align-items:center;
justify-content:center;
background:#cbd5e1;
border-radius:20px;
font-size:60px
}

.info{
display:grid;
grid-template-columns:1fr 1fr;
gap:10px
}

.item{
padding:13px;
background:#f8fafc;
border-radius:10px
}

.label{
display:block;
font-size:13px;
color:#64748b
}

.value{
display:block;
font-weight:bold;
margin-top:5px
}

.button{
display:inline-block;
padding:12px 17px;
border-radius:10px;
background:#0284c7;
color:white;
text-decoration:none;
font-weight:bold;
margin:4px
}

.file{
padding:12px;
border-bottom:1px solid #e2e8f0
}

@media(max-width:650px){

.profile{
flex-direction:column;
text-align:center
}

.info{
grid-template-columns:1fr
}

}

</style>

</head>

<body>

<header>

<div class="dev">
تطوير براهيمي يوسف
</div>

<h1>
الملف الإداري للموظف
</h1>

</header>


<main class="container">


<div class="box">

<div class="profile">

{% if employee.photo %}

<img
class="photo"
src="/photos/{{ employee.photo }}"
>

{% else %}

<div class="no-photo">
👤
</div>

{% endif %}


<div>

<h2>
{{ employee.first_name }}
{{ employee.last_name }}
</h2>

<p>
رقم الموظف:
<strong>
{{ employee.employee_number }}
</strong>
</p>

<a
class="button"
href="/absence/{{ employee.id }}"
target="_blank"
>
📄 استخراج رخصة غياب
</a>

</div>

</div>

</div>


<div class="box">

<h2>
المعلومات الإدارية
</h2>

<div class="info">


<div class="item">
<span class="label">الاسم</span>
<span class="value">{{ employee.first_name }}</span>
</div>


<div class="item">
<span class="label">اللقب</span>
<span class="value">{{ employee.last_name }}</span>
</div>


<div class="item">
<span class="label">رقم الموظف</span>
<span class="value">{{ employee.employee_number }}</span>
</div>


<div class="item">
<span class="label">الرتبة</span>
<span class="value">{{ employee.rank or "—" }}</span>
</div>


<div class="item">
<span class="label">المصلحة</span>
<span class="value">{{ employee.department }}</span>
</div>


<div class="item">
<span class="label">المنصب</span>
<span class="value">{{ employee.position or "—" }}</span>
</div>


<div class="item">
<span class="label">مكان التواجد</span>
<span class="value">{{ employee.workplace }}</span>
</div>


<div class="item">
<span class="label">الحالة</span>
<span class="value">{{ employee.status }}</span>
</div>


<div class="item">
<span class="label">الدرجة</span>
<span class="value">{{ employee.grade or "—" }}</span>
</div>


<div class="item">
<span class="label">الصنف</span>
<span class="value">{{ employee.category or "—" }}</span>
</div>


<div class="item">
<span class="label">تاريخ التوظيف</span>
<span class="value">{{ employee.recruitment_date or "—" }}</span>
</div>


<div class="item">
<span class="label">تاريخ الميلاد</span>
<span class="value">{{ employee.birth_date or "—" }}</span>
</div>


<div class="item">
<span class="label">الهاتف</span>
<span class="value">{{ employee.phone or "—" }}</span>
</div>


<div class="item">
<span class="label">البريد الإلكتروني</span>
<span class="value">{{ employee.email or "—" }}</span>
</div>


<div class="item">
<span class="label">العنوان</span>
<span class="value">{{ employee.address or "—" }}</span>
</div>


</div>

</div>


<div class="box">

<h2>
📁 وثائق الموظف
</h2>

{% if files %}

{% for file in files %}

<div class="file">

📄

<a
href="/documents/{{ file.filename }}"
target="_blank"
>
{{ file.original_name }}
</a>

</div>

{% endfor %}

{% else %}

<p>
لا توجد وثائق مرفوعة.
</p>

{% endif %}

</div>


<div class="box">

<h2>
📝 الملاحظات
</h2>

<p>
{{ employee.notes or "لا توجد ملاحظات." }}
</p>

</div>


</main>

</body>

</html>

""",
        employee=employee_data,
        files=files
    )


# ============================================================
# رخصة الغياب
# ============================================================

@app.route("/absence/<int:employee_id>")
def absence(employee_id):

    conn = get_db()

    employee_data = conn.execute("""
        SELECT *
        FROM employees
        WHERE id = ?
    """, (
        employee_id,
    )).fetchone()

    conn.close()

    if not employee_data:
        return "الموظف غير موجود", 404


    today = datetime.now().strftime(
        "%Y-%m-%d"
    )


    return render_template_string("""

<!DOCTYPE html>

<html lang="ar" dir="rtl">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width,initial-scale=1">

<title>رخصة غياب</title>

<style>

body{
margin:0;
background:#ddd;
font-family:"Times New Roman",Tahoma,serif
}

.actions{
text-align:center;
padding:18px
}

button{
padding:13px 25px;
border:0;
border-radius:9px;
background:#075985;
color:white;
font-weight:bold;
cursor:pointer;
font-size:16px
}

.paper{
width:210mm;
min-height:297mm;
margin:15px auto;
background:white;
padding:24mm 22mm;
box-sizing:border-box
}

.header{
text-align:center;
line-height:2;
font-size:17px
}

.title{
text-align:center;
font-size:27px;
font-weight:bold;
text-decoration:underline;
margin-top:45px;
margin-bottom:45px
}

.content{
font-size:19px;
line-height:2.4;
text-align:justify
}

.signature{
margin-top:70px;
text-align:left;
font-weight:bold
}

.footer{
margin-top:100px;
text-align:center;
font-size:11px;
color:#777;
border-top:1px solid #aaa;
padding-top:10px
}

@media print{

body{
background:white
}

.actions{
display:none
}

.paper{
margin:0;
box-shadow:none
}

}

</style>

</head>

<body>

<div class="actions">

<button onclick="window.print()">
🖨️ طباعة / حفظ PDF
</button>

</div>


<div class="paper">


<div class="header">

<strong>
الجمهورية الجزائرية الديمقراطية الشعبية
</strong>

<strong>
ولاية ........................................
</strong>

<strong>
مقر الولاية
</strong>

<strong>
مصلحة المستخدمين
</strong>

</div>


<div class="title">
رخصة غياب
</div>


<div class="content">

<p>
يشهد السيد/السيدة مسؤول مصلحة المستخدمين أن الموظف:
</p>


<p>

الاسم:
<strong>
{{ employee.first_name }}
</strong>

<br>

اللقب:
<strong>
{{ employee.last_name }}
</strong>

<br>

رقم الموظف:
<strong>
{{ employee.employee_number }}
</strong>

<br>

الرتبة:
<strong>
{{ employee.rank or "................................" }}
</strong>

<br>

المصلحة:
<strong>
{{ employee.department }}
</strong>

<br>

مكان العمل:
<strong>
{{ employee.workplace }}
</strong>

</p>


<p>
مرخص له بالغياب عن العمل:
</p>


<p style="text-align:center">

من:
....................................................

<br>

إلى:
....................................................

</p>


<p>
وذلك وفقًا للإجراءات والتنظيمات المعمول بها.
</p>


<p>

حررت بتاريخ:

<strong>
{{ today }}
</strong>

</p>

</div>


<div class="signature">

مسؤول مصلحة المستخدمين

<br><br><br>

الإمضاء والختم

</div>


<div class="footer">
تطوير براهيمي يوسف
</div>


</div>

</body>

</html>

""",
        employee=employee_data,
        today=today
    )


# ============================================================
# البحث
# ============================================================

@app.route("/search")
def search():

    q = clean(
        request.args.get("q")
    )

    conn = get_db()

    if q:

        pattern = "%" + q + "%"

        rows = conn.execute("""
            SELECT *
            FROM employees

            WHERE employee_number LIKE ?
               OR first_name LIKE ?
               OR last_name LIKE ?
               OR rank LIKE ?
               OR department LIKE ?
               OR position LIKE ?
               OR workplace LIKE ?

            ORDER BY id DESC
        """, (
            pattern,
            pattern,
            pattern,
            pattern,
            pattern,
            pattern,
            pattern
        )).fetchall()

    else:

        rows = conn.execute("""
            SELECT *
            FROM employees
            ORDER BY id DESC
        """).fetchall()


    conn.close()


    result = []

    for row in rows:

        result.append({
            "id": row["id"],
            "employee_number": row["employee_number"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "rank": row["rank"],
            "department": row["department"],
            "position": row["position"],
            "workplace": row["workplace"],
            "status": row["status"],
            "photo": row["photo"]
        })


    return jsonify(result)


# ============================================================
# الإحصائيات
# ============================================================

@app.route("/api/stats")
def api_stats():

    conn = get_db()

    total = conn.execute(
        "SELECT COUNT(*) FROM employees"
    ).fetchone()[0]

    active = conn.execute(
        "SELECT COUNT(*) FROM employees WHERE status='نشط'"
    ).fetchone()[0]

    vacation = conn.execute("""
        SELECT COUNT(*)
        FROM employees
        WHERE status='في عطلة'
    """).fetchone()[0]

    sick = conn.execute("""
        SELECT COUNT(*)
        FROM employees
        WHERE status='في إجازة مرضية'
    """).fetchone()[0]

    conn.close()

    return jsonify({
        "total": total,
        "active": active,
        "vacation": vacation,
        "sick": sick
    })


# ============================================================
# تشغيل
# ============================================================

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
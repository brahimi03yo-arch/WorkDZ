import os
import sqlite3
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# --- إعداد قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- كود الواجهة (HTML + CSS + JS) كاملاً في نص واحد ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>حملة المترشح إبراهيمي يوسف</title>
    <!-- استدعاء خط Cairo من جوجل لتحسين شكل النص -->
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Cairo', sans-serif; }
        body { line-height: 1.8; color: #2c3e50; background-color: #f8f9fa; }
        .container { width: 90%; max-width: 1200px; margin: auto; }
        h2 { text-align: center; margin-bottom: 2.5rem; color: #1a3c6e; font-size: 2.2rem; position: relative; }
        h2::after { content: ''; display: block; width: 60px; height: 4px; background: #f0c14b; margin: 10px auto 0; border-radius: 2px; }
        
        /* شريط التنقل */
        nav { background: #1a3c6e; color: #fff; padding: 1rem 0; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        nav .container { display: flex; justify-content: space-between; align-items: center; }
        .logo { font-size: 1.5rem; font-weight: 900; color: #f0c14b; }
        nav ul { display: flex; list-style: none; }
        nav ul li { margin-right: 2rem; }
        nav ul li a { color: #fff; text-decoration: none; font-weight: 700; transition: color 0.3s; font-size: 1.1rem; }
        nav ul li a:hover { color: #f0c14b; }

        /* قسم البطل */
        .hero { background: linear-gradient(rgba(26, 60, 110, 0.85), rgba(26, 60, 110, 0.85)), url('https://images.unsplash.com/photo-1540910419892-4a36d2c3266c?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80') no-repeat center center/cover; color: #fff; padding: 8rem 0; text-align: center; }
        .hero h1 { font-size: 3.5rem; margin-bottom: 1rem; font-weight: 900; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .hero p { font-size: 1.3rem; margin-bottom: 2.5rem; font-weight: 400; }
        .btn { display: inline-block; background: #f0c14b; color: #1a3c6e; padding: 1rem 2.5rem; text-decoration: none; font-weight: 900; border-radius: 50px; transition: all 0.3s; font-size: 1.1rem; box-shadow: 0 4px 15px rgba(240, 193, 75, 0.4); }
        .btn:hover { background: #fff; color: #1a3c6e; transform: translateY(-3px); }

        /* قسم النبذة */
        .about { padding: 5rem 0; background: #fff; }
        .about-content { display: flex; align-items: center; gap: 3rem; flex-wrap: wrap; }
        .about-img { flex: 1; min-width: 250px; text-align: center; }
        .about-img img { width: 250px; height: 250px; border-radius: 50%; object-fit: cover; border: 6px solid #1a3c6e; box-shadow: 0 10px 20px rgba(0,0,0,0.15); }
        .about-text { flex: 2; min-width: 300px; }
        .about-text p { font-size: 1.15rem; margin-bottom: 1rem; color: #555; }
        .about-text strong { color: #1a3c6e; }

        /* قسم البرنامج */
        .programs { padding: 5rem 0; background: #f8f9fa; }
        .program-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 2rem; }
        .program-card { background: #fff; padding: 2rem; border-radius: 12px; box-shadow: 0 5px 20px rgba(0,0,0,0.05); text-align: center; transition: transform 0.3s; border-top: 4px solid #f0c14b; }
        .program-card:hover { transform: translateY(-5px); }
        .program-card h3 { color: #1a3c6e; margin-bottom: 1rem; font-size: 1.3rem; }
        .program-card p { color: #666; }

        /* نموذج التواصل */
        .contact { padding: 5rem 0; background: #fff; }
        .contact form { max-width: 600px; margin: auto; display: flex; flex-direction: column; gap: 1.2rem; }
        .contact input, .contact textarea { padding: 1rem; border: 1px solid #ddd; border-radius: 8px; font-family: inherit; font-size: 1rem; transition: border-color 0.3s; }
        .contact input:focus, .contact textarea:focus { outline: none; border-color: #1a3c6e; }
        .contact button { background: #1a3c6e; color: #fff; padding: 1rem; border: none; border-radius: 8px; cursor: pointer; font-size: 1.1rem; font-weight: 700; transition: background 0.3s; }
        .contact button:hover { background: #142b4d; }
        #formMessage { text-align: center; margin-top: 1rem; font-weight: bold; }
        .success { color: #27ae60; }
        .error { color: #e74c3c; }

        /* التذييل والشريط الدائري */
        footer { background: #1a3c6e; color: #fff; text-align: center; padding: 3rem 0 2rem; position: relative; }
        footer p { margin-top: 1.5rem; font-size: 1rem; opacity: 0.8; }
        
        /* تصميم الشريط الدائري */
        .dev-badge {
            display: inline-flex;
            justify-content: center;
            align-items: center;
            width: 160px;
            height: 160px;
            border-radius: 50%;
            background: linear-gradient(135deg, #f0c14b, #d4a72c);
            color: #1a3c6e;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
            border: 4px dashed #fff;
            margin: 0 auto;
            transition: transform 0.5s ease;
        }
        .dev-badge:hover { transform: rotate(10deg) scale(1.05); }
        .dev-badge-content { text-align: center; padding: 10px; }
        .dev-badge-content span { display: block; font-size: 0.8rem; font-weight: 700; margin-bottom: 5px; }
        .dev-badge-content strong { display: block; font-size: 1.2rem; font-weight: 900; line-height: 1.2; }

        @media (max-width: 768px) {
            nav .container { flex-direction: column; }
            nav ul { margin-top: 1rem; }
            nav ul li { margin: 0 0.5rem; }
            .hero h1 { font-size: 2.5rem; }
            .about-content { flex-direction: column; text-align: center; }
            h2 { font-size: 1.8rem; }
        }
    </style>
</head>
<body>

    <nav>
        <div class="container">
            <div class="logo">إبراهيمي يوسف</div>
            <ul>
                <li><a href="#hero">الرئيسية</a></li>
                <li><a href="#about">من هو؟</a></li>
                <li><a href="#programs">التزاماتنا</a></li>
                <li><a href="#contact">تواصل</a></li>
            </ul>
        </div>
    </nav>

    <section id="hero" class="hero">
        <div class="container">
            <h1>صوتك.. قوة التغيير</h1>
            <p>معاً نبني غداً مشرقاً بقيادة المترشح إبراهيمي يوسف</p>
            <a href="#contact" class="btn">انضم إلى الحملة</a>
        </div>
    </section>

    <section id="about" class="about">
        <div class="container">
            <h2>المترشح إبراهيمي يوسف</h2>
            <div class="about-content">
                <div class="about-img">
                    <!-- هنا يتم استدعاء الصورة. تأكد من تسمية الصورة profile.jpg ووضعها بجانب هذا الملف -->
                    <img src="profile.jpg" alt="صورة المترشح إبراهيمي يوسف" onerror="this.src='https://via.placeholder.com/250?text=صورة+المترشح'">
                </div>
                <div class="about-text">
                    <p>أنا <strong>إبراهيمي يوسف</strong>، أؤمن إيماناً راسخاً بأن الشباب هم العمود الفقري لأي نهضة حقيقية. خبرتي الميدانية وعملي الدؤوب في خدمة المجتمع جعلتني أدرك احتياجاتكم عن قرب.</p>
                    <p>أترشح اليوم حاملاً معي برنامجاً واقعياً وطموحاً، يهدف إلى <strong>تحقيق التنمية المستدامة، محاربة البطالة، وتوفير حياة كريمة تستحقونها</strong>. رؤيتي تقوم على الشفافية، العمل الجاد، وإشراككم في صنع القرار.</p>
                </div>
            </div>
        </div>
    </section>

    <section id="programs" class="programs">
        <div class="container">
            <h2>التزاماتنا وبرنامجنا</h2>
            <div class="program-grid">
                <div class="program-card">
                    <h3>التعليم أولاً</h3>
                    <p>إصلاح شامل للمنظومة التعليمية، دعم البحث العلمي، وتوفير بيئة مدرسية محفزة للأجيال القادمة.</p>
                </div>
                <div class="program-card">
                    <h3>الصحة للجميع</h3>
                    <p>تطوير المرافق الصحية، تقريب الخدمات الطبية من المناطق النائية، وتوفير الأدوية بأسعار في متناول الجميع.</p>
                </div>
                <div class="program-card">
                    <h3>الاقتصاد والفرص</h3>
                    <p>تشجيع الاستثمار، دعم المؤسسات الصغيرة والمتوسطة، وإطلاق برامج وطنية لخلق فرص عمل حقيقية للشباب.</p>
                </div>
            </div>
        </div>
    </section>

    <section id="contact" class="contact">
        <div class="container">
            <h2>كن جزءاً من التغيير</h2>
            <form id="contactForm">
                <input type="text" id="name" placeholder="الاسم الكامل" required>
                <input type="email" id="email" placeholder="البريد الإلكتروني" required>
                <textarea id="message" rows="5" placeholder="كيف يمكننا خدمتك؟ أو اترك لنا رسالة دعم..." required></textarea>
                <button type="submit">إرسال الرسالة</button>
            </form>
            <div id="formMessage"></div>
        </div>
    </section>

    <footer>
        <div class="container">
            <!-- الشريط الدائري المطلوب -->
            <div class="dev-badge">
                <div class="dev-badge-content">
                    <span>برمجة وتطوير</span>
                    <strong>المترشح<br>إبراهيمي يوسف</strong>
                </div>
            </div>
            <p>&copy; 2026 حملة إبراهيمي يوسف. جميع الحقوق محفوظة.</p>
        </div>
    </footer>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.getElementById('contactForm');
            const formMessage = document.getElementById('formMessage');

            // تمرير سلس
            document.querySelectorAll('nav a').forEach(anchor => {
                anchor.addEventListener('click', function(e) {
                    e.preventDefault();
                    const targetId = this.getAttribute('href');
                    const targetElement = document.querySelector(targetId);
                    if (targetElement) {
                        targetElement.scrollIntoView({ behavior: 'smooth' });
                    }
                });
            });

            // إرسال النموذج
            form.addEventListener('submit', async function(e) {
                e.preventDefault();
                const name = document.getElementById('name').value;
                const email = document.getElementById('email').value;
                const message = document.getElementById('message').value;

                formMessage.textContent = 'جاري الإرسال...';
                formMessage.className = '';

                try {
                    const response = await fetch('/api/contact', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name, email, message })
                    });

                    const data = await response.json();

                    if (response.ok) {
                        formMessage.textContent = data.success;
                        formMessage.className = 'success';
                        form.reset();
                    } else {
                        formMessage.textContent = data.error || 'حدث خطأ.';
                        formMessage.className = 'error';
                    }
                } catch (error) {
                    formMessage.textContent = 'تعذر الاتصال بالخادم.';
                    formMessage.className = 'error';
                }
            });
        });
    </script>
</body>
</html>
"""

# --- مسارات التطبيق (Routes) ---

@app.route('/')
def home():
    return render_template_string(HTML_CONTENT)

@app.route('/api/contact', methods=['POST'])
def contact():
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('email') or not data.get('message'):
        return jsonify({'error': 'جميع الحقول مطلوبة'}), 400
    
    name = data['name']
    email = data['email']
    message = data['message']
    
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO messages (name, email, message) VALUES (?, ?, ?)',
            (name, email, message)
        )
        conn.commit()
        conn.close()
        return jsonify({'success': 'شكراً لك! تم استلام رسالتك بنجاح.'}), 201
    except Exception as e:
        return jsonify({'error': 'حدث خطأ أثناء حفظ الرسالة'}), 500

# مسار لعرض الرسائل المحفوظة
@app.route('/api/messages', methods=['GET'])
def get_messages():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, email, message, created_at FROM messages ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    messages = []
    for row in rows:
        messages.append({
            'id': row[0],
            'name': row[1],
            'email': row[2],
            'message': row[3],
            'created_at': row[4]
        })
    return jsonify(messages)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
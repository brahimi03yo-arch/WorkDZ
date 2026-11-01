from flask import Flask, render_template

# إعداد Flask ليقرأ ملف index.html من نفس المجلد (بدون مجلد templates)
app = Flask(__name__, template_folder='.', static_folder='.')

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
import os
import sqlite3
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# DB setup
def init_db():
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY, name TEXT, email TEXT, message TEXT)''')
    conn.commit()
    conn.close()

init_db()

HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
... (HTML from previous response)
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/api/contact', methods=['POST'])
def contact():
    # handle data
    ...
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime
import uuid
from itsdangerous import URLSafeTimedSerializer
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'
serializer = URLSafeTimedSerializer(app.secret_key)


# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS users")
    c.execute("DROP TABLE IF EXISTS posts")
    c.execute("DROP TABLE IF EXISTS logs")

    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    password TEXT,
                    email TEXT,
                    is_admin BOOLEAN DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    text TEXT,
                    created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT,
                    key TEXT,
                    txt TEXT,
                    session TEXT,
                    ipaddr TEXT,
                    app TEXT,
                    time TEXT)''')
    conn.commit()
    conn.close()


init_db()


# Utility function to generate hashed UUID
def generate_hashed_uuid():
    raw_uuid = str(uuid.uuid4())
    hashed_uuid = serializer.dumps(raw_uuid)
    return hashed_uuid


# Utility function to save logs
def save_log(key, txt, session_id, ipaddr, app):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hashed_uuid = generate_hashed_uuid()
    c.execute("INSERT INTO logs (uuid, key, txt, session, ipaddr, app, time) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (hashed_uuid, key, txt, session_id, ipaddr, app, time))
    conn.commit()
    conn.close()


# Home page
@app.route('/')
def home():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    team_members = c.fetchall()
    conn.close()
    team_member_names = [member[0] for member in team_members]
    return render_template('index.html', team_members=team_member_names)


# Log page
@app.route('/log')
def log():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM logs")
    logs = c.fetchall()
    conn.close()
    return render_template('log.html', logs=logs)


# Register user
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        is_admin = request.form.get('is_admin') == 'on'
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, email, is_admin) VALUES (?, ?, ?, ?)",
                  (username, password, email, is_admin))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')


# Sign in user
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            token = serializer.dumps(user[0])
            save_log(key="LOGIN", txt=f"User {username} logged in",
                     session_id=session['user_id'], ipaddr=request.remote_addr, app="MyApp")
            return redirect(url_for('profile', token=token))
        else:
            return "Invalid credentials"
    return render_template('login.html')


# User profile
@app.route('/profile/<token>', methods=['GET', 'POST'])
def profile(token):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        user_id = serializer.loads(token, max_age=3600)
    except:
        return "Invalid or expired token", 403

    if request.method == 'POST':
        text = request.form['text']
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO posts (user_id, text, created_at) VALUES (?, ?, ?)", (user_id, text, created_at))
        conn.commit()
        conn.close()

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM posts WHERE user_id=?", (user_id,))
    posts = c.fetchall()
    conn.close()

    return render_template('profile.html', username=session['username'], posts=posts)


# Logout user
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))


# Admin decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT is_admin FROM users WHERE id=?", (session['user_id'],))
        user = c.fetchone()
        conn.close()
        if not user or not user[0]:
            return redirect(url_for('home'))
        return f(*args, **kwargs)

    return decorated_function


# Admin dashboard
@app.route('/admin')
@admin_required
def admin():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    c.execute("SELECT * FROM posts")
    posts = c.fetchall()
    conn.close()
    return render_template('admin.html', users=users, posts=posts)


if __name__ == '__main__':
    app.run(debug=True)

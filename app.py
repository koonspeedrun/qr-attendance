from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_bcrypt import Bcrypt
import sqlite3, qrcode, io, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"
bcrypt = Bcrypt(app)

# ====== สร้าง DB ======
def init_db():
    conn = sqlite3.connect("instance/database.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  role TEXT,
                  student_id TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  time TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()

init_db()

# ====== Register ======
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = bcrypt.generate_password_hash(request.form["password"]).decode("utf-8")
        student_id = request.form["student_id"]
        role = request.form.get("role","user")

        conn = sqlite3.connect("instance/database.db")
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username,password,role,student_id) VALUES (?,?,?,?)",
                      (username,password,role,student_id))
            conn.commit()
            flash("สมัครสมาชิกสำเร็จ! ไปที่หน้า Login ได้เลย","success")
            return redirect(url_for("login"))
        except:
            flash("Username นี้มีแล้ว!","danger")
        conn.close()
    return render_template("register.html")

# ====== Login ======
@app.route("/", methods=["GET","POST"])
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("instance/database.db")
        c = conn.cursor()
        c.execute("SELECT id, password, role, student_id FROM users WHERE username=?",(username,))
        user = c.fetchone()
        conn.close()

        if user and bcrypt.check_password_hash(user[1],password):
            session["user_id"] = user[0]
            session["role"] = user[2]
            session["student_id"] = user[3]
            session["username"] = username
            return redirect(url_for("dashboard"))
        else:
            flash("Username/Password ไม่ถูกต้อง!","danger")
    return render_template("login.html")

# ====== Dashboard ======
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("dashboard.html", username=session["username"], student_id=session["student_id"])

# ====== Generate QR Code ======
@app.route("/my_qr")
def my_qr():
    if "user_id" not in session:
        return redirect(url_for("login"))

    data = f"{session['user_id']}|{session['username']}|{session['student_id']}"
    qr = qrcode.make(data)
    img_io = io.BytesIO()
    qr.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype="image/png")

# ====== Scan QR (บันทึกการลงชื่อ) ======
@app.route("/scan", methods=["POST"])
def scan():
    qr_data = request.form["qr_data"]  # ข้อมูลจากกล้อง
    user_id, username, student_id = qr_data.split("|")

    conn = sqlite3.connect("instance/database.db")
    c = conn.cursor()
    c.execute("INSERT INTO attendance (user_id,time) VALUES (?,?)",(user_id,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return "บันทึกสำเร็จ!"

# ====== Admin ดูประวัติ ======
@app.route("/admin", methods=["GET","POST"])
def admin():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    records = []
    if request.method == "POST":
        username = request.form["username"]
        conn = sqlite3.connect("instance/database.db")
        c = conn.cursor()
        c.execute("""SELECT attendance.time, users.username, users.student_id 
                     FROM attendance JOIN users ON users.id=attendance.user_id 
                     WHERE users.username=?""",(username,))
        records = c.fetchall()
        conn.close()
    return render_template("admin.html", records=records)
    
if __name__ == "__main__":
    app.run(debug=True)

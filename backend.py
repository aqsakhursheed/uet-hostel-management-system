from functools import wraps
import datetime as dt
import json
import os
import secrets
import threading
import uuid

from flask import Flask, jsonify, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY") or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "0") == "1",
    MAX_CONTENT_LENGTH=1 * 1024 * 1024,
)

FILES = {
    "students": os.path.join(DATA_DIR, "students.json"),
    "staff": os.path.join(DATA_DIR, "staff.json"),
    "complaints": os.path.join(DATA_DIR, "complaints.json"),
    "payments": os.path.join(DATA_DIR, "payments.json"),
    "settings": os.path.join(DATA_DIR, "settings.json"),
    "activity": os.path.join(DATA_DIR, "activity.json"),
    "applications": os.path.join(DATA_DIR, "applications.json"),
    "users": os.path.join(DATA_DIR, "users.json"),
}

DEFAULT_SETTINGS = {
    "hostel_name": "UET Hostel",
    "admin_name": "Admin",
    "notifications": True,
    "dark_theme": True,
    "room_prices": {"Single": 15000, "Double": 10000, "Triple": 5000, "Four Sharing": 4000},
    "ac_addon": 1000,
    "room_categories": ["Single", "Double", "Triple", "Four Sharing"],
    "staff_categories": [
        "Resident Tutor", "Mess Head", "Servants", "Dhobi", "Sweepers",
        "Plumbers", "Electricians", "Carpenters", "Painters",
    ],
}

_write_lock = threading.RLock()


def now_string(with_time=True):
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S" if with_time else "%Y-%m-%d")


def read_file(key):
    path = FILES[key]
    if not os.path.exists(path):
        default = DEFAULT_SETTINGS if key == "settings" else []
        if key == "settings":
            write_file(key, default)
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            value = json.load(f)
        if key == "settings" and not isinstance(value, dict):
            return DEFAULT_SETTINGS.copy()
        if key != "settings" and not isinstance(value, list):
            return []
        return value
    except (OSError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.copy() if key == "settings" else []


def write_file(key, data):
    """Atomically replace a JSON data file to reduce corruption from partial writes."""
    path = FILES[key]
    temp_path = f"{path}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    try:
        with _write_lock:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.replace(temp_path, path)
        return True
    except OSError as exc:
        print(f"[write_file ERROR] {key}: {exc}")
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass
        return False


def log_activity(action, details=""):
    activities = read_file("activity")
    activities.insert(0, {
        "id": str(uuid.uuid4()),
        "action": action,
        "details": details,
        "timestamp": now_string(),
    })
    write_file("activity", activities[:50])


def generate_student_id():
    students = read_file("students")
    nums = []
    for student in students:
        try:
            nums.append(int(str(student.get("student_id", "STU0000")).replace("STU", "")))
        except (TypeError, ValueError):
            continue
    return f"STU{(max(nums) + 1 if nums else 1):04d}"


def calculate_fee(room_type, ac):
    settings = read_file("settings")
    prices = settings.get("room_prices", DEFAULT_SETTINGS["room_prices"])
    base = int(prices.get(room_type, 0) or 0)
    return base + (int(settings.get("ac_addon", 1000) or 0) if bool(ac) else 0)


def err(message, code=400):
    return jsonify({"success": False, "error": message}), code


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            return err("Admin authentication required", 401)
        return view(*args, **kwargs)
    return wrapped


def student_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "student":
            return err("Student authentication required", 401)
        return view(*args, **kwargs)
    return wrapped


def parse_json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    return data


def clean_text(value, max_length=200):
    return str(value or "").strip()[:max_length]


def init_admin():
    """Create/update the admin account from environment variables, never from source code."""
    email = clean_text(os.getenv("ADMIN_EMAIL", ""), 254).lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    if not email or not password:
        print("[startup] ADMIN_EMAIL and ADMIN_PASSWORD are not set; admin account was not initialized.")
        return False
    if len(password) < 8:
        print("[startup] ADMIN_PASSWORD must be at least 8 characters; admin account was not initialized.")
        return False

    users = read_file("users")
    admin = next((u for u in users if u.get("role") == "admin"), None)
    timestamp = now_string()
    if admin is None:
        users.append({
            "id": "ADMIN001",
            "name": "Admin",
            "email": email,
            "reg_no": "",
            "password": generate_password_hash(password),
            "role": "admin",
            "created_at": timestamp,
        })
        write_file("users", users)
        print(f"[startup] Admin account initialized for {email}.")
        return True

    changed = False
    if admin.get("email") != email:
        admin["email"] = email
        changed = True
    # Re-hash only when the configured password does not match the stored hash.
    try:
        matches = check_password_hash(admin.get("password", ""), password)
    except (ValueError, TypeError):
        matches = False
    if not matches:
        admin["password"] = generate_password_hash(password)
        changed = True
    if changed:
        write_file("users", users)
    return True


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


# ── Page Routes ───────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login")
def login_page():
    if session.get("role") == "admin":
        return redirect("/dashboard")
    if session.get("role") == "student":
        return redirect("/portal")
    return render_template("login.html")


@app.route("/portal")
def portal():
    if session.get("role") != "student":
        return redirect("/login")
    return render_template("portal.html")


@app.route("/dashboard")
def dashboard_page():
    if session.get("role") != "admin":
        return redirect("/login")
    return render_template("index.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ── API: Auth ─────────────────────────────────────────────────────────────────

@app.route("/api/register", methods=["POST"])
def register():
    data = parse_json_body()
    if data is None:
        return err("Invalid JSON")

    name = clean_text(data.get("name"), 100)
    email = clean_text(data.get("email"), 254).lower()
    reg_no = clean_text(data.get("reg_no"), 50)
    password = str(data.get("password") or "")
    if not all([name, email, reg_no, password]):
        return err("All fields are required")
    if len(password) < 8:
        return err("Password must be at least 8 characters")

    users = read_file("users")
    if any(u.get("email", "").lower() == email for u in users):
        return err("Email already registered. Please login.")

    user = {
        "id": "USR" + uuid.uuid4().hex[:8].upper(),
        "name": name,
        "email": email,
        "reg_no": reg_no,
        "password": generate_password_hash(password),
        "role": "student",
        "created_at": now_string(),
    }
    users.append(user)
    if not write_file("users", users):
        return err("Could not create account", 500)
    log_activity("Student Registered", f"{name} ({email})")
    return jsonify({"success": True}), 201


@app.route("/api/login", methods=["POST"])
def login_api():
    data = parse_json_body()
    if data is None:
        return err("Invalid JSON")

    email = clean_text(data.get("email"), 254).lower()
    password = str(data.get("password") or "")
    role = data.get("role", "student")
    if role not in {"admin", "student"}:
        return err("Invalid role")
    if not email or not password:
        return err("Email and password are required")

    users = read_file("users")
    user = next((u for u in users if u.get("email", "").lower() == email and u.get("role") == role), None)
    if not user or not check_password_hash(user.get("password", ""), password):
        return err("Invalid email or password", 401)

    session.clear()
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    session["name"] = user["name"]
    session["email"] = user["email"]
    session["reg_no"] = user.get("reg_no", "")
    redirect_url = "/dashboard" if role == "admin" else "/portal"
    return jsonify({"success": True, "redirect": redirect_url})


@app.route("/api/me")
def get_me():
    if "user_id" not in session:
        return err("Not logged in", 401)
    return jsonify({
        "user_id": session.get("user_id"),
        "name": session.get("name"),
        "email": session.get("email"),
        "role": session.get("role"),
        "reg_no": session.get("reg_no", ""),
    })


# ── API: Dashboard ────────────────────────────────────────────────────────────

@app.route("/api/dashboard")
@admin_required
def dashboard():
    try:
        students = read_file("students")
        complaints = read_file("complaints")
        payments = read_file("payments")
        activities = read_file("activity")
        applications = read_file("applications")
        occupied = {s.get("room_number") for s in students if s.get("room_number")}
        pending_pay = [p for p in payments if p.get("status") == "Unpaid"]
        active_c = [c for c in complaints if c.get("status") != "Resolved"]
        pending_apps = [a for a in applications if a.get("status") == "Pending"]
        return jsonify({
            "total_students": len(students),
            "occupied_rooms": len(occupied),
            "pending_payments": len(pending_pay),
            "active_complaints": len(active_c),
            "pending_applications": len(pending_apps),
            "recent_activity": activities[:10],
        })
    except Exception as exc:
        return err(str(exc), 500)


# ── API: Students (admin only) ────────────────────────────────────────────────

@app.route("/api/students", methods=["GET"])
@admin_required
def get_students():
    return jsonify(read_file("students"))


@app.route("/api/students", methods=["POST"])
@admin_required
def add_student():
    data = parse_json_body()
    if data is None:
        return err("Invalid or missing JSON body")
    for field in ["name", "registration_number", "room_number"]:
        if not clean_text(data.get(field)):
            return err(f"Missing required field: {field}")

    students = read_file("students")
    registration_number = clean_text(data.get("registration_number"), 50)
    if any(s.get("registration_number") == registration_number for s in students):
        return err("A student with this registration number already exists")

    room_type = clean_text(data.get("room_type", "Single"), 30)
    ac = bool(data.get("ac", False))
    student = {
        "student_id": generate_student_id(),
        "name": clean_text(data.get("name"), 100),
        "registration_number": registration_number,
        "phone": clean_text(data.get("phone"), 30),
        "room_number": clean_text(data.get("room_number"), 20),
        "room_type": room_type,
        "ac": ac,
        "fee": calculate_fee(room_type, ac),
        "created_at": now_string(),
    }
    students.append(student)
    if not write_file("students", students):
        return err("Could not save student", 500)

    payments = read_file("payments")
    payments.append({
        "id": str(uuid.uuid4()), "student_id": student["student_id"],
        "student_name": student["name"], "amount": student["fee"],
        "status": "Unpaid", "history": [], "created_at": now_string(False),
    })
    write_file("payments", payments)
    log_activity("Student Added", f"{student['name']} ({student['student_id']}) → Room {student['room_number']}")
    return jsonify({"success": True, "student": student}), 201


@app.route("/api/students/<sid>", methods=["GET"])
@admin_required
def get_student(sid):
    students = read_file("students")
    student = next((s for s in students if s.get("student_id") == sid), None)
    if not student:
        return err("Not found", 404)
    return jsonify({
        "success": True,
        "student": student,
        "complaints": [c for c in read_file("complaints") if c.get("student_id") == sid],
        "payments": [p for p in read_file("payments") if p.get("student_id") == sid],
    })


@app.route("/api/students/<sid>", methods=["PUT"])
@admin_required
def update_student(sid):
    data = parse_json_body() or {}
    students = read_file("students")
    for i, student in enumerate(students):
        if student.get("student_id") != sid:
            continue
        allowed = {"name", "registration_number", "phone", "room_number", "room_type", "ac"}
        updates = {k: data[k] for k in allowed if k in data}
        if "registration_number" in updates:
            updates["registration_number"] = clean_text(updates["registration_number"], 50)
            if any(s.get("registration_number") == updates["registration_number"] and s.get("student_id") != sid for s in students):
                return err("A student with this registration number already exists")
        for key in ["name", "phone", "room_number", "room_type"]:
            if key in updates:
                updates[key] = clean_text(updates[key], 100 if key == "name" else 30)
        if "ac" in updates:
            updates["ac"] = bool(updates["ac"])
        room_type = updates.get("room_type", student.get("room_type", "Single"))
        ac = updates.get("ac", student.get("ac", False))
        updates["fee"] = calculate_fee(room_type, ac)
        students[i].update(updates)
        if not write_file("students", students):
            return err("Could not save student", 500)
        payments = read_file("payments")
        for payment in payments:
            if payment.get("student_id") == sid and payment.get("status") == "Unpaid":
                payment["amount"] = students[i]["fee"]
                payment["student_name"] = students[i]["name"]
        write_file("payments", payments)
        log_activity("Student Updated", f"{students[i]['name']} ({sid})")
        return jsonify({"success": True, "student": students[i]})
    return err("Not found", 404)


@app.route("/api/students/<sid>", methods=["DELETE"])
@admin_required
def delete_student(sid):
    students = read_file("students")
    student = next((s for s in students if s.get("student_id") == sid), None)
    if not student:
        return err("Not found", 404)
    write_file("students", [s for s in students if s.get("student_id") != sid])
    log_activity("Student Deleted", f"{student['name']} ({sid})")
    return jsonify({"success": True})


# ── API: Rooms (admin only) ───────────────────────────────────────────────────

@app.route("/api/rooms", methods=["GET"])
@admin_required
def get_rooms():
    students = read_file("students")
    settings = read_file("settings")
    room_map = {}
    for student in students:
        room_number = student.get("room_number")
        if room_number:
            room_map.setdefault(room_number, {
                "room_number": room_number,
                "room_type": student.get("room_type", ""),
                "students": [],
                "ac": student.get("ac", False),
            })
            room_map[room_number]["students"].append({
                "name": student.get("name", ""),
                "student_id": student.get("student_id", ""),
            })
    return jsonify({
        "rooms": list(room_map.values()),
        "categories": settings.get("room_categories", DEFAULT_SETTINGS["room_categories"]),
        "prices": settings.get("room_prices", DEFAULT_SETTINGS["room_prices"]),
    })


# ── API: Payments (admin only) ────────────────────────────────────────────────

@app.route("/api/payments", methods=["GET"])
@admin_required
def get_payments():
    return jsonify(read_file("payments"))


@app.route("/api/payments/<pid>/pay", methods=["POST"])
@admin_required
def pay(pid):
    data = parse_json_body() or {}
    payments = read_file("payments")
    for payment in payments:
        if payment.get("id") == pid:
            payment["status"] = "Paid"
            payment.setdefault("history", []).append({
                "amount": payment["amount"],
                "date": now_string(False),
                "note": clean_text(data.get("note", "Manual payment"), 100),
            })
            write_file("payments", payments)
            log_activity("Payment Received", f"{payment['student_name']} paid PKR {payment['amount']}")
            return jsonify({"success": True})
    return err("Not found", 404)


@app.route("/api/payments/<pid>/unpay", methods=["POST"])
@admin_required
def unpay(pid):
    payments = read_file("payments")
    for payment in payments:
        if payment.get("id") == pid:
            payment["status"] = "Unpaid"
            write_file("payments", payments)
            log_activity("Payment Reverted", f"{payment['student_name']} marked Unpaid")
            return jsonify({"success": True})
    return err("Not found", 404)


# ── API: Complaints ───────────────────────────────────────────────────────────

@app.route("/api/complaints", methods=["GET"])
@admin_required
def get_complaints():
    return jsonify(read_file("complaints"))


@app.route("/api/complaints", methods=["POST"])
@student_required
def add_complaint():
    data = parse_json_body()
    if data is None:
        return err("Invalid JSON")

    student_id = clean_text(data.get("student_id"), 30).upper()
    category = clean_text(data.get("category", "Other"), 50)
    description = clean_text(data.get("description"), 1000)
    if not student_id or not category or not description:
        return err("Student ID, category and description are required")

    students = read_file("students")
    student = next((s for s in students if s.get("student_id") == student_id), None)
    if not student:
        return err("Student not found", 404)
    # A student may only submit a complaint for their own approved student record.
    if clean_text(student.get("registration_number"), 50).lower() != clean_text(session.get("reg_no"), 50).lower():
        return err("You can only submit complaints for your own student record", 403)

    complaints = read_file("complaints")
    complaint = {
        "id": str(uuid.uuid4()),
        "student_id": student_id,
        "student_name": student.get("name", ""),
        "room_number": student.get("room_number", ""),
        "category": category,
        "description": description,
        "status": "Pending",
        "created_at": now_string(),
    }
    complaints.append(complaint)
    write_file("complaints", complaints)
    log_activity("Complaint Filed", f"{student['name']} — {category}")
    return jsonify({"success": True, "complaint": complaint}), 201


@app.route("/api/complaints/<cid>/resolve", methods=["POST"])
@admin_required
def resolve_complaint(cid):
    complaints = read_file("complaints")
    for complaint in complaints:
        if complaint.get("id") == cid:
            complaint["status"] = "Resolved"
            complaint["resolved_at"] = now_string()
            write_file("complaints", complaints)
            log_activity("Complaint Resolved", f"{complaint['category']} for {complaint['student_name']}")
            return jsonify({"success": True})
    return err("Not found", 404)


@app.route("/api/complaints/<cid>", methods=["DELETE"])
@admin_required
def delete_complaint(cid):
    complaints = read_file("complaints")
    complaint = next((c for c in complaints if c.get("id") == cid), None)
    if not complaint:
        return err("Not found", 404)
    write_file("complaints", [c for c in complaints if c.get("id") != cid])
    log_activity("Complaint Deleted", f"{complaint['category']} for {complaint['student_name']}")
    return jsonify({"success": True})


# ── API: Staff (admin only) ───────────────────────────────────────────────────

@app.route("/api/staff", methods=["GET"])
@admin_required
def get_staff():
    return jsonify(read_file("staff"))


@app.route("/api/staff", methods=["POST"])
@admin_required
def add_staff():
    data = parse_json_body()
    if data is None or not clean_text(data.get("name")):
        return err("Name is required")
    staff = read_file("staff")
    nums = []
    for member in staff:
        try:
            nums.append(int(str(member.get("staff_id", "STF0000")).replace("STF", "")))
        except (TypeError, ValueError):
            continue
    next_num = max(nums) + 1 if nums else 1
    try:
        salary = int(data.get("salary", 0) or 0)
        if salary < 0:
            raise ValueError
    except (TypeError, ValueError):
        return err("Salary must be a non-negative number")
    member = {
        "staff_id": f"STF{next_num:04d}",
        "name": clean_text(data.get("name"), 100),
        "category": clean_text(data.get("category", "Servants"), 50),
        "phone": clean_text(data.get("phone"), 30),
        "salary": salary,
        "created_at": now_string(False),
    }
    staff.append(member)
    write_file("staff", staff)
    log_activity("Staff Added", f"{member['name']} — {member['category']}")
    return jsonify({"success": True, "member": member}), 201


@app.route("/api/staff/<sfid>", methods=["PUT"])
@admin_required
def update_staff(sfid):
    data = parse_json_body() or {}
    staff = read_file("staff")
    for i, member in enumerate(staff):
        if member.get("staff_id") == sfid:
            allowed = {"name", "category", "phone", "salary"}
            updates = {k: data[k] for k in allowed if k in data}
            if "name" in updates:
                updates["name"] = clean_text(updates["name"], 100)
            if "category" in updates:
                updates["category"] = clean_text(updates["category"], 50)
            if "phone" in updates:
                updates["phone"] = clean_text(updates["phone"], 30)
            if "salary" in updates:
                try:
                    updates["salary"] = int(updates["salary"] or 0)
                    if updates["salary"] < 0:
                        raise ValueError
                except (TypeError, ValueError):
                    return err("Salary must be a non-negative number")
            member.update(updates)
            write_file("staff", staff)
            log_activity("Staff Updated", f"{member['name']} ({sfid})")
            return jsonify({"success": True, "member": member})
    return err("Not found", 404)


@app.route("/api/staff/<sfid>", methods=["DELETE"])
@admin_required
def delete_staff(sfid):
    staff = read_file("staff")
    member = next((s for s in staff if s.get("staff_id") == sfid), None)
    if not member:
        return err("Not found", 404)
    write_file("staff", [s for s in staff if s.get("staff_id") != sfid])
    log_activity("Staff Removed", f"{member['name']} ({sfid})")
    return jsonify({"success": True})


# ── API: Settings (admin only) ────────────────────────────────────────────────

@app.route("/api/settings", methods=["GET"])
@admin_required
def get_settings():
    return jsonify(read_file("settings"))


@app.route("/api/settings", methods=["POST"])
@admin_required
def update_settings():
    data = parse_json_body() or {}
    settings = read_file("settings")
    if "room_prices" in data and isinstance(data["room_prices"], dict):
        prices = {}
        for room_type, price in data["room_prices"].items():
            try:
                value = int(price)
                if value < 0:
                    raise ValueError
                prices[clean_text(room_type, 40)] = value
            except (TypeError, ValueError):
                return err("Room prices must be non-negative numbers")
        settings["room_prices"] = prices
    if "ac_addon" in data:
        try:
            addon = int(data["ac_addon"])
            if addon < 0:
                raise ValueError
            settings["ac_addon"] = addon
        except (TypeError, ValueError):
            return err("AC addon must be a non-negative number")
    for key in ["hostel_name", "admin_name"]:
        if key in data:
            settings[key] = clean_text(data[key], 100)
    for key in ["notifications", "dark_theme"]:
        if key in data:
            settings[key] = bool(data[key])
    write_file("settings", settings)
    log_activity("Settings Updated", "Admin modified system settings")
    return jsonify({"success": True, "settings": settings})


# ── API: Search (admin only) ──────────────────────────────────────────────────

@app.route("/api/search")
@admin_required
def search():
    q = clean_text(request.args.get("q", ""), 100).lower()
    if not q:
        return jsonify([])
    results = []
    for student in read_file("students"):
        if any(q in clean_text(student.get(field)).lower() for field in ["student_id", "registration_number", "room_number", "name"]):
            results.append({"type": "student", **student})
    for member in read_file("staff"):
        if any(q in clean_text(member.get(field)).lower() for field in ["staff_id", "name"]):
            results.append({"type": "staff", **member})
    return jsonify(results[:10])


# ── API: Applications ─────────────────────────────────────────────────────────
# Application submission and status lookup remain public because this is the
# public admissions workflow. Admin-only endpoints return the full application.

@app.route("/api/applications", methods=["GET"])
@admin_required
def get_applications():
    return jsonify(read_file("applications"))


@app.route("/api/applications", methods=["POST"])
def add_application():
    data = parse_json_body()
    if data is None:
        return err("Invalid or missing JSON body")
    for field in ["name", "cnic", "registration_number", "phone"]:
        if not clean_text(data.get(field)):
            return err(f"Missing required field: {field}")

    applications = read_file("applications")
    application = {
        "id": "APP" + uuid.uuid4().hex[:8].upper(),
        "name": clean_text(data.get("name"), 100),
        "cnic": clean_text(data.get("cnic"), 30),
        "registration_number": clean_text(data.get("registration_number"), 50),
        "phone": clean_text(data.get("phone"), 30),
        "email": clean_text(data.get("email"), 254),
        "department": clean_text(data.get("department"), 100),
        "year": clean_text(data.get("year"), 30),
        "room_type": clean_text(data.get("room_type", "Single"), 30),
        "ac": bool(data.get("ac", False)),
        "guardian_name": clean_text(data.get("guardian_name"), 100),
        "guardian_phone": clean_text(data.get("guardian_phone"), 30),
        "guardian_relation": clean_text(data.get("guardian_relation"), 50),
        "special_requirements": clean_text(data.get("special_requirements"), 500),
        "status": "Pending",
        "created_at": now_string(),
    }
    applications.append(application)
    if not write_file("applications", applications):
        return err("Could not save application", 500)
    log_activity("Application Received", f"{application['name']} — {application['department']}")
    return jsonify({"success": True, "application": application, "app_id": application["id"]}), 201


@app.route("/api/applications/<aid>/status", methods=["GET"])
def check_application_status(aid):
    applications = read_file("applications")
    application = next((a for a in applications if a.get("id") == aid), None)
    if not application:
        return err("Application not found", 404)
    # Public status lookup returns only fields needed by the applicant.
    return jsonify({
        "success": True,
        "application": {
            "id": application.get("id"),
            "name": application.get("name"),
            "registration_number": application.get("registration_number"),
            "room_type": application.get("room_type"),
            "ac": application.get("ac", False),
            "status": application.get("status"),
            "created_at": application.get("created_at"),
            "rejection_reason": application.get("rejection_reason", ""),
        },
    })


@app.route("/api/applications/<aid>/approve", methods=["POST"])
@admin_required
def approve_application(aid):
    data = parse_json_body() or {}
    room_number = clean_text(data.get("room_number"), 20)
    if not room_number:
        return err("Room number is required")

    applications = read_file("applications")
    for application in applications:
        if application.get("id") != aid:
            continue
        if application.get("status") != "Pending":
            return err("Only pending applications can be approved")

        students = read_file("students")
        if any(s.get("registration_number") == application.get("registration_number") for s in students):
            return err("A student with this registration number already exists")

        application["status"] = "Approved"
        application["approved_at"] = now_string()
        write_file("applications", applications)

        sid = generate_student_id()
        room_type = application.get("room_type", "Single")
        ac = bool(application.get("ac", False))
        fee = calculate_fee(room_type, ac)
        student = {
            "student_id": sid,
            "name": application["name"],
            "registration_number": application["registration_number"],
            "phone": application["phone"],
            "room_number": room_number,
            "room_type": room_type,
            "ac": ac,
            "fee": fee,
            "created_at": now_string(),
        }
        students.append(student)
        write_file("students", students)

        payments = read_file("payments")
        payments.append({
            "id": str(uuid.uuid4()), "student_id": sid,
            "student_name": student["name"], "amount": fee,
            "status": "Unpaid", "history": [], "created_at": now_string(False),
        })
        write_file("payments", payments)
        log_activity("Application Approved", f"{application['name']} → {sid}, Room {room_number}")
        return jsonify({"success": True, "student_id": sid})
    return err("Not found", 404)


@app.route("/api/applications/<aid>/reject", methods=["POST"])
@admin_required
def reject_application(aid):
    data = parse_json_body() or {}
    applications = read_file("applications")
    for application in applications:
        if application.get("id") == aid:
            if application.get("status") != "Pending":
                return err("Only pending applications can be rejected")
            application["status"] = "Rejected"
            application["rejection_reason"] = clean_text(data.get("reason", "Does not meet requirements"), 500)
            application["rejected_at"] = now_string()
            write_file("applications", applications)
            log_activity("Application Rejected", application["name"])
            return jsonify({"success": True})
    return err("Not found", 404)


@app.route("/api/applications/<aid>", methods=["DELETE"])
@admin_required
def delete_application(aid):
    applications = read_file("applications")
    application = next((a for a in applications if a.get("id") == aid), None)
    if not application:
        return err("Not found", 404)
    write_file("applications", [a for a in applications if a.get("id") != aid])
    log_activity("Application Deleted", application["name"])
    return jsonify({"success": True})


# Execute admin creation on import for serverless environments (Vercel)
init_admin()

if __name__ == "__main__":
    # Local development only
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
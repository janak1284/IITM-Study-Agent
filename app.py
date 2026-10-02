import os
import json
import uuid
import subprocess
import threading
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from functools import wraps
from database import db, User

app = Flask(__name__)
CORS(app)

# SQLite Database config
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# In-memory store for running tasks
TASKS = {}
LOGS_DIR = "debug"
os.makedirs(LOGS_DIR, exist_ok=True)

# --- Authentication Middleware ---
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = request.headers.get('Authorization')
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401
        
        # Remove Bearer if present
        if user_id.startswith('Bearer '):
            user_id = user_id.split(' ')[1]
            
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "Unauthorized - User not found"}), 401
            
        g.user = user
        return f(*args, **kwargs)
    return decorated

# --- Auth Routes ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    local_save_path = data.get('local_save_path')
    
    if not username or not password or not local_save_path:
        return jsonify({"error": "Missing required fields"}), 400
        
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400
        
    new_user = User(username=username, local_save_path=local_save_path)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    
    # Ensure local save directory exists
    os.makedirs(local_save_path, exist_ok=True)
    
    return jsonify({"message": "Registration successful", "user": new_user.to_dict()})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return jsonify({"message": "Login successful", "user": user.to_dict()})
        
    return jsonify({"error": "Invalid username or password"}), 401

# --- Config & Data Routes ---
@app.route('/api/config', methods=['GET'])
@require_auth
def get_config():
    return jsonify(g.user.to_dict())

@app.route('/api/config', methods=['POST'])
@require_auth
def update_config():
    data = request.json
    for key, value in data.items():
        if hasattr(g.user, key) and key not in ['id', 'username', 'password_hash']:
            setattr(g.user, key, value)
    db.session.commit()
    return jsonify({"status": "success", "user": g.user.to_dict()})

@app.route('/api/courses', methods=['GET'])
@require_auth
def get_courses():
    if g.user.courses_json:
        try:
            courses = json.loads(g.user.courses_json)
            return jsonify({"courses": courses})
        except:
            pass
    return jsonify({"courses": []})

# --- Onboarding Automation Routes ---
@app.route('/api/onboarding/launch_iitm', methods=['POST'])
@require_auth
def launch_iitm():
    # Launches Chrome with CDP on user's configured port
    port = g.user.cdp_port or "9222"
    cmd = f'start "" "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port={port} --user-data-dir="C:\\chrome-iitm-profile" "https://app.onlinedegree.iitm.ac.in/student_dashboard/current_courses"'
    subprocess.Popen(cmd, shell=True)
    return jsonify({"status": "launched", "message": "IITM Chrome instance launched. Please login manually."})

@app.route('/api/onboarding/launch_gemini', methods=['POST'])
@require_auth
def launch_gemini():
    port = g.user.cdp_port or "9222" # Using default but the string overrides it to 9223 as requested
    cmd = 'start "" "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9223 --user-data-dir="C:\\chrome-gemini-profile" "https://gemini.google.com/app"'
    subprocess.Popen(cmd, shell=True)
    return jsonify({"status": "launched", "message": "Gemini Chrome instance launched. Please login manually."})

@app.route('/api/onboarding/scrape_courses', methods=['POST'])
@require_auth
def scrape_courses():
    # Placeholder for actual Playwright/Selenium CDP scraping logic
    # In a real scenario, this would connect to localhost:CDP_PORT, read the DOM, extract courses
    
    # For now, we will simulate a successful scrape to keep the UI flowing
    simulated_courses = ["Business Data Management", "Machine Learning Techniques", "Software Engineering"]
    
    g.user.courses_json = json.dumps(simulated_courses)
    db.session.commit()
    
    return jsonify({"status": "success", "courses": simulated_courses})

@app.route('/api/onboarding/complete', methods=['POST'])
@require_auth
def complete_onboarding():
    g.user.onboarding_completed = True
    db.session.commit()
    return jsonify({"status": "success", "user": g.user.to_dict()})

# --- Task Execution ---
def run_script_task(task_id, script_name, log_file, user_id):
    # In reality, you'd pass user_id to the script via argparse so it can lookup the local_save_path from DB
    with open(log_file, "w") as f:
        process = subprocess.Popen(
            ["python", script_name, "--user_id", user_id],
            stdout=f,
            stderr=subprocess.STDOUT,
            text=True
        )
        TASKS[task_id]["status"] = "running"
        process.wait()
        TASKS[task_id]["status"] = "completed" if process.returncode == 0 else "error"
        
        with open(log_file, "a") as log:
            log.write(f"\n[Task Finished with exit code: {process.returncode}]\n")

@app.route('/api/run_task', methods=['POST'])
@require_auth
def run_task():
    data = request.json
    script = data.get("script", "orchestrator.py")
    
    task_id = str(uuid.uuid4())
    log_file = os.path.join(LOGS_DIR, f"task_{task_id}.log")
    
    TASKS[task_id] = {
        "script": script,
        "status": "starting",
        "log_file": log_file
    }
    
    thread = threading.Thread(target=run_script_task, args=(task_id, script, log_file, g.user.id))
    thread.start()
    
    return jsonify({"task_id": task_id, "status": "started", "message": f"Started {script}"})

@app.route('/api/task_status/<task_id>', methods=['GET'])
def task_status(task_id):
    if task_id not in TASKS:
        return jsonify({"error": "Task not found"}), 404
        
    task_info = TASKS[task_id]
    log_content = ""
    if os.path.exists(task_info["log_file"]):
        with open(task_info["log_file"], "r", encoding="utf-8") as f:
            log_content = f.read()
            
    return jsonify({
        "status": task_info["status"],
        "logs": log_content
    })

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000)

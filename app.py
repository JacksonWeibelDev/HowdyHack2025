import os
import json
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from predict import classify_resume, MODEL_DIR

from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['BRAND'] = 'HowdyHack'
# IMPORTANT: Use a strong, secret key in production, perhaps from environment variables
app.config['SECRET_KEY'] = 'i like to play roblox' # Keep this for session management

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect here if @login_required fails
login_manager.login_message_category = 'info' # Category for the "Please log in" message


# --- File path for user data ---
USER_DATA_FILE = 'users.json'


# --- User Data Loading/Saving Functions (unchanged) ---
def load_users():
    # ...(logic remains the same)...
    default_users = {'1': {'email': 'admin@example.com', 'password_hash': 'password', 'name': 'Admin User', 'history': [] }}
    default_next_id = 2
    if not os.path.exists(USER_DATA_FILE):
        print(f"'{USER_DATA_FILE}' not found. Creating it...")
        try:
            save_users(default_users, default_next_id)
            print(f"Successfully created '{USER_DATA_FILE}'.")
            return default_users, default_next_id
        except Exception as e:
            print(f"Error creating '{USER_DATA_FILE}': {e}.")
            return default_users, default_next_id
    try:
        with open(USER_DATA_FILE, 'r') as f:
            data = json.load(f)
            users_dict = data.get('users', {})
            for user_id in users_dict:
                if 'history' not in users_dict[user_id]:
                    users_dict[user_id]['history'] = []
            max_id = 0
            if users_dict:
                 numeric_ids = [int(k) for k in users_dict.keys() if k.isdigit()]
                 if numeric_ids: max_id = max(numeric_ids)
            next_id = data.get('next_user_id', max_id + 1)
            if not users_dict:
                 print(f"'{USER_DATA_FILE}' was empty. Initializing...")
                 save_users(default_users, default_next_id)
                 return default_users, default_next_id
            return users_dict, next_id
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading user data: {e}.")
        return default_users, default_next_id

def save_users(users_dict, next_id):
    # ...(logic remains the same)...
     try:
        with open(USER_DATA_FILE, 'w') as f:
            json.dump({'users': users_dict, 'next_user_id': next_id}, f, indent=4)
     except IOError as e:
        print(f"Error saving user data: {e}")

users, next_user_id = load_users()
print(f"Loaded {len(users)} users. Next ID: {next_user_id}")

# --- User Class & Loader (unchanged) ---
class User(UserMixin):
    # ...(unchanged)...
     def __init__(self, id, email, name):
        self.id = id
        self.email = email
        self.name = name

@login_manager.user_loader
def load_user(user_id):
    # ...(unchanged)...
    user_data = users.get(user_id)
    if user_data:
        return User(id=user_id, email=user_data['email'], name=user_data['name'])
    return None

# --- Context Processor (Inject brand, brand_img AND current_user) ---
@app.context_processor
def inject_global_vars():
    """Makes 'brand', 'brand_img' and 'current_user' available in all templates.

    If a `static/hero.png` file exists it will be used as the navbar brand image.
    """
    brand = app.config.get('BRAND', 'Your Brand')
    # Prefer a hero image in static/hero.png when available
    try:
        hero_path = os.path.join(app.root_path, 'static', 'hero.png')
        if os.path.exists(hero_path):
            brand_img = url_for('static', filename='hero_white.png')
        else:
            brand_img = None
    except Exception:
        brand_img = None

    return {'brand': brand, 'brand_img': brand_img, 'current_user': current_user}

# --- Routes ---
@app.route('/')
def index():
    return render_template('upload.html', active_page='home')

@app.route('/about')
def about():
    return render_template('about.html', active_page='about')

@app.route('/services')
def services():
    return render_template('index.html', active_page='services')

@app.route('/contact')
def contact():
    return render_template('contact.html', active_page='contact')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index')) # Already logged in

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        # Find user by email (in our simple dictionary)
        user_instance = None
        user_id_found = None
        for uid, user_data in users.items():
            if user_data['email'] == email:
                 # !!! SECURITY WARNING: Check HASHED password here in a real app !!!
                if user_data['password'] == password:
                    user_instance = User(id=uid, email=user_data['email'], name=user_data['name'])
                    user_id_found = uid
                    break # Found the user

        if user_instance:
            login_user(user_instance, remember=remember)
            print('Logged in successfully!')
            # Redirect to the page they were trying to access, or index
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Login Unsuccessful. Please check email and password.', 'danger')

    return render_template('login.html', active_page='login')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    global next_user_id # To modify the global counter
    if current_user.is_authenticated:
        return redirect(url_for('index')) # Don't allow signup if logged in

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password') # Assume signup.html has a password field

        # Check if email already exists
        email_exists = any(ud['email'] == email for ud in users.values())
        if email_exists:
            flash('Email address already registered.', 'warning')
            return redirect(url_for('signup'))

        # Basic password validation (add more robust checks!)
        if not password or len(password) < 6:
            flash('Password must be at least 6 characters.', 'warning')
            return redirect(url_for('signup'))

        # Create new user
        user_id = str(next_user_id)
        # !!! SECURITY WARNING: HASH the password before storing in a real app !!!
        # from werkzeug.security import generate_password_hash
        # hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        users[user_id] = {'email': email, 'password': password, 'name': name}
        next_user_id += 1

        save_users(users_dict=users,next_id=next_user_id)

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html', active_page='signup')

# --- New Logout Route ---
@app.route('/logout')
@login_required # Must be logged in to log out
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/history')
@login_required
def history():
    # ...(logic remains the same)...
    user_id = current_user.get_id()
    user_data = users.get(user_id)
    user_history = user_data.get('history', []) if user_data else []
    return render_template('history.html', history=user_history, active_page='history')


@app.route('/testing', methods=['GET'])
@login_required # Example: Protect the testing page
def upload():
    # Now only logged-in users can see this
    return render_template('upload.html', active_page='testing')

# --- MODIFIED /classify Route ---
@app.route('/classify', methods=['POST'])
@login_required
def classify_resume_route():
    data = request.get_json()
    if not data: return jsonify({"error": "No JSON data provided"}), 400

    resume_text = data.get('resume_text')
    job_role = data.get('job_role')
    job_description = data.get('job_description') # --- NEW: Get job description ---

    # Basic validation
    if not resume_text or not job_role:
        return jsonify({"error": "Missing 'resume_text' or 'job_role'"}), 400

    # Call prediction function, passing job_description
    result = classify_resume(resume_text, job_role, job_description) # --- MODIFIED CALL ---

    # Save result to user history (including new fields)
    if "error" not in result.get("error", ""): # Check more robustly for errors
        user_id = current_user.get_id()
        if user_id in users:
            history_entry = {
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'job_role': job_role,
                'job_description_snippet': (job_description[:150] + "...") if job_description else "N/A", # --- NEW ---
                'resume_snippet': resume_text[:200] + "...",
                'ml_prediction': result.get('ml_prediction'),
                'ml_confidence': result.get('ml_confidence'),
                'gen_ai_assessment': result.get('gen_ai_assessment'),
                'resume_jd_comparison': result.get('resume_jd_comparison'), # --- NEW ---
                'improvement_suggestions': result.get('improvement_suggestions')
            }
            if 'history' not in users[user_id]: users[user_id]['history'] = []
            users[user_id]['history'].append(history_entry)
            save_users(users, next_user_id)
        else:
            print(f"Warning: Could not find user {user_id} to save history.")

    # Return result
    if "error" in result.get("error", ""): # Check more robustly for errors
        status_code = 404 if "No ML model found" in result.get("error", "") else 500
        return jsonify(result), status_code
    return jsonify(result), 200


if __name__ == '__main__':
    # Check if the model directory exists (optional, but good practice)
    if not os.path.exists(MODEL_DIR):
        print(f"Warning: Model directory '{MODEL_DIR}' not found.")
        print("Please run the training script first to create and save the models.")
    app.run(debug=True) # debug=True is okay for development
import os
import json # --- NEW: For handling JSON file ---
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash # --- NEW: For password hashing ---
from predict import classify_resume, MODEL_DIR

app = Flask(__name__)
app.config['BRAND'] = 'HowdyHack'
app.config['SECRET_KEY'] = 'i like to play roblox' # Keep this for session management

# --- File path for user data ---
USER_DATA_FILE = 'users.json'

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# --- User Data Loading/Saving Functions ---
def load_users():
    """Loads user data from the JSON file. Creates the file with a default admin if it doesn't exist."""
    default_users = {'1': {'email': 'admin@example.com', 'password_hash': generate_password_hash('password'), 'name': 'Admin User'}}
    default_next_id = 2

    if not os.path.exists(USER_DATA_FILE):
        print(f"'{USER_DATA_FILE}' not found. Creating it with default admin user.")
        try:
            # --- NEW: Save the default data immediately ---
            save_users(default_users, default_next_id)
            print(f"Successfully created '{USER_DATA_FILE}'.")
            return default_users, default_next_id
        except Exception as e:
            print(f"Error creating '{USER_DATA_FILE}': {e}. Using in-memory default.")
            return default_users, default_next_id # Fallback to in-memory

    # --- Existing logic to load if file DOES exist ---
    try:
        with open(USER_DATA_FILE, 'r') as f:
            data = json.load(f)
            users_dict = data.get('users', {})
            # Ensure next_user_id logic is robust
            max_id = 0
            if users_dict:
                 numeric_ids = [int(k) for k in users_dict.keys() if k.isdigit()]
                 if numeric_ids:
                      max_id = max(numeric_ids)
            next_id = data.get('next_user_id', max_id + 1)
            # Handle case where loaded file might be empty but exists
            if not users_dict:
                 print(f"'{USER_DATA_FILE}' was empty. Initializing with default admin.")
                 save_users(default_users, default_next_id)
                 return default_users, default_next_id
            return users_dict, next_id
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading user data from existing file: {e}. Using in-memory default.")
        return default_users, default_next_id # Fallback
    
def save_users(users_dict, next_id):
    """Saves user data to the JSON file."""
    try:
        with open(USER_DATA_FILE, 'w') as f:
            json.dump({'users': users_dict, 'next_user_id': next_id}, f, indent=4)
    except IOError as e:
        print(f"Error saving user data: {e}")

# --- Load Users at Startup ---
users, next_user_id = load_users()
print(f"Loaded {len(users)} users from {USER_DATA_FILE}. Next ID: {next_user_id}")


# --- User Class (unchanged) ---
class User(UserMixin):
    def __init__(self, id, email, name):
        self.id = id
        self.email = email
        self.name = name

# --- User Loader Function (unchanged) ---
@login_manager.user_loader
def load_user(user_id):
    user_data = users.get(user_id)
    if user_data:
        return User(id=user_id, email=user_data['email'], name=user_data['name'])
    return None

# --- Context Processor (Inject brand AND current_user) ---
@app.context_processor
def inject_brand():
    return {'brand': app.config.get('BRAND', 'Your Brand')}
@app.route('/')
def index():
    return render_template('index.html', active_page='home')

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
    if request.method == 'POST':
        # stub: grab form data and pretend to authenticate
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
    if request.method == 'POST':
        # stub: collect signup data
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password') # Assume signup.html has a password field

        # Check if email already exists
        email_exists = any(ud['email'] == email for ud in users.values())
        if email_exists:
            print('Email address already registered.')
            return redirect(url_for('signup'))

        # Basic password validation (add more robust checks!)
        if not password:
            print('Password must be at least 6 characters.')
            return redirect(url_for('signup'))

        # Create new user
        user_id = str(next_user_id)
        # !!! SECURITY WARNING: HASH the password before storing in a real app !!!
        #from werkzeug.security import generate_password_hash
        #hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        users[user_id] = {'email': email, 'password': password, 'name': name}
        next_user_id += 1

        print('Account created successfully! Please log in.')
        save_users(users_dict=users, next_id=next_user_id)
        return redirect(url_for('login'))
    return render_template('signup.html', active_page='signup')

# --- New Logout Route ---
@app.route('/logout')
@login_required # Must be logged in to log out
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/history', methods=['GET'])
@login_required
def history():
    return render_template('history.html')

@app.route('/testing', methods=['GET'])
def upload():
    return render_template('upload.html')




# --- Protect the /classify endpoint ---
@app.route('/classify', methods=['POST'])
def classify_resume_route():
    """
    This is the main API endpoint. It expects a JSON payload with
    'resume_text' and 'job_role' (which is the name of the job).
    """
    # Get the JSON data from the POST request
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    # Extract the required fields
    resume_text = data.get('resume_text')
    job_role = data.get('job_role') # IMPORTANT: This must be the job *name*

    if not resume_text or not job_role:
        return jsonify({"error": "Missing 'resume_text' or 'job_role' in JSON"}), 400

    # Import the prediction routine lazily so the app can start quickly
    try:
        from predict import classify_resume
    except Exception as e:
        return jsonify({"error": f"Prediction module could not be loaded: {e}"}), 500

    # Call the prediction function
    result = classify_resume(resume_text, job_role)

    # Return the result as JSON
    if "error" in result:
        return jsonify(result), 404 # 404 Not Found (no model for that role)
    
    return jsonify(result), 200


if __name__ == '__main__':
    app.run(debug=True)
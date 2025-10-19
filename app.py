import os
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

# --- Simple In-Memory User Store (Replace with a database in a real app!) ---
# WARNING: Storing plain text passwords like this is VERY insecure. Use hashing (e.g., werkzeug.security)!
users = {
    '1': {'email': 'test@example.com', 'password': 'password', 'name': 'Test User'}
}
next_user_id = 2 # Simple ID counter

# --- User Class ---
class User(UserMixin):
    def __init__(self, id, email, name):
        self.id = id
        self.email = email
        self.name = name
    # We don't store the password hash on the User object itself usually

# --- User Loader Function ---
@login_manager.user_loader
def load_user(user_id):
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
            brand_img = url_for('static', filename='hero.png')
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
            flash('Logged in successfully!', 'success')
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


@app.route('/testing', methods=['GET'])
@login_required # Example: Protect the testing page
def upload():
    # Now only logged-in users can see this
    return render_template('upload.html')


# --- Protect the /classify endpoint ---
@app.route('/classify', methods=['POST'])
@login_required # Add this decorator
def classify_resume_route():
    """
    This is the main API endpoint. It expects a JSON payload with
    'resume_text' and 'job_role' (which is the name of the job).
    Now requires the user to be logged in.
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    resume_text = data.get('resume_text')
    job_role = data.get('job_role')

    if not resume_text or not job_role:
        return jsonify({"error": "Missing 'resume_text' or 'job_role' in JSON"}), 400

    # Call our imported prediction function
    result = classify_resume(resume_text, job_role)

    if "error" in result:
         # Distinguish between model not found and other errors if needed
        if "No ML model found" in result.get("error", ""):
            return jsonify(result), 404 # 404 Not Found (no model for that role)
        else:
            return jsonify(result), 500 # Internal Server Error for other issues

    return jsonify(result), 200


if __name__ == '__main__':
    # Check if the model directory exists (optional, but good practice)
    if not os.path.exists(MODEL_DIR):
        print(f"Warning: Model directory '{MODEL_DIR}' not found.")
        print("Please run the training script first to create and save the models.")
    app.run(debug=True) # debug=True is okay for development
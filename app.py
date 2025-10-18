import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from predict import classify_resume, MODEL_DIR

app = Flask(__name__)
app.config['BRAND'] = 'HowdyHack'
app.config['SECRET_KEY'] = 'i like to play roblox'

@app.context_processor
def inject_brand():
    return {'brand': app.config.get('BRAND', 'Your Brand')}
@app.route('/')
def index():
    return render_template('index.html', active_page='home')

@app.route('/about')
def about():
    return render_template('index.html', active_page='about')

@app.route('/services')
def services():
    return render_template('index.html', active_page='services')

@app.route('/contact')
def contact():
    return render_template('index.html', active_page='contact')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # stub: grab form data and pretend to authenticate
        email = request.form.get('email')
        password = request.form.get('password')
        # TODO: add real authentication
        flash('Login attempt for: ' + (email or ''), 'info')
        return redirect(url_for('index'))
    return render_template('login.html', active_page='login')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # stub: collect signup data
        name = request.form.get('name')
        email = request.form.get('email')
        # TODO: create user and validate
        flash('Account created for: ' + (email or ''), 'success')
        return redirect(url_for('login'))
    return render_template('signup.html', active_page='signup')

@app.route('/testing', methods=['GET'])
def upload():
    return render_template('upload.html')


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

    # Call our imported prediction function
    result = classify_resume(resume_text, job_role)

    # Return the result as JSON
    if "error" in result:
        return jsonify(result), 404 # 404 Not Found (no model for that role)
    
    return jsonify(result), 200


if __name__ == '__main__':
    app.run(debug=True)
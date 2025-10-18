from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html', active_page='home', brand='HowdyHack')


@app.route('/about')
def about():
    return render_template('index.html', active_page='about', brand='HowdyHack')


@app.route('/services')
def services():
    return render_template('index.html', active_page='services', brand='HowdyHack')


@app.route('/contact')
def contact():
    return render_template('index.html', active_page='contact', brand='HowdyHack')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # stub: grab form data and pretend to authenticate
        email = request.form.get('email')
        password = request.form.get('password')
        # TODO: add real authentication
        flash('Login attempt for: ' + (email or ''), 'info')
        return redirect(url_for('index'))
    return render_template('login.html', active_page='login', brand='HowdyHack')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # stub: collect signup data
        name = request.form.get('name')
        email = request.form.get('email')
        # TODO: create user and validate
        flash('Account created for: ' + (email or ''), 'success')
        return redirect(url_for('login'))
    return render_template('signup.html', active_page='signup', brand='HowdyHack')


if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, render_template

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


@app.route('/login')
def login():
    return render_template('index.html', active_page='login', brand='HowdyHack')


@app.route('/signup')
def signup():
    return render_template('index.html', active_page='signup', brand='HowdyHack')


if __name__ == '__main__':
    app.run(debug=True)
"""
A Flask web application with user registration, login, and a dashboard integrated with the Openverse API for searching images and audio.
Passwords are securely hashed using Flask-Bcrypt.
SQL injection prevention is achieved using parameterized queries with flask_mysqldb.
"""
import os
import re
import requests
from flask import Flask, render_template, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', '127.0.0.1')
app.config['MYSQL_PORT'] = int(os.environ.get('MYSQL_PORT', 3306))
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', 'rabin8866')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'mydatabase')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.secret_key = '8966rabin'

# Openverse API Configuration
app.config['OPENVERSE_BASE_URL'] = 'https://api.openverse.engineering/v1'
app.config['OPENVERSE_API_KEY'] = os.environ.get('OPENVERSE_API_KEY', '')  # Set your API key if needed

mysql = MySQL(app)
bcrypt = Bcrypt(app)
app.config['WTF_CSRF_ENABLED'] = False  # For demonstration purposes only

class RegistrationForm(FlaskForm):
    """Form for user registration."""
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Register")

class LoginForm(FlaskForm):
    """Form for user login."""
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class SearchForm(FlaskForm):
    """Form for searching Openverse content."""
    query = StringField("Search", validators=[DataRequired()])
    submit = SubmitField("Search")

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        password = form.password.data

        cursor = mysql.connection.cursor()
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            flash("Email already registered", "warning")
        else:
            # Hash the password before storing it
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, hashed_pw))
            mysql.connection.commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        password = form.password.data

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if not user:
            flash("User not registered, please register first.", "warning")
        else:
            stored_pw = user['password']
            # Migrate plaintext password to bcrypt hash if needed.
            if not re.match(r"^\$2[abxy]\$", stored_pw):
                if stored_pw == password:
                    new_hashed = bcrypt.generate_password_hash(password).decode('utf-8')
                    cursor.execute("UPDATE users SET password = %s WHERE email = %s", (new_hashed, email))
                    mysql.connection.commit()
                    stored_pw = new_hashed
                else:
                    flash("Incorrect password", "danger")
                    return render_template('login.html', form=form)
            if bcrypt.check_password_hash(stored_pw, password):
                session['user_id'] = email  # using email as session identifier
                flash("Login successful", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Incorrect password", "danger")
    return render_template('login.html', form=form)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    
    form = SearchForm()
    images = []
    audio = []
    
    if form.validate_on_submit():
        query = form.query.data
        headers = {'Authorization': f'Bearer {app.config["OPENVERSE_API_KEY"]}'} if app.config['OPENVERSE_API_KEY'] else {}
        
        # Fetch images from Openverse
        image_url = f"{app.config['OPENVERSE_BASE_URL']}/images/?q={query}"
        try:
            response = requests.get(image_url, headers=headers)
            if response.status_code == 200:
                images = response.json().get('results', [])
            else:
                flash("Error fetching images", "danger")
        except requests.exceptions.RequestException as e:
            flash(f"Error connecting to Openverse: {str(e)}", "danger")
        
        # Fetch audio from Openverse
        audio_url = f"{app.config['OPENVERSE_BASE_URL']}/audio/?q={query}"
        try:
            response = requests.get(audio_url, headers=headers)
            if response.status_code == 200:
                audio = response.json().get('results', [])
            else:
                flash("Error fetching audio", "danger")
        except requests.exceptions.RequestException as e:
            flash(f"Error connecting to Openverse: {str(e)}", "danger")
    
    return render_template('dashboard.html', user=session['user_id'], form=form, images=images, audio=audio)

# [Remaining app code remains identical...]

@app.route('/')
def index():
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

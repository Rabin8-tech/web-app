import os
import re
import requests
from flask import Flask, render_template, redirect, url_for, flash, session, request, g
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp
from flask_bcrypt import Bcrypt
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = '8966rabin'
bcrypt = Bcrypt(app)
app.config['WTF_CSRF_ENABLED'] = False

# PostgreSQL Configuration (via environment or defaults)
bcrypt = Bcrypt(app)

# Hardcoded PostgreSQL URL
db_url = 'postgresql://media_admin:0Eys5adGA9Tvyyc7zvfOa64ZW7Rl33ZC@dpg-d0dkj5euk2gs73d7kdag-a.oregon-postgres.render.com/open_media_db'

# Openverse API
app.config['OPENVERSE_BASE_URL'] = 'https://api.openverse.engineering/v1'
app.config['OPENVERSE_API_KEY']  = os.environ.get('OPENVERSE_API_KEY', '')

# In-memory store for recent searches
recent_searches = []

# --- Database helper functions ---
def get_db_connection():
    if 'db_conn' not in g:
        g.db_conn = psycopg2.connect(db_url)
    return g.db_conn

def get_db_cursor():
    return get_db_connection().cursor(cursor_factory=psycopg2.extras.RealDictCursor)

@app.teardown_appcontext
def close_db_connection(exc):
    db = g.pop('db_conn', None)
    if db is not None:
        db.close()

# --- Forms ---
class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name  = StringField('Last Name',  validators=[DataRequired()])
    email      = StringField('Email',      validators=[DataRequired(), Email()])
    password   = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8),
        Regexp(
            r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&]).+$',
            message="Password must contain a letter, number, and special character."
        ),
    ])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email    = StringField("Email",    validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit   = SubmitField("Login")

class SearchForm(FlaskForm):
    query  = StringField("Search", validators=[DataRequired()])
    submit = SubmitField("Search")

# --- Routes ---
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        cursor = get_db_cursor()
        email = form.email.data.lower().strip()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            flash("Email already registered", "warning")
        else:
            hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            cursor.execute(
                "INSERT INTO users (first_name, last_name, email, password) VALUES (%s, %s, %s, %s)",
                (form.first_name.data, form.last_name.data, email, hashed_pw)
            )
            get_db_connection().commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        cursor = get_db_cursor()
        email = form.email.data.lower().strip()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if not user:
            flash("User not registered", "warning")
        else:
            stored_pw = user['password']
            # Migrate plaintext to bcrypt if needed
            if not re.match(r"^\$2[abxy]\$", stored_pw):
                if stored_pw == form.password.data:
                    new_hashed = bcrypt.generate_password_hash(stored_pw).decode('utf-8')
                    cursor.execute("UPDATE users SET password=%s WHERE email=%s", (new_hashed, email))
                    get_db_connection().commit()
                    stored_pw = new_hashed
                else:
                    flash("Incorrect password", "danger")
                    return render_template('login.html', form=form)
            if bcrypt.check_password_hash(stored_pw, form.password.data):
                session['user_id'] = email
                flash("Login successful", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Incorrect password", "danger")
    return render_template('login.html', form=form)

@app.route('/dashboard', methods=['GET','POST'])
def dashboard():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    cursor = get_db_cursor()
    cursor.execute("SELECT first_name FROM users WHERE email = %s", (session['user_id'],))
    user = cursor.fetchone()
    first_name = user['first_name'] if user else 'User'

    form = SearchForm()
    images = []
    audio  = []
    query  = None

    if request.method == 'GET' and request.args.get('search_query'):
        query = request.args.get('search_query')
    if form.validate_on_submit():
        query = form.query.data.strip()

    if query:
        if query not in recent_searches:
            recent_searches.append(query)
            if len(recent_searches) > 5:
                recent_searches.pop(0)

        headers = {}
        if app.config['OPENVERSE_API_KEY']:
            headers['Authorization'] = f"Bearer {app.config['OPENVERSE_API_KEY']}"

        img_res = requests.get(f"{app.config['OPENVERSE_BASE_URL']}/images/?q={query}", headers=headers)
        if img_res.ok:
            images = img_res.json().get('results', [])

        aud_res = requests.get(f"{app.config['OPENVERSE_BASE_URL']}/audio/?q={query}", headers=headers)
        if aud_res.ok:
            audio = aud_res.json().get('results', [])

    return render_template(
        'dashboard.html',
        first_name=first_name,
        query=query,
        images=images,
        audio=audio,
        recent_searches=recent_searches,
        form=form
    )

@app.route('/clear_searches')
def clear_searches():
    recent_searches.clear()
    flash("Recent searches cleared.", "info")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Logged out successfully", "info")
    return redirect(url_for('login'))

# Static pages
@app.route('/features')
def features():  return render_template('features.html')
@app.route('/pricing')
def pricing():   return render_template('pricing.html')
@app.route('/about')
def about():     return render_template('about.html')
@app.route('/contact')
def contact():   return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)

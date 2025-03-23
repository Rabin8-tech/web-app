"""
A Flask web application that provides user registration, login, and a dashboard.

This module demonstrates a simple web application using Flask, Flask-WTF, and WTForms for handling
web forms, and Flask-MySQLdb for database interactions. The login page checks if a user's email is registered.
If it is not, the user is informed to register first (with a registration link provided on the login page).
After registration, the user can log in and access the dashboard.
No additional email validation is performed beyond requiring a non-empty input.
"""

from flask import Flask, render_template, redirect, url_for, flash, session, request
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask_mysqldb import MySQL

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'rabin8866'  # Make sure this is your correct password
app.config['MYSQL_DB'] = 'mydatabase'
app.secret_key = '8966rabin'
mysql = MySQL(app)

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Register a new user by inserting their email and password into the database.
    
    If the provided email is already registered, the user is informed via a flash message.
    On successful registration, the user is redirected to the login page.
    """
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        cursor = mysql.connection.cursor()
        # Check if the email already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            flash("Email already registered", "warning")
        else:
            cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, password))
            mysql.connection.commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login by checking credentials against the database.
    
    When a user submits the login form:
        - The application checks whether the email exists in the database.
        - If the email is not found, a flash message is displayed prompting the user to register,
          and the login page is rendered again with a link to the registration page.
        - If the email exists, the password is verified. On success, the user is logged in and redirected 
          to the dashboard; otherwise, an error message is shown.
    """
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        cursor = mysql.connection.cursor()
        # Check if the user is registered
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if not user:
            flash("User not registered, please register first.", "warning")
        else:
            # Verify password for the existing user
            cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
            if cursor.fetchone():
                session['user_id'] = email  # Store email in session
                flash("Login successful", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Incorrect password", "danger")
    return render_template('login.html', form=form)

@app.route('/dashboard')
def dashboard():
    """
    Display the dashboard for a logged-in user.
    
    If the user is not logged in (i.e., no email stored in the session), the user is redirected 
    to the login page with a message prompting them to log in.
    """
    if 'user_id' in session:
        return render_template('dashboard.html', user=session['user_id'])
    flash("Please log in first.", "warning")
    return redirect(url_for('login'))

@app.route('/')
def index():
    """
    Redirect the root URL to the login page.
    
    This ensures that the login page is the first page the user sees.
    """
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

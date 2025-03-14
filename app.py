"""
A simple Flask web application that renders a login form and a dashboard.

This module provides a login interface that accepts any email and password,
stores the email in the session, and then redirects to a dashboard. The application
uses Flask, Flask-WTF, and WTForms for handling web requests and forms.
"""

from flask import Flask, render_template, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

app = Flask(__name__)
app.secret_key = 'rabinrk8966'
app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for simplicity (enable in production)

# In-memory store for registered users (for demonstration)
# Structure: { email: {"name": ..., "password": ... } }
users_db = {}

class RegisterForm(FlaskForm):
    """A form for registering a new user."""
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Register")

class LoginForm(FlaskForm):
    """A form for logging in a user."""
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Render the registration form and handle user registration.

    Users provide a name, email, and password to create an account. If the email already exists,
    a flash message notifies them. On successful registration, they are redirected to login.
    """
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data
        if email in users_db:
            flash("Email already registered. Please login.", "danger")
            return redirect(url_for('login'))
        users_db[email] = {"name": name, "password": password}  # Store user details
        flash("Registration successful. Please login.", "success")
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Render the login form and handle user login.

    On successful form submission (i.e., both email and password provided),
    the user's email is stored in the session and they are redirected to the dashboard.
    """
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        if email in users_db and users_db[email]["password"] == password:
            session['user_id'] = email  # Store email in session
            flash("Login successful", "success")
            return redirect(url_for('dashboard'))
        flash("Invalid email or password. Please try again.", "danger")
    return render_template('login.html', form=form)

@app.route('/', methods=['GET', 'POST'])
def index():
    """Render the login page at the root URL.

    This route displays the same login form as the /login route.
    """
    form = LoginForm()
    return render_template('login.html', form=form)

@app.route('/dashboard')
def dashboard():
    """Render the dashboard for a logged-in user.

    If the user is not logged in, a flash message is shown and the user is redirected
    to the login page.
    """
    if 'user_id' in session:
        email = session['user_id']
        user = users_db.get(email, {})
        # Prefer to show the user's name if available, otherwise the email
        display_name = user.get("name", email)
        return render_template('dashboard.html', user=display_name)
    flash("Please log in first.", "warning")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

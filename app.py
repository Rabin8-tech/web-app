"""A simple Flask web application that renders a login form and a dashboard.

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

class LoginForm(FlaskForm):
    """A form for logging in a user.

    Attributes:
        email (StringField): Field for the user's email.
        password (PasswordField): Field for the user's password.
        submit (SubmitField): Submit button for the form.
    """
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Render the login form and handle user login.

    On successful form submission (i.e., both email and password provided),
    the user's email is stored in the session and they are redirected to the dashboard.

    Returns:
        A rendered HTML template for the login page or a redirect to the dashboard.
    """
    form = LoginForm()
    if form.validate_on_submit():
        session['user_id'] = form.email.data  # Store email in session
        flash("Login successful", "success")
        return redirect(url_for('dashboard'))
    return render_template('login.html', form=form)

@app.route('/', methods=['GET', 'POST'])
def index():
    """Render the login page at the root URL.

    This route displays the same login form as the /login route.

    Returns:
        A rendered HTML template for the login page.
    """
    form = LoginForm()
    return render_template('login.html', form=form)

@app.route('/dashboard')
def dashboard():
    """Render the dashboard for a logged-in user.

    If the user is not logged in, a flash message is shown and the user is redirected
    to the login page.

    Returns:
        A rendered HTML template for the dashboard or a redirect to the login page.
    """
    if 'user_id' in session:
        return render_template('dashboard.html', user=session['user_id'])
    flash("Please log in first.", "warning")
    return redirect(url_for('login'))

if __name__ == '__main__':
    """Run the Flask development server."""
    app.run(debug=True)

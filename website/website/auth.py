from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import login_user, login_required, logout_user, current_user

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method =='POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in successfully!' , category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect password, try again.', category='error')
        else:
            flash('Email does not exist.', category='error')

    return render_template("login.html", user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        if(request.form.get('admin') == 'on'):
            admin_privilege = True
        else:
            admin_privilege = False

        user = User.query.filter_by(email=email).first()
        
        if user:
            flash('Email already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif len(first_name) < 2:
            flash('First name must be greater than 1 character.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
        else:
            new_user = User(email=email, first_name=first_name, password=generate_password_hash(password1, method='sha256'), admin_user = admin_privilege)
            db.session.add(new_user)
            db.session.commit()
            flash('Account created!', category='success')
            return redirect(url_for('auth.sign_up'))
            
    return render_template("sign-up.html", user=current_user)

@auth.route('/manage-account', methods=['GET'])
@login_required  # Requires the user to be logged in to access this page
def users():
    users = User.query.all()
    return render_template('manage-account.html', users=users, user=current_user)

@auth.route('/edit-user/<int:id>', methods=['GET', 'POST'])
@login_required  # Requires the user to be logged in to access this page
def edit_user(id):
    edituser = User.query.get_or_404(id)

    if request.method == 'POST':

        # Check if the password fields are filled
        password1 = request.form['password1']
        password2 = request.form['password2']

        user = User.query.filter_by(email=request.form['email']).first()
        
        if user and user.id != id:
            flash('Email already exists.', category='error')
            return redirect(url_for('auth.edit_user', id=id))
        elif len(request.form['email']) < 4:
            flash('Email must be greater than 3 characters.', category='error')
            return redirect(url_for('auth.edit_user', id=id))
        elif len(request.form['firstName']) < 2:
            flash('First name must be greater than 1 character.', category='error')
            return redirect(url_for('auth.edit_user', id=id))
        else:
            # Update user details based on the submitted form data
            edituser.email = request.form['email']
            edituser.first_name = request.form['firstName']
            edituser.subscribed = bool(request.form.get('subscribed'))
        if password1 and password2:
            # Check if the passwords match
            if password1 == password2:
                # Generate a new password hash
                edituser.password = generate_password_hash(password1, method='sha256')
                flash('Password updated successfully', 'success')
            elif password1 != password2:
                flash('Passwords don\'t match.', category='error')
                return redirect(url_for('auth.edit_user', id=id))
            elif len(password1) < 7:
                flash('Password must be at least 7 characters.', category='error')
                return redirect(url_for('auth.edit_user', id=id))

        # Save the changes to the database
        db.session.commit()

        flash('User details updated successfully', 'success')
        # Redirect to the users page or any other desired page
        return redirect(url_for('auth.users'))

    return render_template('edit-user.html', user=current_user, edituser=edituser)

from flask import redirect, url_for

# Route to delete a user
@auth.route('/delete_user/<int:user_id>', methods=['GET', 'POST'])
def delete_user(user_id):
    # Find the user by ID
    user = User.query.get(user_id)

    if user:
        # Delete the user from the database
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully!', category='success')
    else:
        flash('User not found!', category='error')

    return redirect(url_for('auth.users'))

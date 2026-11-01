from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from ..extensions import db
from ..models import User

bp = Blueprint('auth', __name__)

SELF_SERVICE_ROLES = ('customer', 'provider') 

@bp.route('/register',methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        role = request.form['role']
        location = request.form['location']
        password = generate_password_hash(request.form['password'],method='pbkdf2:sha256')

        if role not in SELF_SERVICE_ROLES:
            role = 'customer'

        if User.query.filter((User.email == email) | (User.username == username)).first():
            flash("Username or email already Exist , danger")
            return redirect(url_for('auth.register'))

        new_user = User(username=username,email = email , password = password, role=role,
                        location = location)
        db.session.add(new_user)
        db.session.commit()

        flash('Registered successfully! Please Login.','success')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@bp.route('/login',methods = ["GET","POST"])
def login():
    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password,password):
            flash('Invalid credentials','danger')
            return render_template(url_for('auth.login'))

        login_user(user)
        flash('Logged in successfully!','success')

        if user.role == 'admin':
            return redirect(url_for('admin.admin'))
        else:
            return redirect(url_for('main.index'))
    return render_template('login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully ')
    return redirect(url_for('main.index'))


@bp.route('/profile',methods=['GET','POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.phone = request.form['phone']
        current_user.location = request.form['location']

        db.session.commit()
        flash("Profile updated Successfully!",'success')
        return redirect(url_for('auth.profile'))
    return render_template('profile.html',user=current_user)


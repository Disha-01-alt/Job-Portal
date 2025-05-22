from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from database import get_user_by_email, create_user
import logging

auth_bp = Blueprint('auth_routes', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please provide both email and password.', 'error')
            return render_template('auth/login.html')
        
        try:
            user = get_user_by_email(email)
            
            if user and user.check_password(password):
                if not user.is_approved and user.role == 'company':
                    flash('Your account is pending approval. Please contact the administrator.', 'warning')
                    return render_template('auth/login.html')
                
                login_user(user)
                flash(f'Welcome back, {user.full_name or user.email}!', 'success')
                
                # Redirect based on role
                if user.role == 'candidate':
                    return redirect(url_for('candidate_routes.dashboard'))
                elif user.role == 'admin':
                    return redirect(url_for('admin_routes.dashboard'))
                elif user.role == 'company':
                    return redirect(url_for('company_routes.dashboard'))
                else:
                    return redirect(url_for('index'))
            else:
                flash('Invalid email or password.', 'error')
        
        except Exception as e:
            logging.error(f"Login error: {e}")
            flash('An error occurred during login. Please try again.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', '')
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        linkedin = request.form.get('linkedin', '').strip()
        github = request.form.get('github', '').strip()
        
        # Validation
        if not all([email, password, confirm_password, role, full_name]):
            flash('Please fill in all required fields.', 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('auth/register.html')
        
        if role not in ['candidate', 'company']:
            flash('Invalid role selected.', 'error')
            return render_template('auth/register.html')
        
        try:
            # Check if email already exists
            existing_user = get_user_by_email(email)
            if existing_user:
                flash('An account with this email already exists.', 'error')
                return render_template('auth/register.html')
            
            # Create new user
            user_id = create_user(
                email=email,
                password=password,
                role=role,
                full_name=full_name,
                phone=phone or None,
                linkedin=linkedin or None,
                github=github or None
            )
            
            if role == 'company':
                flash('Account created successfully! Your account is pending approval by an administrator.', 'info')
            else:
                flash('Account created successfully! You can now log in.', 'success')
            
            return redirect(url_for('auth_routes.login'))
        
        except Exception as e:
            logging.error(f"Registration error: {e}")
            flash('An error occurred during registration. Please try again.', 'error')
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

# jobportal/routes/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user # current_user might be used for conditional rendering
from database import get_user_by_email, create_user, get_user_by_id # Ensure get_user_by_id is available
from models import User 
import logging

auth_bp = Blueprint('auth_routes', __name__)

# This /login route is for a potential manual email/password login form.
# If you are ONLY using Google Sign-In, this route might not be directly used by users,
# but Flask-Login needs a login_view. It can simply redirect to Google login.
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Redirect based on role if already logged in
        if current_user.role == 'candidate': return redirect(url_for('candidate_routes.dashboard'))
        if current_user.role == 'admin': return redirect(url_for('admin_routes.dashboard'))
        if current_user.role == 'company': return redirect(url_for('company_routes.dashboard'))
        return redirect(url_for('index'))
    
    # For now, if someone hits /auth/login, guide them to Google Sign-In
    flash("Please use Google Sign-In to access your account.", "info")
    return redirect(url_for('google_auth.login'))

    # If you were to implement manual login:
    # if request.method == 'POST':
    #     email = request.form.get('email', '').strip().lower()
    #     password = request.form.get('password', '')
    #     # ... (manual password checking logic) ...
    # return render_template('auth/login.html') # A page with manual login form

@auth_bp.route('/register', methods=['GET', 'POST'])
def register(): # For manual registration
    if current_user.is_authenticated:
        return redirect(url_for('index')) 
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', '')
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip() or None
        linkedin = request.form.get('linkedin', '').strip() or None
        github = request.form.get('github', '').strip() or None
        
        errors = []
        if not all([email, password, confirm_password, role, full_name]):
            errors.append('Please fill in all required fields (*).')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        if role not in ['candidate', 'company']:
            errors.append('Invalid role selected.')
        
        if not errors:
            existing_user = get_user_by_email(email)
            if existing_user:
                errors.append('An account with this email already exists. Please login or use a different email.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html', form_data=request.form)
        
        try:
            user_id = create_user( # create_user in database.py hashes the password
                email=email, password=password, role=role, full_name=full_name,
                phone=phone, linkedin=linkedin, github=github
            )
            logging.info(f"Manual registration successful for {email}, role: {role}, user_id: {user_id}")
            
            if role == 'company':
                flash('Account created! Your company account is pending admin approval.', 'info')
            else:
                flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('google_auth.login')) # Redirect to login page after manual registration
        
        except Exception as e:
            logging.exception(f"Error during manual registration for {email}:")
            flash('An error occurred during registration. Please try again.', 'error')
            return render_template('auth/register.html', form_data=request.form)

    return render_template('auth/register.html') # For GET request

@auth_bp.route('/complete_registration', methods=['GET', 'POST'])
def complete_registration():
    if not session.get('pending_registration') or not session.get('google_email'):
        flash('Invalid registration session. Please try signing in with Google again.', 'warning')
        return redirect(url_for('google_auth.login'))
    
    if request.method == 'POST':
        role = request.form.get('role')
        # Use Google name from session as default if form field is empty, else use form field
        full_name_from_form = request.form.get('full_name', '').strip()
        full_name_to_save = full_name_from_form if full_name_from_form else session.get('google_name', 'New User')
        
        phone_to_save = request.form.get('phone', '').strip() or None
        linkedin_to_save = request.form.get('linkedin', '').strip() or None
        github_to_save = request.form.get('github', '').strip() or None
        
        if not role or role not in ['candidate', 'company']:
            flash('Please select a valid role.', 'error')
            return render_template('auth/complete_registration.html', 
                                 google_name=session.get('google_name'), 
                                 google_email=session.get('google_email'),
                                 form_data=request.form) # Pass back form data
        
        google_email_from_session = session['google_email']
        
        # Defensive check: Ensure user wasn't created in a concurrent request or by other means
        if get_user_by_email(google_email_from_session):
            flash('This Google account is already registered. Please log in.', 'info')
            session.pop('pending_registration', None)
            session.pop('google_email', None) 
            return redirect(url_for('google_auth.login'))

        try:
            # Create user account. password_hash in DB will be hash of empty string.
            user_id = create_user(
                email=google_email_from_session,
                password='',  # For Google-auth, password isn't set here
                role=role,
                full_name=full_name_to_save,
                phone=phone_to_save,
                linkedin=linkedin_to_save,
                github=github_to_save
            )
            logging.info(f"Google user registration completed for {google_email_from_session}, role: {role}, user_id: {user_id}")

            newly_created_user = get_user_by_id(user_id)
            if not newly_created_user:
                logging.error(f"Failed to fetch newly created user (ID: {user_id}) after completing registration.")
                flash("Critical error during registration. Account might not be fully active. Please contact support.", "error")
                session.pop('pending_registration', None) # Clean up session
                session.pop('google_email', None)
                return redirect(url_for('google_auth.login'))

            login_user(newly_created_user) # Log in the newly created user
            
            # Clear sensitive/temporary session data
            session.pop('pending_registration', None)
            session.pop('google_email', None) 
            # Keep 'google_id', 'google_name', 'google_picture' if used for display in base.html for logged-in user

            if role == 'company':
                if not newly_created_user.is_approved: # is_approved is set by create_user
                    flash('Your company account has been created and is pending admin approval. You will be notified.', 'info')
                    return redirect(url_for('index')) # Or a specific "pending" page
                else: # Should not happen for new companies if default is_approved is False
                    flash('Company account created and approved!', 'success')
                    return redirect(url_for('company_routes.dashboard'))
            else: # Candidate
                flash(f'Welcome, {newly_created_user.full_name}! Your account is ready.', 'success')
                return redirect(url_for('candidate_routes.dashboard'))
                
        except Exception as e:
            logging.exception(f"Error completing registration for Google user {session.get('google_email')}:")
            flash(f'Error creating your account: {str(e)}. Please try again.', 'error')
            return render_template('auth/complete_registration.html',
                                 google_name=session.get('google_name'),
                                 google_email=session.get('google_email'),
                                 form_data=request.form) # Pass back form data for pre-filling
                                 
    # GET request to /complete_registration
    return render_template('auth/complete_registration.html', 
                         google_name=session.get('google_name'), # For pre-filling name field
                         google_email=session.get('google_email')) # For display

# Note: The main logout (/logout or /google_logout) is in google_auth.py now
# as it needs to clear Google-specific session keys.

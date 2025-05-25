from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from database import get_candidate_profile, update_candidate_profile, get_all_jobs
import os
import logging

candidate_bp = Blueprint('candidate_routes', __name__)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

@candidate_bp.before_request
def check_candidate_role():
    if current_user.is_authenticated and current_user.role != 'candidate':
        flash('Access denied. This area is for candidates only.', 'error')
        return redirect(url_for('index'))

@candidate_bp.route('/dashboard')
@login_required
def dashboard():
    try:
        profile = get_candidate_profile(current_user.id)
        return render_template('candidate/dashboard.html', profile=profile)
    except Exception as e:
        logging.error(f"Error loading candidate dashboard: {e}")
        flash('Error loading dashboard. Please try again.', 'error')
        return redirect(url_for('index'))

@candidate_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    try:
        if request.method == 'POST':
            # Get form data
            summary = request.form.get('summary', '').strip()
            education = request.form.get('education', '').strip()
            experience = request.form.get('experience', '').strip()
            skills = request.form.get('skills', '').strip()
            
            # Handle file uploads
            cv_file = request.files.get('cv')
            id_card_file = request.files.get('id_card')
            marksheet_file = request.files.get('marksheet')
            
            update_data = {}
            
            # Update text fields
            if summary:
                update_data['summary'] = summary
            if education:
                update_data['education'] = education
            if experience:
                update_data['experience'] = experience
            if skills:
                update_data['skills'] = skills
            
            # Handle CV upload
            if cv_file and cv_file.filename:
                if allowed_file(cv_file.filename, {'pdf', 'doc', 'docx'}):
                    filename = secure_filename(f"{current_user.id}_cv_{cv_file.filename}")
                    cv_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'cvs', filename)
                    cv_file.save(cv_path)
                    update_data['cv_filename'] = filename
                else:
                    flash('CV must be a PDF, DOC, or DOCX file.', 'error')
                    return redirect(url_for('candidate_routes.profile'))
            
            # Handle ID card upload
            if id_card_file and id_card_file.filename:
                if allowed_file(id_card_file.filename, {'pdf', 'jpg', 'jpeg', 'png'}):
                    filename = secure_filename(f"{current_user.id}_id_{id_card_file.filename}")
                    id_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'id_cards', filename)
                    id_card_file.save(id_path)
                    update_data['id_card_filename'] = filename
                else:
                    flash('ID card must be a PDF, JPG, JPEG, or PNG file.', 'error')
                    return redirect(url_for('candidate_routes.profile'))
            
            # Handle marksheet upload
            if marksheet_file and marksheet_file.filename:
                if allowed_file(marksheet_file.filename, {'pdf', 'jpg', 'jpeg', 'png'}):
                    filename = secure_filename(f"{current_user.id}_marksheet_{marksheet_file.filename}")
                    marksheet_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'marksheets', filename)
                    marksheet_file.save(marksheet_path)
                    update_data['marksheet_filename'] = filename
                else:
                    flash('Marksheet must be a PDF, JPG, JPEG, or PNG file.', 'error')
                    return redirect(url_for('candidate_routes.profile'))
            
            # Update profile
            if update_data:
                update_candidate_profile(current_user.id, **update_data)
                flash('Profile updated successfully!', 'success')
            else:
                flash('No changes were made to your profile.', 'info')
            
            return redirect(url_for('candidate_routes.profile'))
        
        # GET request - show profile form
        profile = get_candidate_profile(current_user.id)
        return render_template('candidate/profile.html', profile=profile)
    
    except Exception as e:
        logging.error(f"Error in candidate profile: {e}")
        flash('Error updating profile. Please try again.', 'error')
        return redirect(url_for('candidate_routes.dashboard'))

@candidate_bp.route('/jobs')
def jobs():
    try:
        jobs = get_all_jobs()
        return render_template('candidate/jobs.html', jobs=jobs)
    except Exception as e:
        logging.error(f"Error loading jobs: {e}")
        flash('Error loading jobs. Please try again.', 'error')
        return redirect(url_for('index'))

@candidate_bp.route('/download/<file_type>')
@login_required
def download_file(file_type):
    try:
        profile = get_candidate_profile(current_user.id)
        if not profile:
            flash('Profile not found.', 'error')
            return redirect(url_for('candidate_routes.dashboard'))
        
        filename = None
        folder = None
        
        if file_type == 'cv' and profile.cv_filename:
            filename = profile.cv_filename
            folder = 'cvs'
        elif file_type == 'id_card' and profile.id_card_filename:
            filename = profile.id_card_filename
            folder = 'id_cards'
        elif file_type == 'marksheet' and profile.marksheet_filename:
            filename = profile.marksheet_filename
            folder = 'marksheets'
        
        if filename and folder:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder, filename)
            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True)
        
        flash('File not found.', 'error')
        return redirect(url_for('candidate_routes.profile'))
    
    except Exception as e:
        logging.error(f"Error downloading file: {e}")
        flash('Error downloading file. Please try again.', 'error')
        return redirect(url_for('candidate_routes.profile'))

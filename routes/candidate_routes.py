# jobportal/routes/candidate_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from database import get_candidate_profile, update_candidate_profile, get_all_jobs
import os
import logging

candidate_bp = Blueprint('candidate_routes', __name__)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@candidate_bp.before_request
@login_required 
def check_candidate_role():
    # If the request is for the 'jobs' endpoint within this blueprint, allow it.
    if request.endpoint == 'candidate_routes.jobs':
        logging.debug(f"User {current_user.email} accessing endpoint {request.endpoint}. Allowing without specific role check.")
        return  # Proceed to the jobs route for any authenticated user

    if current_user.role != 'candidate':
        if current_user.role == 'pending_setup' or session.get('needs_registration_completion'):
            flash('Please complete your registration to access this feature.', 'info')
            return redirect(url_for('auth_routes.complete_registration')) # Send them to complete it

        flash('Access denied. This area is for candidates only.', 'error')
        return redirect(url_for('index'))

@candidate_bp.route('/dashboard')
def dashboard():
    try:
        profile = get_candidate_profile(current_user.id)
        return render_template('candidate/dashboard.html', profile=profile)
    except Exception as e:
        logging.exception(f"Error loading candidate dashboard for user {current_user.id}:")
        flash('Error loading dashboard. Please try again.', 'error')
        return redirect(url_for('index'))

@candidate_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    try:
        if request.method == 'POST':
            update_data = {}
            update_data['summary'] = request.form.get('summary', '').strip()
                
            update_data['college_name'] = request.form.get('college_name', '').strip()
            update_data['degree'] = request.form.get('degree', '').strip()
            grad_year_str = request.form.get('graduation_year', '').strip()
            update_data['graduation_year'] = int(grad_year_str) if grad_year_str.isdigit() else None
            
            core_interests_list = request.form.getlist('core_interest_domains')
            update_data['core_interest_domains'] = ','.join(core_interests_list) if core_interests_list else None
            
            update_data['twelfth_school_type'] = request.form.get('twelfth_school_type')
            update_data['parental_annual_income'] = request.form.get('parental_annual_income')
            
            files_to_process = {
                'cv': {'ext': {'pdf', 'doc', 'docx'}, 'folder': 'cvs', 'db_field': 'cv_filename'},
                'id_card': {'ext': {'pdf', 'jpg', 'jpeg', 'png'}, 'folder': 'id_cards', 'db_field': 'id_card_filename'},
                'marksheet': {'ext': {'pdf', 'jpg', 'jpeg', 'png'}, 'folder': 'marksheets', 'db_field': 'marksheet_filename'},
                'ews_certificate': {'ext': {'pdf', 'jpg', 'jpeg', 'png'}, 'folder': 'ews_certificates', 'db_field': 'ews_certificate_filename'}
            }

            any_file_processed = False
            for form_field_name, config in files_to_process.items():
                file = request.files.get(form_field_name)
                if file and file.filename: # Check if a file was actually selected
                    any_file_processed = True
                    if allowed_file(file.filename, config['ext']):
                        filename = secure_filename(f"{current_user.id}_{form_field_name}_{file.filename}")
                        folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], config['folder'])
                        os.makedirs(folder_path, exist_ok=True)
                        file.save(os.path.join(folder_path, filename))
                        update_data[config['db_field']] = filename
                    else:
                        flash(f"{form_field_name.replace('_', ' ').title()} must be one of {', '.join(config['ext'])}.", 'error')
                        # Decide if you want to abort all updates or just skip this file
                        # For now, we'll let other text updates proceed.

            # Check if any textual data has changed or if files were processed
            # This logic can be complex if you want to detect *actual* changes vs just submitted data
            # A simpler approach is to just update if any form data (text or file) was submitted.
            if update_data or any_file_processed:
                update_candidate_profile(current_user.id, **update_data)
                flash('Profile updated successfully!', 'success')
            else:
                flash('No changes were detected in your profile.', 'info')
            
            return redirect(url_for('candidate_routes.profile'))
        
        # GET Request
        profile_data = get_candidate_profile(current_user.id)
        selected_core_interests = []
        if profile_data and profile_data.core_interest_domains:
            selected_core_interests = [interest.strip() for interest in profile_data.core_interest_domains.split(',')]
        
        available_core_interests = [
            "Web Development", "Backend Development", "Data Science", 
            "Machine Learning", "Deep Learning", "AI Engineering", "Full-Stack Development",
            "DevOps", "Cybersecurity", "Cloud Computing", "Mobile App Development"
        ]
        
        return render_template('candidate/profile.html', 
                            profile=profile_data, 
                            selected_core_interests=selected_core_interests,
                            available_core_interests=available_core_interests)
    
    except Exception as e:
        logging.exception(f"Error in candidate profile for user {current_user.id}:")
        flash(f'Error updating profile: {str(e)}. Please try again.', 'error')
        # It's better to render the profile page again with existing data if possible,
        # but redirecting for simplicity on major error.
        return redirect(url_for('candidate_routes.dashboard'))


@candidate_bp.route('/document/<file_type>') 
@candidate_bp.route('/document/<file_type>/<action>') 
def serve_candidate_document(file_type, action='download'): 
    try:
        profile = get_candidate_profile(current_user.id)
        if not profile:
            flash('Profile not found.', 'error')
            return redirect(url_for('candidate_routes.dashboard'))

        filename_map = {
            'cv': profile.cv_filename, 'id_card': profile.id_card_filename,
            'marksheet': profile.marksheet_filename, 'ews_certificate': profile.ews_certificate_filename
        }
        folder_map = {
            'cv': 'cvs', 'id_card': 'id_cards',
            'marksheet': 'marksheets', 'ews_certificate': 'ews_certificates'
        }
        viewable_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.txt'}

        filename = filename_map.get(file_type)
        folder = folder_map.get(file_type)

        if filename and folder:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder, filename)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                file_ext = os.path.splitext(filename)[1].lower()
                if action == 'view' and file_ext in viewable_extensions:
                    return send_file(file_path, as_attachment=False) 
                else:
                    return send_file(file_path, as_attachment=True)
            else:
                logging.warning(f"Candidate: File not found on server: {file_path} for user {current_user.id}")
                flash(f'{file_type.replace("_", " ").title()} file not found on server.', 'error')
        else:
            flash(f'{file_type.replace("_", " ").title()} not uploaded or link broken.', 'error')
        
        # Try to redirect back to profile page if that was the referrer
        if request.referrer and url_for('candidate_routes.profile') in request.referrer:
             return redirect(url_for('candidate_routes.profile'))
        return redirect(url_for('candidate_routes.dashboard')) # Fallback redirect

    except Exception as e:
        logging.exception(f"Error serving {file_type} ({action}) for user {current_user.id}:")
        flash(f'Error accessing {file_type.replace("_", " ").title()}. Please try again.', 'error')
        if request.referrer and url_for('candidate_routes.profile') in request.referrer:
             return redirect(url_for('candidate_routes.profile'))
        return redirect(url_for('candidate_routes.dashboard'))

@candidate_bp.route('/jobs')
def jobs():
    try:
        location_filter = request.args.get('location_filter', '').strip()
        work_model_filter = request.args.get('work_model_filter', '').strip()
        date_posted_filter = request.args.get('date_posted_filter', '').strip()
        company_filter = request.args.get('company_filter', '').strip()
        job_function_filter = request.args.get('job_function_filter', '').strip()

        jobs_list = get_all_jobs(
            location_filter=location_filter or None,
            work_model_filter=work_model_filter or None,
            date_posted_filter=date_posted_filter or None,
            company_filter=company_filter or None,
            job_function_filter=job_function_filter or None
        )
        
        return render_template('candidate/jobs.html', 
                            jobs=jobs_list,
                            search_filters={
                                'location': location_filter,
                                'work_model': work_model_filter,
                                'date_posted': date_posted_filter,
                                'company': company_filter,
                                'job_function': job_function_filter
                            })
    except Exception as e:
        logging.exception("Error loading jobs for candidate:")
        flash('Error loading jobs. Please try again.', 'error')
        return redirect(url_for('index'))

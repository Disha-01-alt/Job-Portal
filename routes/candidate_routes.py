# jobportal/routes/candidate_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from database import get_candidate_profile, update_candidate_profile, get_all_jobs, update_user_details
import os
import logging
import re # For WhatsApp number validation

candidate_bp = Blueprint('candidate_routes', __name__)

def allowed_file(filename, allowed_extensions):
    # For documents, allowed_extensions will now always be {'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@candidate_bp.before_request
@login_required 
def candidate_blueprint_checks():
    if request.endpoint == 'candidate_routes.jobs':
        logging.debug(f"User {current_user.email} accessing endpoint {request.endpoint}. Allowing.")
        return 

    if current_user.role == 'pending_setup' or session.get('needs_registration_completion'):
        flash('Please complete your registration to access this feature.', 'info')
        return redirect(url_for('auth_routes.complete_registration'))
    
    if current_user.role != 'candidate':
        logging.warning(f"Access denied for user {current_user.email} (role: {current_user.role}) to {request.endpoint}.")
        flash('Access denied. This area is for candidates only.', 'error')
        if current_user.role == 'admin': return redirect(url_for('admin_routes.dashboard'))
        if current_user.role == 'company': return redirect(url_for('company_routes.dashboard'))
        return redirect(url_for('index'))
    
    logging.debug(f"User {current_user.email} (role: {current_user.role}) accessing {request.endpoint}. Candidate check passed.")

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
    # This list is used for both GET (displaying checkboxes) and POST (validation)
    available_core_interests = [
        "Frontend Development", "Backend Development", "Full-Stack Development",
        "Data Engineering", "Data Analytics", "Data Science & Machine Learning",
        "Prompt Engineering", "Deep Learning & AI"
    ]
    profile_db_data = get_candidate_profile(current_user.id) # Get existing profile for comparison and display

    if request.method == 'POST':
        logging.debug(f"POST to /candidate/profile. Form: {request.form}, Files: {request.files}")
        
        form_errors = []
        user_update_payload = {}
        profile_update_payload = {}

        # --- Collect and Validate User Details (from users table) ---
        new_full_name = request.form.get('full_name', '').strip()
        new_whatsapp_number = request.form.get('whatsapp_number', '').strip()
        new_linkedin = request.form.get('linkedin', '').strip() # Optional
        new_github = request.form.get('github', '').strip()     # Optional

        if not new_full_name: form_errors.append("Full Name is required.")
        if not new_whatsapp_number: 
            form_errors.append("WhatsApp Number is required.")
        elif not re.fullmatch(r"^(?:\+91|91|0)?[6789]\d{9}$", new_whatsapp_number):
            form_errors.append("Invalid WhatsApp Number. Use a 10-digit Indian number, optionally with +91/91/0 prefix.")
        
        # --- Collect and Validate Candidate Profile Details ---
        summary = request.form.get('summary', '').strip()
        if not summary: form_errors.append("Summary of Skills and Strengths is required.")
        profile_update_payload['summary'] = summary
        
        college_name = request.form.get('college_name', '').strip()
        if not college_name: form_errors.append("College Name is required.")
        profile_update_payload['college_name'] = college_name
        
        degree = request.form.get('degree', '').strip()
        if not degree: form_errors.append("Degree is required.")
        profile_update_payload['degree'] = degree
        
        grad_year_str = request.form.get('graduation_year', '').strip()
        if not grad_year_str: 
            form_errors.append("Graduation Year is required.")
            profile_update_payload['graduation_year'] = None
        elif not grad_year_str.isdigit() or not (1950 <= int(grad_year_str) <= 2050):
            form_errors.append("Invalid Graduation Year. Please enter a valid year (e.g., 1950-2050).")
            profile_update_payload['graduation_year'] = None # Or keep old if invalid, or re-render
        else:
             profile_update_payload['graduation_year'] = int(grad_year_str)

        core_interests_list = request.form.getlist('core_interest_domains')
        if not core_interests_list: 
            form_errors.append("Please select at least one Core Interest Domain.")
        profile_update_payload['core_interest_domains'] = ','.join(core_interests_list) if core_interests_list else None
        
        twelfth_school_type = request.form.get('twelfth_school_type')
        if not twelfth_school_type: form_errors.append("12th School Type is required.")
        profile_update_payload['twelfth_school_type'] = twelfth_school_type
        
        parental_annual_income = request.form.get('parental_annual_income')
        if not parental_annual_income: form_errors.append("Parental Annual Income is required.")
        profile_update_payload['parental_annual_income'] = parental_annual_income

        # --- File Uploads (All PDF only) ---
        files_to_process = {
            'cv': {'ext': {'pdf'}, 'folder': 'cvs', 'db_field': 'cv_filename', 'label': 'CV/Resume', 'is_required': True},
            'id_card': {'ext': {'pdf'}, 'folder': 'id_cards', 'db_field': 'id_card_filename', 'label': 'ID Card', 'is_required': True},
            'marksheet': {'ext': {'pdf'}, 'folder': 'marksheets', 'db_field': 'marksheet_filename', 'label': '12th Marksheet', 'is_required': True},
            'ews_certificate': {'ext': {'pdf'}, 'folder': 'ews_certificates', 'db_field': 'ews_certificate_filename', 'label': 'EWS Certificate', 'is_required': False} # EWS is optional
        }
        any_new_file_processed_successfully = False

        for form_field_name, config in files_to_process.items():
            file = request.files.get(form_field_name)
            existing_filename = getattr(profile_db_data, config['db_field'], None) if profile_db_data else None
            
            if file and file.filename: 
                any_new_file_processed_successfully = True # Mark that a file processing was attempted
                if allowed_file(file.filename, config['ext']):
                    base, ext = os.path.splitext(file.filename)
                    sane_base = "".join(c if c.isalnum() or c in ['_', '-'] else '' for c in base[:50])
                    filename_to_save = secure_filename(f"{current_user.id}_{form_field_name}_{sane_base}{ext}")
                    folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], config['folder'])
                    os.makedirs(folder_path, exist_ok=True)
                    try:
                        file.save(os.path.join(folder_path, filename_to_save))
                        profile_update_payload[config['db_field']] = filename_to_save
                        logging.info(f"Saved {form_field_name} to {os.path.join(folder_path, filename_to_save)}")
                    except Exception as e_save:
                        logging.error(f"Error saving file {filename_to_save}: {e_save}")
                        form_errors.append(f"Error saving {config['label']}.")
                else:
                    form_errors.append(f"{config['label']} must be a PDF file.")
            elif config['is_required'] and not existing_filename:
                form_errors.append(f"{config['label']} is required.")

        if form_errors:
            for error in form_errors:
                flash(error, 'error')
            # Re-render form with attempted values and existing profile data
            # Create a dictionary from request.form for easy access in template
            form_data_attempt = request.form.to_dict()
            # Pass the currently selected checkboxes back too
            selected_core_interests_attempt = request.form.getlist('core_interest_domains')

            return render_template('candidate/profile.html',
                                 profile=profile_db_data, # For existing filenames, etc.
                                 form_data_attempt=form_data_attempt, # User's input attempt
                                 selected_core_interests=selected_core_interests_attempt, # User's checkbox attempt
                                 available_core_interests=available_core_interests)

        # --- If no validation errors, proceed to update database ---
        user_details_changed = False
        if new_full_name != current_user.full_name: user_update_payload['full_name'] = new_full_name; user_details_changed = True
        if new_whatsapp_number != (current_user.phone or ''): user_update_payload['phone'] = new_whatsapp_number; user_details_changed = True
        if new_linkedin != (current_user.linkedin or ''): user_update_payload['linkedin'] = new_linkedin or None; user_details_changed = True
        if new_github != (current_user.github or ''): user_update_payload['github'] = new_github or None; user_details_changed = True
        
        if user_details_changed and user_update_payload: # Ensure there's something to update
            update_user_details(current_user.id, **user_update_payload)

        # Check if profile specific text fields actually changed
        profile_text_fields_changed = False
        if profile_db_data:
            for key, value in profile_update_payload.items():
                # Exclude filenames from this specific text change check, they're handled by any_new_file_processed_successfully
                if key not in [config['db_field'] for config in files_to_process.values()]: 
                    if getattr(profile_db_data, key, None) != value:
                        profile_text_fields_changed = True
                        break
        elif any(profile_update_payload.get(key) for key in profile_update_payload if key not in [config['db_field'] for config in files_to_process.values()]):
            # New profile, so any text data is a change
            profile_text_fields_changed = True
        
        # Prepare final data for profile update, only including new files if uploaded
        final_profile_data_to_update = {}
        for key, value in profile_update_payload.items():
            is_file_db_field = any(key == cfg['db_field'] for cfg in files_to_process.values())
            if is_file_db_field:
                if value is not None: # Means a new file was processed and its name is in payload
                    final_profile_data_to_update[key] = value
            else: # Not a file field, so include it if it changed or is new
                 final_profile_data_to_update[key] = value
        
        if final_profile_data_to_update and (profile_text_fields_changed or any_new_file_processed_successfully):
            logging.debug(f"Updating candidate profile {current_user.id} with: {final_profile_data_to_update}")
            update_candidate_profile(current_user.id, **final_profile_data_to_update)
        
        if user_details_changed or profile_text_fields_changed or any_new_file_processed_successfully:
            flash('Profile updated successfully!', 'success')
        else:
            flash('No changes were detected in your profile.', 'info')
        
        return redirect(url_for('candidate_routes.profile'))
    
    # --- GET Request ---
    selected_core_interests_on_get = []
    if profile_db_data and profile_db_data.core_interest_domains:
        selected_core_interests_on_get = [interest.strip() for interest in profile_db_data.core_interest_domains.split(',')]
    
    return render_template('candidate/profile.html', 
                        profile=profile_db_data, 
                        selected_core_interests=selected_core_interests_on_get,
                        available_core_interests=available_core_interests,
                        form_data_attempt=None) # No form attempt data on initial GET

except Exception as e:
    logging.exception(f"Critical error in candidate profile for user {current_user.id}:")
    flash(f'A critical error occurred while processing your profile: {str(e)}. Please try again.', 'error')
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
        # All documents are now PDF, so they are viewable
        viewable_extensions = {'.pdf'} 

        filename = filename_map.get(file_type)
        folder = folder_map.get(file_type)

        if filename and folder:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder, filename)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                file_ext = os.path.splitext(filename)[1].lower()
                if action == 'view' and file_ext in viewable_extensions: # Should always be true if only PDF allowed
                    return send_file(file_path, as_attachment=False) 
                else: # Default to download or if somehow not PDF
                    return send_file(file_path, as_attachment=True)
            else:
                logging.warning(f"Candidate: File not found on server: {file_path} for user {current_user.id}")
                flash(f'{file_type.replace("_", " ").title()} file not found on server.', 'error')
        else:
            flash(f'{file_type.replace("_", " ").title()} not uploaded or link broken.', 'error')
        
        # Redirect to profile page if that was the referrer
        if request.referrer and url_for('candidate_routes.profile') in request.referrer:
             return redirect(url_for('candidate_routes.profile'))
        return redirect(url_for('candidate_routes.dashboard')) # Fallback

    except Exception as e:
        logging.exception(f"Error serving {file_type} ({action}) for user {current_user.id}:")
        flash(f'Error accessing {file_type.replace("_", " ").title()}. Please try again.', 'error')
        if request.referrer and url_for('candidate_routes.profile') in request.referrer:
             return redirect(url_for('candidate_routes.profile'))
        return redirect(url_for('candidate_routes.dashboard'))

@candidate_bp.route('/jobs')
def jobs():
    logging.info(f"Accessing /candidate/jobs by user: {current_user.email if current_user.is_authenticated else 'Guest'}")
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
        logging.exception("Error loading jobs page for user:")
        flash('Error loading job listings. Please try again.', 'error')
        # For a jobs page, redirecting to index on error is usually fine
        return redirect(url_for('index'))

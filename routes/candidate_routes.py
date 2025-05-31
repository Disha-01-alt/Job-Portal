# jobportal/routes/candidate_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from database import get_candidate_profile, update_candidate_profile, get_all_jobs, update_user_details
import os
import logging
import re # For WhatsApp number validation
import cloudinary # Import Cloudinary
import cloudinary.uploader # Import uploader

candidate_bp = Blueprint('candidate_routes', __name__)

def allowed_file(filename, allowed_extensions):
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
    available_core_interests = [
        "Frontend Development", "Backend Development", "Full-Stack Development",
        "Data Engineering", "Data Analytics", "Data Science & Machine Learning",
        "Prompt Engineering", "Deep Learning & AI"
    ]
    profile_db_data = get_candidate_profile(current_user.id)

# --- Job-Portal-master/routes/candidate_routes.py (Modifications in profile POST route) ---
# ... inside def profile():
    if request.method == 'POST':
        logging.debug(f"POST to /candidate/profile. Form: {request.form}, Files: {request.files}")
        
        form_errors = []
        user_update_payload = {}
        profile_update_payload = {}
        user_details_changed = False # Initialize this flag

        # Full Name is NOT taken from this form. It's read-only in the HTML.
        # Email is NOT taken from this form. It's read-only in the HTML.

        # WhatsApp Number (editable in form)
        new_whatsapp_number = request.form.get('whatsapp_number', '').strip()
        if not new_whatsapp_number: 
            form_errors.append("WhatsApp Number is required.")
        elif not re.fullmatch(r"^(?:\+91|91|0)?[6789]\d{9}$", new_whatsapp_number):
            form_errors.append("Invalid WhatsApp Number. Use a 10-digit Indian number, optionally with +91/91/0 prefix.")
        # Check for change only if no errors related to whatsapp number format/presence
        elif not any("WhatsApp Number" in error for error in form_errors) and new_whatsapp_number != (current_user.phone or ''):
            user_update_payload['phone'] = new_whatsapp_number
            user_details_changed = True
        
        # LinkedIn (now editable in form)
        new_linkedin = request.form.get('linkedin', '').strip()
        if new_linkedin != (current_user.linkedin or ''): # Allows empty string to clear
            user_update_payload['linkedin'] = new_linkedin
            user_details_changed = True
        
        # GitHub (editable in form)
        new_github = request.form.get('github', '').strip()     
        if new_github != (current_user.github or ''): # Allows empty string to clear
            user_update_payload['github'] = new_github
            user_details_changed = True

        # Summary (candidate_profiles table)
        summary = request.form.get('summary', '').strip()
        if not summary: form_errors.append("Summary of Skills and Strengths is required.")
        profile_update_payload['summary'] = summary
        
        # College Name (candidate_profiles table)
        college_name = request.form.get('college_name', '').strip()
        if not college_name: form_errors.append("College Name is required.")
        profile_update_payload['college_name'] = college_name
        
        # Degree (candidate_profiles table)
        degree = request.form.get('degree', '').strip()
        if not degree: form_errors.append("Degree is required.")
        profile_update_payload['degree'] = degree
        
        # Graduation Year (candidate_profiles table)
        grad_year_str = request.form.get('graduation_year', '').strip()
        if not grad_year_str: 
            form_errors.append("Graduation Year is required.")
            # Do not set profile_update_payload['graduation_year'] to None here if it's a validation error
            # Let it retain old value or handle None carefully in update_candidate_profile
        elif not grad_year_str.isdigit() or not (1950 <= int(grad_year_str) <= 2050):
            form_errors.append("Invalid Graduation Year. Please enter a valid year (e.g., 1950-2050).")
        else:
             profile_update_payload['graduation_year'] = int(grad_year_str)

        # Core Interest Domains (candidate_profiles table)
        core_interests_list = request.form.getlist('core_interest_domains')
        if not core_interests_list: 
            form_errors.append("Please select at least one Core Interest Domain.")
        profile_update_payload['core_interest_domains'] = ','.join(core_interests_list) if core_interests_list else None
        
        # 12th School Type (candidate_profiles table)
        twelfth_school_type = request.form.get('twelfth_school_type')
        if not twelfth_school_type: form_errors.append("12th School Type is required.")
        profile_update_payload['twelfth_school_type'] = twelfth_school_type
        
        # Parental Annual Income (candidate_profiles table)
        parental_annual_income = request.form.get('parental_annual_income')
        if not parental_annual_income: form_errors.append("Parental Annual Income is required.")
        profile_update_payload['parental_annual_income'] = parental_annual_income

        # --- File Uploads to Cloudinary (All PDF only) ---
        # ... (existing file upload logic - seems okay as per problem description) ...
        files_to_process_cloudinary = {
            'cv': {'folder': f'job_portal/user_{current_user.id}/cvs', 'db_field': 'cv_filename', 'label': 'CV/Resume', 'is_required': True},
            'id_card': {'folder': f'job_portal/user_{current_user.id}/id_cards', 'db_field': 'id_card_filename', 'label': 'ID Card', 'is_required': True},
            'marksheet': {'folder': f'job_portal/user_{current_user.id}/marksheets', 'db_field': 'marksheet_filename', 'label': '12th Marksheet', 'is_required': True},
            'ews_certificate': {'folder': f'job_portal/user_{current_user.id}/ews_certificates', 'db_field': 'ews_certificate_filename', 'label': 'EWS Certificate', 'is_required': False}
        }
        any_new_file_processed_successfully = False

        for form_field_name, config in files_to_process_cloudinary.items():
            file = request.files.get(form_field_name)
            existing_file_url = getattr(profile_db_data, config['db_field'], None) if profile_db_data else None
            
            if file and file.filename:
                original_filename = secure_filename(file.filename)
                if original_filename.lower().endswith('.pdf'):
                    any_new_file_processed_successfully = True
                    try:
                        public_id_base = os.path.splitext(original_filename)[0] # Name without original extension
                        public_id_with_ext = f"{current_user.id}_{form_field_name}_{public_id_base[:40]}.pdf" # Explicitly add .pdf
                        logging.info(f"Uploading {config['label']} to Cloudinary. Public ID: {public_id}, Folder: {config['folder']}")
                        
                        upload_result = cloudinary.uploader.upload(
                            file,
                            folder=config['folder'],
                            public_id=public_id,
                            resource_type="raw",
                            overwrite=True 
                        )
                        profile_update_payload[config['db_field']] = upload_result['secure_url']
                        logging.info(f"Uploaded {config['label']} to Cloudinary: {upload_result['secure_url']}")
                    except Exception as e_cloudinary:
                        logging.error(f"Cloudinary upload error for {config['label']}: {e_cloudinary}")
                        form_errors.append(f"Error uploading {config['label']}. Please try again.")
                else:
                    form_errors.append(f"{config['label']} must be a PDF file.")
            elif config['is_required'] and not existing_file_url:
                form_errors.append(f"{config['label']} is required.")


        if form_errors:
            for error_msg in form_errors:
                flash(error_msg, 'error')
            form_data_attempt = request.form.to_dict() # Keep this
            # Ensure selected_core_interests_attempt is correctly set for re-rendering
            selected_core_interests_attempt = request.form.getlist('core_interest_domains')
            return render_template('candidate/profile.html',
                                 profile=profile_db_data, 
                                 form_data_attempt=form_data_attempt, 
                                 selected_core_interests=selected_core_interests_attempt, # Pass this back
                                 available_core_interests=available_core_interests) # And this

        # --- If no validation errors, proceed to update database ---
        
        if user_details_changed and user_update_payload: # Only update if changed and payload exists
            logging.debug(f"Updating user (users table) for {current_user.id} with: {user_update_payload}")
            update_user_details(current_user.id, **user_update_payload)

        profile_text_fields_changed = False
        if profile_db_data: # Check against existing profile data
            for key, value in profile_update_payload.items():
                # Exclude file fields from this specific text change check, they are handled by any_new_file_processed_successfully
                if key not in [config['db_field'] for config in files_to_process_cloudinary.values()]: 
                    if getattr(profile_db_data, key, None) != value:
                        profile_text_fields_changed = True
                        break
        elif any(profile_update_payload.get(key) for key in profile_update_payload if key not in [config['db_field'] for config in files_to_process_cloudinary.values()]):
             # If no profile_db_data, any text field with a value is a change
            profile_text_fields_changed = True

        if profile_update_payload and (profile_text_fields_changed or any_new_file_processed_successfully):
            logging.debug(f"Updating candidate_profiles for {current_user.id} with: {profile_update_payload}")
            update_candidate_profile(current_user.id, **profile_update_payload)
        
        if user_details_changed or (profile_update_payload and (profile_text_fields_changed or any_new_file_processed_successfully)):
            flash('Profile updated successfully!', 'success')
        else:
            flash('No changes were detected in your profile.', 'info')
        
        return redirect(url_for('candidate_routes.profile'))
    
    # --- GET Request ---
    # ... (existing GET logic should be fine) ...
    
    # --- GET Request (logic as before) ---
    selected_core_interests_on_get = []
    if profile_db_data and profile_db_data.core_interest_domains:
        selected_core_interests_on_get = [interest.strip() for interest in profile_db_data.core_interest_domains.split(',')]
    
    return render_template('candidate/profile.html', 
                        profile=profile_db_data, 
                        selected_core_interests=selected_core_interests_on_get,
                        available_core_interests=available_core_interests,
                        form_data_attempt=None)

    # except Exception as e: # This was the line with the syntax error in your previous log
    #     logging.exception(f"Critical error in candidate profile for user {current_user.id}:")
    #     flash(f'A critical error occurred while processing your profile: {str(e)}. Please try again.', 'error')
    #     return redirect(url_for('candidate_routes.dashboard'))
    # THE TRY-EXCEPT FOR THE WHOLE FUNCTION WAS MOVED TO WRAP THE ENTIRE CONTENT

# @candidate_bp.route('/document/<file_type>') 
# @candidate_bp.route('/document/<file_type>/<action>') 
# def serve_candidate_document(file_type, action='download'): 
#     try:
#         profile = get_candidate_profile(current_user.id)
#         if not profile:
#             flash('Profile not found.', 'error')
#             return redirect(url_for('candidate_routes.dashboard'))

#         filename_map = {
#             'cv': profile.cv_filename, 'id_card': profile.id_card_filename,
#             'marksheet': profile.marksheet_filename, 'ews_certificate': profile.ews_certificate_filename
#         }
#         folder_map = {
#             'cv': 'cvs', 'id_card': 'id_cards',
#             'marksheet': 'marksheets', 'ews_certificate': 'ews_certificates'
#         }
#         viewable_extensions = {'.pdf'} 

#         filename = filename_map.get(file_type)
#         folder = folder_map.get(file_type)

#         if filename and folder:
#             file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder, filename)
#             if os.path.exists(file_path) and os.path.isfile(file_path):
#                 file_ext = os.path.splitext(filename)[1].lower()
#                 if action == 'view' and file_ext in viewable_extensions: 
#                     return send_file(file_path, as_attachment=False) 
#                 else: 
#                     return send_file(file_path, as_attachment=True)
#             else:
#                 logging.warning(f"Candidate: File not found on server: {file_path} for user {current_user.id}")
#                 flash(f'{file_type.replace("_", " ").title()} file not found on server.', 'error')
#         else:
#             flash(f'{file_type.replace("_", " ").title()} not uploaded or link broken.', 'error')
        
#         if request.referrer and url_for('candidate_routes.profile') in request.referrer:
#              return redirect(url_for('candidate_routes.profile'))
#         return redirect(url_for('candidate_routes.dashboard'))

#     except Exception as e: # General exception for this route
#         logging.exception(f"Error serving document {file_type} ({action}) for user {current_user.id}:")
#         flash(f'Error accessing {file_type.replace("_", " ").title()}. Please try again.', 'error')
#         if request.referrer and url_for('candidate_routes.profile') in request.referrer:
#              return redirect(url_for('candidate_routes.profile'))
#         return redirect(url_for('candidate_routes.dashboard'))

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
    except Exception as e: # This is line 214 from your traceback
        logging.exception("Error loading jobs page for user:") 
        flash('Error loading job listings. Please try again.', 'error')
        return redirect(url_for('index'))

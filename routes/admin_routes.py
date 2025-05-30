# jobportal/routes/admin_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
from database import (get_all_jobs, create_job, get_all_candidates, 
                     update_candidate_rating_feedback, delete_job as db_delete_job,
                     get_job_by_id, update_job as db_update_job, 
                     get_candidate_profile, get_pending_companies, 
                     approve_company as db_approve_company, get_candidate_details_by_id)
from job_extractor import extract_job_from_linkedin 
import os
import logging

admin_bp = Blueprint('admin_routes', __name__)

# Custom Exception (optional, if your job_extractor might raise it)
class JobExtractionError(Exception):
    pass

@admin_bp.before_request
@login_required 
def check_admin_role():
    if not current_user.is_authenticated: 
        return redirect(url_for('auth_routes.login')) 
    if current_user.role != 'admin':
        flash('Access denied. This area is for administrators only.', 'error')
        return redirect(url_for('index'))

def get_available_job_tags(): 
    return [
        "Engineering", "Information Technology", "Marketing", "Sales", 
        "Business Development", "Human Resources", "Operations", "Finance", 
        "Customer Service", "Product Management", "Administrative", "Design",
        "Software Development", "Data Science", "AI/ML", "Cloud Computing",
        "Cybersecurity", "DevOps", "Project Management", "Content Creation",
        "Digital Marketing", "Consulting", "Healthcare", "Education"
    ]

def get_available_admin_skill_tags():
    return [
        "Frontend Development", "Backend Development", "Full-Stack Development",
        "Data Engineering", "Data Analytics", "Data Science & Machine Learning",
        "Prompt Engineering", "Deep Learning & AI"
    ]

@admin_bp.route('/dashboard')
def dashboard():
    try:
        jobs = get_all_jobs() 
        candidates = get_all_candidates() 
        pending_companies_list = get_pending_companies()
        
        total_jobs = len(jobs)
        total_candidates = len(candidates)
        rated_candidates = len([c for c in candidates if c.get('rating') is not None]) 
        
        stats = {
            'total_jobs': total_jobs,
            'total_candidates': total_candidates,
            'rated_candidates': rated_candidates,
            'pending_reviews': total_candidates - rated_candidates,
            'pending_companies': len(pending_companies_list)
        }
        
        recent_jobs_display = jobs[:5] 
        recent_candidates_display = candidates[:5]

        return render_template('admin/dashboard.html', stats=stats, 
                             recent_jobs=recent_jobs_display, 
                             recent_candidates=recent_candidates_display,
                             pending_companies=pending_companies_list)
    except Exception as e:
        logging.exception("Error loading admin dashboard:") 
        flash('Error loading dashboard. Please try again.', 'error')
        return redirect(url_for('index'))

@admin_bp.route('/add_job', methods=['GET', 'POST'])
def add_job():
    if request.method == 'POST':
        linkedin_url = request.form.get('linkedin_url', '').strip()
        manual_title = request.form.get('manual_title', '').strip()
        manual_company = request.form.get('manual_company', '').strip()
        manual_location = request.form.get('manual_location', '').strip()
        manual_description = request.form.get('manual_description', '').strip()
        manual_requirements = request.form.get('manual_requirements', '').strip()
        manual_salary_range = request.form.get('manual_salary_range', '').strip()
        manual_job_type = request.form.get('manual_job_type', '').strip()
        manual_linkedin_url_field = request.form.get('manual_linkedin_url', '').strip()
        
        job_tags_list = request.form.getlist('job_tags') 
        job_tags_str = ','.join(tag.strip() for tag in job_tags_list if tag.strip()) or None
        form_source = request.form.get('form_source') # Hidden input: 'ai_extraction' or 'manual_entry'

        try:
            if not hasattr(current_user, 'id') or not isinstance(current_user.id, int):
                flash("Error: User session is invalid. Please log in again.", "error")
                return redirect(url_for('auth_routes.login'))

            if form_source == 'ai_extraction' and linkedin_url:
                flash('Extracting job information. This may take a moment...', 'info')
                job_data = extract_job_from_linkedin(linkedin_url)
                
                if not job_data or "extraction failed" in str(job_data.get('title','')).lower() or \
                   "authentication required" in str(job_data.get('title','')).lower() or \
                   not job_data.get('title') or not job_data.get('company'):
                    flash('AI Job extraction failed or essential data missing. Please review or try manual entry.', 'error')
                    return render_template('admin/add_job.html', 
                                         extracted_job_data=job_data, 
                                         linkedin_url_for_ai=linkedin_url,
                                         available_job_tags=get_available_job_tags(),
                                         # Pass back manual fields too in case user was switching
                                         job={'title': manual_title, 'company': manual_company, 'location': manual_location, 
                                              'description': manual_description, 'requirements': manual_requirements, 
                                              'salary_range': manual_salary_range, 'job_type': manual_job_type,
                                              'linkedin_url': manual_linkedin_url_field, 'job_tags_list': job_tags_list }
                                         )

                job_id = create_job(
                    title=job_data.get('title'), company=job_data.get('company'),
                    location=job_data.get('location'), description=job_data.get('description'),
                    requirements=job_data.get('requirements'), posted_by=current_user.id,
                    salary_range=job_data.get('salary_range'), job_type=job_data.get('job_type'),
                    linkedin_url=linkedin_url, job_tags=job_tags_str
                )
                flash(f'Job "{job_data.get("title")}" (ID: {job_id}) extracted and saved!', 'success')
                return redirect(url_for('admin_routes.manage_jobs'))

            elif form_source == 'manual_entry' and manual_title and manual_company:
                job_id = create_job(
                    title=manual_title, company=manual_company, location=manual_location,
                    description=manual_description, requirements=manual_requirements,
                    posted_by=current_user.id, salary_range=manual_salary_range,
                    job_type=manual_job_type, linkedin_url=manual_linkedin_url_field or None,
                    job_tags=job_tags_str
                )
                flash(f'Job "{manual_title}" (ID: {job_id}) manually added!', 'success')
                return redirect(url_for('admin_routes.manage_jobs'))
            else:
                if form_source == 'ai_extraction' and not linkedin_url:
                     flash('Please provide a LinkedIn URL for AI extraction.', 'error')
                elif form_source == 'manual_entry' and (not manual_title or not manual_company):
                     flash('For manual entry, Job Title and Company are required.', 'error')
                else: # Should not happen if form_source is always set
                    flash('Invalid submission. Please select an action.', 'error')
        
        except Exception as e:
            logging.exception(f"Error in add_job: {e}")
            flash(f'An error occurred: {str(e)}. Please try again.', 'error')
            # Repopulate form with submitted data on error
            return render_template('admin/add_job.html', 
                                 linkedin_url_for_ai=linkedin_url,
                                 available_job_tags=get_available_job_tags(),
                                 job={'title': manual_title, 'company': manual_company, 'location': manual_location, 
                                      'description': manual_description, 'requirements': manual_requirements, 
                                      'salary_range': manual_salary_range, 'job_type': manual_job_type,
                                      'linkedin_url': manual_linkedin_url_field, 'job_tags_list': job_tags_list }
                                 )
    # GET request
    return render_template('admin/add_job.html', available_job_tags=get_available_job_tags())

@admin_bp.route('/manage_jobs')
def manage_jobs():
    try:
        jobs = get_all_jobs() 
        return render_template('admin/manage_jobs.html', jobs=jobs)
    except Exception as e:
        logging.exception("Error loading/displaying jobs in manage_jobs:")
        flash('Error loading jobs page. Please try again.', 'error')
        return redirect(url_for('admin_routes.dashboard'))

@admin_bp.route('/edit_job/<int:job_id>', methods=['GET', 'POST'])
def edit_job(job_id):
    job = get_job_by_id(job_id) 
    if not job:
        flash('Job not found.', 'error')
        return redirect(url_for('admin_routes.manage_jobs'))
    
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            company = request.form.get('company', '').strip()
            location = request.form.get('location', '').strip()
            description = request.form.get('description', '').strip()
            requirements = request.form.get('requirements', '').strip()
            salary_range = request.form.get('salary_range', '').strip()
            job_type = request.form.get('job_type', '').strip()
            linkedin_url_form = request.form.get('linkedin_url', '').strip()
            
            job_tags_list = request.form.getlist('job_tags')
            job_tags_str = ','.join(tag.strip() for tag in job_tags_list if tag.strip()) or None

            if not title or not company or not description: 
                flash('Title, Company, and Description are required.', 'error')
                job_data_for_template = job.__dict__.copy()
                job_data_for_template.update(request.form.to_dict(flat=False)) # Use flat=False for lists
                job_data_for_template['job_tags_list'] = job_tags_list # Ensure this is set correctly
                return render_template('admin/add_job.html', job=job_data_for_template, edit_mode=True, available_job_tags=get_available_job_tags())

            db_update_job(
                job_id, title=title, company=company, location=location or None,
                description=description, requirements=requirements or None,
                salary_range=salary_range or None, job_type=job_type or None,
                linkedin_url=linkedin_url_form or None, job_tags=job_tags_str
            )
            flash('Job updated successfully!', 'success')
            return redirect(url_for('admin_routes.manage_jobs'))
        except Exception as e:
            logging.exception(f"Error editing job {job_id}:")
            flash(f'Error editing job: {str(e)}', 'error')
            job_data_for_template = job.__dict__.copy()
            job_data_for_template.update(request.form.to_dict(flat=False))
            job_data_for_template['job_tags_list'] = request.form.getlist('job_tags') # Get again
            return render_template('admin/add_job.html', job=job_data_for_template, edit_mode=True, available_job_tags=get_available_job_tags())

    # GET request
    job_data_for_template = job.__dict__.copy() 
    selected_job_tags = [tag.strip() for tag in (job.job_tags.split(',') if job.job_tags else [])]
    job_data_for_template['job_tags_list'] = selected_job_tags
    return render_template('admin/add_job.html', job=job_data_for_template, edit_mode=True, available_job_tags=get_available_job_tags())

@admin_bp.route('/delete_job/<int:job_id>')
def delete_job_route(job_id):
    try:
        job = get_job_by_id(job_id)
        if not job:
            flash('Job not found.', 'error')
        else:
            job_title_to_display = job.title or f"ID {job_id}"
            db_delete_job(job_id)
            flash(f'Job "{job_title_to_display}" has been deleted.', 'success')
    except Exception as e:
        logging.exception(f"Error deleting job {job_id}:")
        flash('Error deleting job. Please try again.', 'error')
    return redirect(url_for('admin_routes.manage_jobs'))

@admin_bp.route('/review_candidates')
def review_candidates():
    try:
        candidates = get_all_candidates() 
        return render_template('admin/review_candidates.html', candidates=candidates)
    except Exception as e:
        logging.exception("Error loading candidates for review:")
        flash('Error loading candidates. Please try again.', 'error')
        return redirect(url_for('admin_routes.dashboard'))

@admin_bp.route('/candidate_detail/<int:candidate_id>')
def candidate_detail(candidate_id):
    try:
        candidate = get_candidate_details_by_id(candidate_id) 
        if not candidate:
            flash('Candidate not found.', 'error')
            return redirect(url_for('admin_routes.review_candidates'))
        
        selected_admin_tags = [tag.strip() for tag in candidate.get('admin_tags', '').split(',') if tag.strip()] \
            if candidate.get('admin_tags') else []
        
        return render_template('admin/candidate_detail.html', 
                            candidate=candidate,
                            selected_admin_tags=selected_admin_tags,
                            available_admin_skill_tags=get_available_admin_skill_tags())
    except Exception as e:
        logging.exception(f"Error loading candidate detail for ID {candidate_id}:")
        flash('Error loading candidate details. Please try again.', 'error')
        return redirect(url_for('admin_routes.review_candidates'))

@admin_bp.route('/rate_candidate/<int:candidate_id>', methods=['POST'])
def rate_candidate(candidate_id):
    try:
        rating_str = request.form.get('rating')
        feedback = request.form.get('feedback', '').strip()
        admin_tags_list = request.form.getlist('admin_tags')
        admin_tags = ','.join(admin_tags_list) if admin_tags_list else None
        is_certified = True if request.form.get('is_certified') == 'on' else False
        
        rating = None 
        if rating_str: 
            try:
                rating = int(rating_str)
                if not (1 <= rating <= 5): 
                    flash('Invalid rating. Must be between 1 and 5.', 'error')
                    return redirect(url_for('admin_routes.candidate_detail', candidate_id=candidate_id))
            except ValueError:
                flash('Invalid rating format.', 'error')
                return redirect(url_for('admin_routes.candidate_detail', candidate_id=candidate_id))
        
        update_candidate_rating_feedback(candidate_id, rating, feedback, admin_tags, is_certified)
        flash('Candidate review updated successfully!', 'success')
        return redirect(url_for('admin_routes.candidate_detail', candidate_id=candidate_id)) 
    
    except Exception as e:
        logging.exception(f"Error rating candidate {candidate_id}:")
        flash('Error updating candidate review. Please try again.', 'error')
        return redirect(url_for('admin_routes.candidate_detail', candidate_id=candidate_id))

@admin_bp.route('/document/<int:candidate_id>/<file_type>')
@admin_bp.route('/document/<int:candidate_id>/<file_type>/<action>')
def serve_admin_document(candidate_id, file_type, action='download'):
    try:
        profile = get_candidate_profile(candidate_id) 
        if not profile:
            flash('Candidate profile not found.', 'error')
            # Redirect to a sensible place if profile not found during document access
            return redirect(request.referrer or url_for('admin_routes.review_candidates'))


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
                logging.warning(f"Admin: File not found: {file_path} for cand {candidate_id}")
                flash(f'{file_type.replace("_", " ").title()} file not found on server.', 'error')
        else:
            flash(f'{file_type.replace("_", " ").title()} not uploaded or link broken.', 'error')
        
        # Smart redirect back to candidate detail if possible, else to review list
        if request.referrer and str(candidate_id) in request.referrer and 'candidate_detail' in request.referrer:
            return redirect(url_for('admin_routes.candidate_detail', candidate_id=candidate_id))
        return redirect(url_for('admin_routes.review_candidates'))

    except Exception as e:
        logging.exception(f"Error admin serving {file_type} ({action}) for cand {candidate_id}:")
        flash(f'Error accessing {file_type.replace("_", " ").title()}. Please try again.', 'error')
        if request.referrer and str(candidate_id) in request.referrer and 'candidate_detail' in request.referrer:
            return redirect(url_for('admin_routes.candidate_detail', candidate_id=candidate_id))
        return redirect(url_for('admin_routes.review_candidates'))

@admin_bp.route('/approve_company/<int:company_id>')
def approve_company_route(company_id):
    try:
        if db_approve_company(company_id):
            flash('Company approved successfully!', 'success')
        else:
            flash('Failed to approve company. Already approved or issue occurred.', 'warning')
    except Exception as e:
        logging.exception(f"Error approving company {company_id}:")
        flash('Error approving company. Please try again.', 'error')
    return redirect(url_for('admin_routes.dashboard'))

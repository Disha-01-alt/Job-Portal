from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
from database import (get_all_jobs, create_job, get_all_candidates, 
                     update_candidate_rating_feedback, delete_job, 
                     get_job_by_id, update_job, get_candidate_profile,
                     get_pending_companies, approve_company)
from job_extractor import extract_job_from_linkedin
import os
import logging

admin_bp = Blueprint('admin_routes', __name__)

@admin_bp.before_request
def check_admin_role():
    if current_user.is_authenticated and current_user.role != 'admin':
        flash('Access denied. This area is for administrators only.', 'error')
        return redirect(url_for('index'))

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    try:
        jobs = get_all_jobs()
        candidates = get_all_candidates()
        pending_companies = get_pending_companies()
        
        # Calculate statistics
        total_jobs = len(jobs)
        total_candidates = len(candidates)
        rated_candidates = len([c for c in candidates if c['rating']])
        
        stats = {
            'total_jobs': total_jobs,
            'total_candidates': total_candidates,
            'rated_candidates': rated_candidates,
            'pending_reviews': total_candidates - rated_candidates,
            'pending_companies': len(pending_companies)
        }
        
        return render_template('admin/dashboard.html', stats=stats, 
                             recent_jobs=jobs[:5], recent_candidates=candidates[:5],
                             pending_companies=pending_companies)
    except Exception as e:
        logging.error(f"Error loading admin dashboard: {e}")
        flash('Error loading dashboard. Please try again.', 'error')
        return redirect(url_for('index'))

@admin_bp.route('/add_job', methods=['GET', 'POST'])
@login_required
def add_job():
    if request.method == 'POST':
        linkedin_url = request.form.get('linkedin_url', '').strip()
        
        if not linkedin_url:
            flash('Please provide a LinkedIn job URL.', 'error')
            return render_template('admin/add_job.html')
        
        try:
            # Extract job data using Gemini AI
            flash('Extracting job information from LinkedIn...', 'info')
            job_data = extract_job_from_linkedin(linkedin_url)
            
            # Create job in database
            job_id = create_job(
                title=job_data['title'],
                company=job_data['company'],
                location=job_data['location'],
                description=job_data['description'],
                requirements=job_data['requirements'],
                posted_by=current_user.id,
                salary_range=job_data.get('salary_range'),
                job_type=job_data.get('job_type'),
                linkedin_url=linkedin_url
            )
            
            flash(f'Job "{job_data["title"]}" at {job_data["company"]} has been successfully extracted and saved!', 'success')
            return redirect(url_for('admin_routes.manage_jobs'))
        
        except Exception as e:
            logging.error(f"Error extracting job: {e}")
            flash(f'Error extracting job information: {str(e)}', 'error')
    
    return render_template('admin/add_job.html')

@admin_bp.route('/manage_jobs')
@login_required
def manage_jobs():
    try:
        jobs = get_all_jobs()
        return render_template('admin/manage_jobs.html', jobs=jobs)
    except Exception as e:
        logging.error(f"Error loading jobs: {e}")
        flash('Error loading jobs. Please try again.', 'error')
        return redirect(url_for('admin_routes.dashboard'))

@admin_bp.route('/edit_job/<int:job_id>', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    try:
        job = get_job_by_id(job_id)
        if not job:
            flash('Job not found.', 'error')
            return redirect(url_for('admin_routes.manage_jobs'))
        
        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            company = request.form.get('company', '').strip()
            location = request.form.get('location', '').strip()
            description = request.form.get('description', '').strip()
            requirements = request.form.get('requirements', '').strip()
            salary_range = request.form.get('salary_range', '').strip()
            job_type = request.form.get('job_type', '').strip()
            
            if not all([title, company, location, description, requirements]):
                flash('Please fill in all required fields.', 'error')
                return render_template('admin/add_job.html', job=job, edit_mode=True)
            
            # Update job
            update_job(
                job_id,
                title=title,
                company=company,
                location=location,
                description=description,
                requirements=requirements,
                salary_range=salary_range or None,
                job_type=job_type or None
            )
            
            flash('Job updated successfully!', 'success')
            return redirect(url_for('admin_routes.manage_jobs'))
        
        return render_template('admin/add_job.html', job=job, edit_mode=True)
    
    except Exception as e:
        logging.error(f"Error editing job: {e}")
        flash('Error editing job. Please try again.', 'error')
        return redirect(url_for('admin_routes.manage_jobs'))

@admin_bp.route('/delete_job/<int:job_id>')
@login_required
def delete_job_route(job_id):
    try:
        job = get_job_by_id(job_id)
        if not job:
            flash('Job not found.', 'error')
        else:
            delete_job(job_id)
            flash(f'Job "{job.title}" has been deleted.', 'success')
    except Exception as e:
        logging.error(f"Error deleting job: {e}")
        flash('Error deleting job. Please try again.', 'error')
    
    return redirect(url_for('admin_routes.manage_jobs'))

@admin_bp.route('/review_candidates')
@login_required
def review_candidates():
    try:
        candidates = get_all_candidates()
        return render_template('admin/review_candidates.html', candidates=candidates)
    except Exception as e:
        logging.error(f"Error loading candidates: {e}")
        flash('Error loading candidates. Please try again.', 'error')
        return redirect(url_for('admin_routes.dashboard'))

@admin_bp.route('/candidate_detail/<int:candidate_id>')
@login_required
def candidate_detail(candidate_id):
    try:
        candidates = get_all_candidates()
        candidate = next((c for c in candidates if c['id'] == candidate_id), None)
        
        if not candidate:
            flash('Candidate not found.', 'error')
            return redirect(url_for('admin_routes.review_candidates'))
        
        return render_template('admin/candidate_detail.html', candidate=candidate)
    except Exception as e:
        logging.error(f"Error loading candidate detail: {e}")
        flash('Error loading candidate details. Please try again.', 'error')
        return redirect(url_for('admin_routes.review_candidates'))

@admin_bp.route('/rate_candidate/<int:candidate_id>', methods=['POST'])
@login_required
def rate_candidate(candidate_id):
    try:
        rating = request.form.get('rating')
        feedback = request.form.get('feedback', '').strip()
        
        if not rating:
            flash('Please provide a rating.', 'error')
            return redirect(url_for('admin_routes.candidate_detail', candidate_id=candidate_id))
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError("Rating must be between 1 and 5")
        except ValueError:
            flash('Invalid rating. Please select a rating between 1 and 5.', 'error')
            return redirect(url_for('admin_routes.candidate_detail', candidate_id=candidate_id))
        
        # Update candidate rating and feedback
        update_candidate_rating_feedback(candidate_id, rating, feedback)
        
        flash('Candidate rating and feedback updated successfully!', 'success')
        return redirect(url_for('admin_routes.review_candidates'))
    
    except Exception as e:
        logging.error(f"Error rating candidate: {e}")
        flash('Error updating candidate rating. Please try again.', 'error')
        return redirect(url_for('admin_routes.candidate_detail', candidate_id=candidate_id))

@admin_bp.route('/download_cv/<int:candidate_id>')
@login_required
def download_cv(candidate_id):
    try:
        profile = get_candidate_profile(candidate_id)
        if not profile or not profile.cv_filename:
            flash('CV not found.', 'error')
            return redirect(url_for('admin_routes.candidate_detail', candidate_id=candidate_id))
        
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'cvs', profile.cv_filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            flash('CV file not found on server.', 'error')
            return redirect(url_for('admin_routes.candidate_detail', candidate_id=candidate_id))
    
    except Exception as e:
        logging.error(f"Error downloading CV: {e}")
        flash('Error downloading CV. Please try again.', 'error')
        return redirect(url_for('admin_routes.candidate_detail', candidate_id=candidate_id))

@admin_bp.route('/approve_company/<int:company_id>')
@login_required
def approve_company_route(company_id):
    check_admin_role()
    try:
        if approve_company(company_id):
            flash('Company has been approved successfully!', 'success')
        else:
            flash('Error approving company. Please try again.', 'error')
    except Exception as e:
        logging.error(f"Error approving company: {e}")
        flash('Error approving company. Please try again.', 'error')
    
    return redirect(url_for('admin_routes.dashboard'))

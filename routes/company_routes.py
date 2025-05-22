from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
from database import search_candidates, get_candidate_profile
import os
import logging

company_bp = Blueprint('company_routes', __name__)

@company_bp.before_request
def check_company_role():
    if current_user.is_authenticated and current_user.role != 'company':
        flash('Access denied. This area is for company representatives only.', 'error')
        return redirect(url_for('index'))

@company_bp.route('/dashboard')
@login_required
def dashboard():
    try:
        if not current_user.is_approved:
            flash('Your account is pending approval. Please contact the administrator.', 'warning')
            return render_template('company/dashboard.html', pending_approval=True)
        
        # Get recent candidates for quick overview
        recent_candidates = search_candidates()[:10]
        
        return render_template('company/dashboard.html', 
                             recent_candidates=recent_candidates,
                             pending_approval=False)
    except Exception as e:
        logging.error(f"Error loading company dashboard: {e}")
        flash('Error loading dashboard. Please try again.', 'error')
        return redirect(url_for('index'))

@company_bp.route('/search_candidates')
@login_required
def search_candidates_route():
    if not current_user.is_approved:
        flash('Your account is pending approval. Please contact the administrator.', 'warning')
        return redirect(url_for('company_routes.dashboard'))
    
    try:
        # Get search parameters
        skills = request.args.get('skills', '').strip()
        education = request.args.get('education', '').strip()
        experience = request.args.get('experience', '').strip()
        min_rating = request.args.get('min_rating', '').strip()
        
        # Convert min_rating to int if provided
        if min_rating:
            try:
                min_rating = int(min_rating)
                if min_rating < 1 or min_rating > 5:
                    min_rating = None
            except ValueError:
                min_rating = None
        else:
            min_rating = None
        
        # Search candidates
        candidates = search_candidates(
            skills=skills or None,
            education=education or None,
            experience=experience or None,
            min_rating=min_rating
        )
        
        # Prepare search filters for template
        search_filters = {
            'skills': skills,
            'education': education,
            'experience': experience,
            'min_rating': min_rating
        }
        
        return render_template('company/search_candidates.html', 
                             candidates=candidates,
                             search_filters=search_filters)
    
    except Exception as e:
        logging.error(f"Error searching candidates: {e}")
        flash('Error searching candidates. Please try again.', 'error')
        return redirect(url_for('company_routes.dashboard'))

@company_bp.route('/candidate_detail/<int:candidate_id>')
@login_required
def candidate_detail(candidate_id):
    if not current_user.is_approved:
        flash('Your account is pending approval. Please contact the administrator.', 'warning')
        return redirect(url_for('company_routes.dashboard'))
    
    try:
        # Search for the specific candidate
        candidates = search_candidates()
        candidate = next((c for c in candidates if c['id'] == candidate_id), None)
        
        if not candidate:
            flash('Candidate not found.', 'error')
            return redirect(url_for('company_routes.search_candidates_route'))
        
        return render_template('company/candidate_detail.html', candidate=candidate)
    
    except Exception as e:
        logging.error(f"Error loading candidate detail: {e}")
        flash('Error loading candidate details. Please try again.', 'error')
        return redirect(url_for('company_routes.search_candidates_route'))

@company_bp.route('/download_cv/<int:candidate_id>')
@login_required
def download_cv(candidate_id):
    if not current_user.is_approved:
        flash('Your account is pending approval. Please contact the administrator.', 'warning')
        return redirect(url_for('company_routes.dashboard'))
    
    try:
        profile = get_candidate_profile(candidate_id)
        if not profile or not profile.cv_filename:
            flash('CV not found.', 'error')
            return redirect(url_for('company_routes.candidate_detail', candidate_id=candidate_id))
        
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'cvs', profile.cv_filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            flash('CV file not found on server.', 'error')
            return redirect(url_for('company_routes.candidate_detail', candidate_id=candidate_id))
    
    except Exception as e:
        logging.error(f"Error downloading CV: {e}")
        flash('Error downloading CV. Please try again.', 'error')
        return redirect(url_for('company_routes.candidate_detail', candidate_id=candidate_id))

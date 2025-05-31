# jobportal/models.py

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin):
    # ... (no changes here for now) ...
    def __init__(self, user_id, email, password_hash, role, full_name=None, 
                 phone=None, linkedin=None, github=None, created_at=None, 
                 is_approved=True):
        self.id = user_id
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.full_name = full_name
        self.phone = phone
        self.linkedin = linkedin
        self.github = github
        self.created_at = created_at or datetime.now()
        self.is_approved = is_approved

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def create_password_hash(password):
        return generate_password_hash(password)

class CandidateProfile:
    def __init__(self, user_id, summary=None,cv_filename=None, id_card_filename=None, 
                 marksheet_filename=None, rating=None, admin_feedback=None,
                 created_at=None, # This was in your original file, but DB schema puts it in users
                                   # and has `updated_at` in candidate_profiles. Let's align.
                 updated_at=None, # Corresponds to updated_at in DB schema
                 # New fields
                 ews_certificate_filename=None,
                 college_name=None,
                 degree=None,
                 graduation_year=None,
                 core_interest_domains=None,
                 twelfth_school_type=None,
                 parental_annual_income=None,
                 admin_tags=None,
                 is_certified=False
                 ):
        self.user_id = user_id
        self.summary = summary
        self.cv_filename = cv_filename
        self.id_card_filename = id_card_filename
        self.marksheet_filename = marksheet_filename
        self.rating = rating
        self.admin_feedback = admin_feedback
        # self.created_at = created_at or datetime.now() # Belongs to user table
        self.updated_at = updated_at or datetime.now()

        # New fields
        self.ews_certificate_filename = ews_certificate_filename
        self.college_name = college_name
        self.degree = degree
        self.graduation_year = graduation_year
        self.core_interest_domains = core_interest_domains # Store as comma-separated string or JSON string
        self.twelfth_school_type = twelfth_school_type
        self.parental_annual_income = parental_annual_income
        self.admin_tags = admin_tags # Store as comma-separated string or JSON string
        self.is_certified = is_certified


class Job:
    def __init__(self, job_id, title, company, location, description, 
                 requirements, salary_range=None, job_type=None, 
                 posted_by=None, created_at=None, linkedin_url=None,
                 # New field
                 job_tags=None):
        self.id = job_id
        self.title = title
        self.company = company
        self.location = location
        self.description = description
        self.requirements = requirements
        self.salary_range = salary_range
        self.job_type = job_type # Can be used for On-Site/Remote/Hybrid
        self.posted_by = posted_by
        self.created_at = created_at or datetime.now()
        self.linkedin_url = linkedin_url
        # New field
        self.job_tags = job_tags # Store as comma-separated string or JSON string

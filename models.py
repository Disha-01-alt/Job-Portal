from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin):
    def __init__(self, user_id, email, password_hash, role, full_name=None, 
                 phone=None, linkedin=None, github=None, created_at=None, 
                 is_approved=True):
        self.id = user_id
        self.email = email
        self.password_hash = password_hash
        self.role = role  # 'candidate', 'admin', 'company'
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
    def __init__(self, user_id, summary=None, education=None, experience=None, 
                 skills=None, cv_filename=None, id_card_filename=None, 
                 marksheet_filename=None, rating=None, admin_feedback=None):
        self.user_id = user_id
        self.summary = summary
        self.education = education
        self.experience = experience
        self.skills = skills
        self.cv_filename = cv_filename
        self.id_card_filename = id_card_filename
        self.marksheet_filename = marksheet_filename
        self.rating = rating
        self.admin_feedback = admin_feedback

class Job:
    def __init__(self, job_id, title, company, location, description, 
                 requirements, salary_range=None, job_type=None, 
                 posted_by=None, created_at=None, linkedin_url=None):
        self.id = job_id
        self.title = title
        self.company = company
        self.location = location
        self.description = description
        self.requirements = requirements
        self.salary_range = salary_range
        self.job_type = job_type
        self.posted_by = posted_by
        self.created_at = created_at or datetime.now()
        self.linkedin_url = linkedin_url

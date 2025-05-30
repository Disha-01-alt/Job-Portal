import psycopg2
import psycopg2.extras
import os
import logging
from contextlib import contextmanager

def get_db_connection():
    """Get database connection"""
    try:
        # Use DATABASE_URL directly for better compatibility
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            conn = psycopg2.connect(database_url)
        else:
            # Fallback to individual parameters
            conn = psycopg2.connect(
                host=os.environ.get('PGHOST'),
                database=os.environ.get('PGDATABASE'),
                user=os.environ.get('PGUSER'),
                password=os.environ.get('PGPASSWORD'),
                port=os.environ.get('PGPORT', 5432)
            )
        return conn
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        raise

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = None
    try:
        conn = get_db_connection()
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Database operation error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def init_db():
    """Initialize database tables"""
    with get_db() as conn:
        cur = conn.cursor()
        
        # Create users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL CHECK (role IN ('candidate', 'admin', 'company')),
                full_name VARCHAR(255),
                phone VARCHAR(20),
                linkedin VARCHAR(255),
                github VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_approved BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Create candidate_profiles table - WITH NEW COLUMNS
        cur.execute("""
            CREATE TABLE IF NOT EXISTS candidate_profiles (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                summary TEXT,                       -- Existing, can be repurposed for "Summary of skill and strength"
                cv_filename VARCHAR(255),
                id_card_filename VARCHAR(255),
                marksheet_filename VARCHAR(255),
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                admin_feedback TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- New fields for candidate profile enhancements
                ews_certificate_filename VARCHAR(255),
                college_name VARCHAR(255),          -- For Education
                degree VARCHAR(255),                -- For Education
                graduation_year INTEGER,            -- For Education
                core_interest_domains TEXT,         -- Checkbox options (e.g., comma-separated or JSON array)
                twelfth_school_type VARCHAR(50),    -- 'government', 'private', 'unknown'
                parental_annual_income VARCHAR(100), -- Store as string for flexibility (e.g., "Below 2 Lakhs", "2-5 Lakhs", "500000")

                -- New fields for admin tagging
                admin_tags TEXT,                    -- Comma-separated skill tags or JSON array
                is_certified BOOLEAN DEFAULT FALSE  -- Admin certified checkbox
            )
        """)
        
        
        # Create jobs table - WITH NEW COLUMN
        cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                company VARCHAR(255) NOT NULL,
                location VARCHAR(255),
                description TEXT,
                requirements TEXT,
                salary_range VARCHAR(100),
                job_type VARCHAR(100),              -- Existing, can be used for on-site/remote/hybrid
                posted_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                linkedin_url TEXT,

                -- New field for job tags
                job_tags TEXT                       -- Comma-separated tags or JSON array
            )
        """)
        
        
         # Create admin user if not exists (no changes here)
        from werkzeug.security import generate_password_hash
        admin_password_hash = generate_password_hash('admin123')
        cur.execute("""
            INSERT INTO users (email, password_hash, role, full_name, is_approved)
            SELECT 'dishasahu786forstudy@gmail.com', %s, 'admin', 'System Administrator', TRUE
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'dishasahu786forstudy@gmail.com')
        """, (admin_password_hash,))
        
        cur.execute("""
            UPDATE users SET password_hash = %s 
            WHERE email = 'dishasahu786forstudy@gmail.com' AND (password_hash IS NULL OR password_hash = '')
        """, (admin_password_hash,))
        
        conn.commit()
        logging.info("Database initialized successfully with new fields.")


# Database helper functions
def get_user_by_email(email):
    """Get user by email"""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
        if row:
            from models import User
            return User(
                user_id=row['id'],
                email=row['email'],
                password_hash=row['password_hash'],
                role=row['role'],
                full_name=row['full_name'],
                phone=row['phone'],
                linkedin=row['linkedin'],
                github=row['github'],
                created_at=row['created_at'],
                is_approved=row['is_approved']
            )
        return None

def get_user_by_id(user_id):
    """Get user by ID"""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        if row:
            from models import User
            return User(
                user_id=row['id'],
                email=row['email'],
                password_hash=row['password_hash'],
                role=row['role'],
                full_name=row['full_name'],
                phone=row['phone'],
                linkedin=row['linkedin'],
                github=row['github'],
                created_at=row['created_at'],
                is_approved=row['is_approved']
            )
        return None

def create_user(email, password, role, full_name=None, phone=None, linkedin=None, github=None):
    from models import User # Keep import here if not global
    # If password is for a Google user and is empty, generate a secure unusable hash
    # or ensure your DB column for password_hash allows NULL for OAuth users.
    # For simplicity, we'll assume User.create_password_hash('') is acceptable if password_hash is NOT NULL.
    password_hash = User.create_password_hash(password if password is not None else os.urandom(16).hex())


    # Determine is_approved status
    if role == 'company':
        is_approved_status = False
    elif role == 'pending_setup': # New temporary role
        is_approved_status = True # Allow login, but features gated by actual role later
    else: # candidate, admin
        is_approved_status = True
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (email, password_hash, role, full_name, phone, linkedin, github, is_approved)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (email, password_hash, role, full_name, phone, linkedin, github, is_approved_status))
        
        user_id = cur.fetchone()[0]
        
        # Create candidate profile only if final role is candidate, or for pending_setup if they choose candidate later
        # For now, let's not create candidate_profile for 'pending_setup' here.
        # It will be created when they complete registration and choose 'candidate'.
        # OR, create a basic one if it simplifies logic. Let's assume it's created later.
        
        conn.commit()
        return user_id

# jobportal/database.py

# ... (other imports and functions)

def get_candidate_details_by_id(user_id):
    """Get comprehensive candidate details by user ID, including user and profile info."""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT u.id, u.email, u.full_name, u.phone, u.linkedin, u.github, u.created_at,
                   u.is_approved,
                   cp.user_id as profile_user_id, cp.summary,
                   cp.cv_filename, cp.id_card_filename, cp.marksheet_filename,
                   cp.rating, cp.admin_feedback, cp.updated_at as profile_updated_at
            FROM users u
            LEFT JOIN candidate_profiles cp ON u.id = cp.user_id
            WHERE u.id = %s AND u.role = 'candidate'
        """, (user_id,))
        row = cur.fetchone()
        if row:
            # Convert row to a dictionary
            candidate_data = dict(row)
            # Ensure 'id' is the primary key for the user.
            # The template will use candidate.id, candidate.full_name, candidate.summary etc.
            return candidate_data
        return None

# ... (rest of the file)
def get_candidate_profile(user_id):
    """Get candidate profile"""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Ensure all new columns are selected
        cur.execute("""
            SELECT user_id, summary,
                   cv_filename, id_card_filename, marksheet_filename, 
                   rating, admin_feedback, updated_at,
                   ews_certificate_filename, college_name, degree, graduation_year,
                   core_interest_domains, twelfth_school_type, parental_annual_income,
                   admin_tags, is_certified
            FROM candidate_profiles WHERE user_id = %s
        """, (user_id,))
        row = cur.fetchone()
        if row:
            from models import CandidateProfile
            return CandidateProfile(
                user_id=row['user_id'],
                summary=row['summary'],
                cv_filename=row['cv_filename'],
                id_card_filename=row['id_card_filename'],
                marksheet_filename=row['marksheet_filename'],
                rating=row['rating'],
                admin_feedback=row['admin_feedback'],
                updated_at=row['updated_at'],
                # New fields
                ews_certificate_filename=row['ews_certificate_filename'],
                college_name=row['college_name'],
                degree=row['degree'],
                graduation_year=row['graduation_year'],
                core_interest_domains=row['core_interest_domains'],
                twelfth_school_type=row['twelfth_school_type'],
                parental_annual_income=row['parental_annual_income'],
                admin_tags=row['admin_tags'],
                is_certified=row['is_certified']
            )
        return None

def update_candidate_profile(user_id, **kwargs):
    """Update candidate profile"""
    with get_db() as conn:
        cur = conn.cursor()
        
        # Build dynamic update query
        set_clauses = []
        values = []
        
        for key, value in kwargs.items():
            if value is not None:
                set_clauses.append(f"{key} = %s")
                values.append(value)
        
        if set_clauses:
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(user_id)
            
            query = f"UPDATE candidate_profiles SET {', '.join(set_clauses)} WHERE user_id = %s"
            cur.execute(query, values)
            conn.commit()

def get_all_jobs(location_filter=None, work_model_filter=None, date_posted_filter=None, company_filter=None, job_function_filter=None): # Added filters
    """Get all jobs with optional filters"""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        query = """
            SELECT j.*, u.full_name as posted_by_name 
            FROM jobs j 
            LEFT JOIN users u ON j.posted_by = u.id 
            WHERE 1=1 
        """ # Start with WHERE 1=1 to easily append AND clauses
        params = []

        if location_filter and location_filter.lower() != "remote":
            query += " AND LOWER(j.location) LIKE LOWER(%s)"
            params.append(f"%{location_filter}%")
        elif location_filter and location_filter.lower() == "remote":
             # Assuming 'Remote' is stored in job_type or a dedicated work_model column
            query += " AND (LOWER(j.job_type) LIKE '%remote%' OR LOWER(j.location) LIKE '%remote%')"


        if work_model_filter: # e.g., 'on-site', 'remote', 'hybrid'
            # This assumes job_type stores this info. Adjust if you add a work_model column.
            query += " AND LOWER(j.job_type) = LOWER(%s)"
            params.append(work_model_filter)
        
        if date_posted_filter:
            if date_posted_filter == 'past_24_hours':
                query += " AND j.created_at >= NOW() - INTERVAL '24 hours'"
            elif date_posted_filter == 'past_week':
                query += " AND j.created_at >= NOW() - INTERVAL '7 days'"
            elif date_posted_filter == 'past_month':
                query += " AND j.created_at >= NOW() - INTERVAL '1 month'"
            # 'anytime' needs no date condition

        if company_filter:
            query += " AND LOWER(j.company) LIKE LOWER(%s)"
            params.append(f"%{company_filter}%")

        if job_function_filter: # Assuming job_tags stores job functions
            query += " AND LOWER(j.job_tags) LIKE LOWER(%s)"
            params.append(f"%{job_function_filter}%")

        query += " ORDER BY j.created_at DESC"
        
        cur.execute(query, tuple(params))
        jobs = []
        for row in cur.fetchall():
            from models import Job
            job = Job(
                job_id=row['id'],
                title=row['title'],
                company=row['company'],
                location=row['location'],
                description=row['description'],
                requirements=row['requirements'],
                salary_range=row['salary_range'],
                job_type=row['job_type'],
                posted_by=row['posted_by'],
                created_at=row['created_at'],
                linkedin_url=row['linkedin_url'],
                job_tags=row['job_tags'] # Added job_tags
            )
            job.posted_by_name = row['posted_by_name'] # Keep this if you use it
            jobs.append(job)
        return jobs


def create_job(title, company, location, description, requirements, 
               posted_by, salary_range=None, job_type=None, linkedin_url=None,
               job_tags=None): # Added job_tags
    """Create a new job"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO jobs (title, company, location, description, requirements, 
                            salary_range, job_type, posted_by, linkedin_url, job_tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (title, company, location, description, requirements, 
              salary_range, job_type, posted_by, linkedin_url, job_tags)) # Added job_tags
        
        result = cur.fetchone()
        job_id = result[0] if result else None
        conn.commit()
        return job_id

def get_all_candidates():
    """Get all candidates with their profiles"""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT u.id, u.email, u.full_name, u.phone, u.linkedin, u.github, u.created_at,
                   cp.summary,
                   cp.cv_filename, cp.id_card_filename, cp.marksheet_filename,
                   cp.rating, cp.admin_feedback,
                   -- New candidate profile fields
                   cp.ews_certificate_filename, cp.college_name, cp.degree, cp.graduation_year,
                   cp.core_interest_domains, cp.twelfth_school_type, cp.parental_annual_income,
                   -- New admin tagging fields
                   cp.admin_tags, cp.is_certified
            FROM users u
            LEFT JOIN candidate_profiles cp ON u.id = cp.user_id
            WHERE u.role = 'candidate'
            ORDER BY u.created_at DESC
        """)
        candidates = []
        for row in cur.fetchall():
            candidate = {
                'id': row['id'],
                'email': row['email'],
                'full_name': row['full_name'],
                'phone': row['phone'],
                'linkedin': row['linkedin'],
                'github': row['github'],
                'summary': row['summary'],
                'cv_filename': row['cv_filename'],
                'id_card_filename': row['id_card_filename'],
                'marksheet_filename': row['marksheet_filename'],
                'rating': row['rating'],
                'admin_feedback': row['admin_feedback'],
                'created_at': row['created_at'],
                # New fields
                'ews_certificate_filename': row['ews_certificate_filename'],
                'college_name': row['college_name'],
                'degree': row['degree'],
                'graduation_year': row['graduation_year'],
                'core_interest_domains': row['core_interest_domains'],
                'twelfth_school_type': row['twelfth_school_type'],
                'parental_annual_income': row['parental_annual_income'],
                'admin_tags': row['admin_tags'],
                'is_certified': row['is_certified']
            }
            candidates.append(candidate)
        return candidates
def update_candidate_rating_feedback(user_id, rating, feedback, admin_tags=None, is_certified=None): # Added new params
    """Update candidate rating, feedback, admin tags, and certification status"""
    with get_db() as conn:
        cur = conn.cursor()
        
        # Build the SET part of the query dynamically
        set_clauses = []
        params = []

        if rating is not None:
            set_clauses.append("rating = %s")
            params.append(rating)
        
        if feedback is not None: # Allow empty string for feedback
            set_clauses.append("admin_feedback = %s")
            params.append(feedback)

        if admin_tags is not None: # admin_tags can be a comma-separated string or None
            set_clauses.append("admin_tags = %s")
            params.append(admin_tags)

        if is_certified is not None: # is_certified is a boolean
            set_clauses.append("is_certified = %s")
            params.append(is_certified)
        
        if not set_clauses: # Nothing to update
            return

        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        
        query = f"""
            UPDATE candidate_profiles 
            SET {', '.join(set_clauses)}
            WHERE user_id = %s
        """
        params.append(user_id)
        
        cur.execute(query, tuple(params))
        conn.commit()
def search_candidates(skills=None, education=None, min_rating=None, experience=None, core_interest_domains_filter=None, admin_tags_filter=None): # Added new filters
    """Search candidates with filters"""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        query = """
            SELECT u.id, u.email, u.full_name, u.phone, u.linkedin, u.github, u.created_at,
                   cp.summary, 
                   cp.cv_filename, cp.id_card_filename, cp.marksheet_filename, -- Added for company detail view potentially
                   cp.rating, cp.admin_feedback,
                   -- New fields relevant for company search/display
                   cp.college_name, cp.degree, cp.graduation_year,
                   cp.core_interest_domains, cp.admin_tags, cp.is_certified
            FROM users u
            LEFT JOIN candidate_profiles cp ON u.id = cp.user_id
            WHERE u.role = 'candidate' AND u.is_approved = TRUE
        """
        params = []
        
        if skills: # General skills search
            query += " AND LOWER(cp.skills) LIKE LOWER(%s)"
            params.append(f"%{skills}%")
        
        if education: # General education search (can be refined if education becomes structured)
            query += " AND (LOWER(cp.education) LIKE LOWER(%s) OR LOWER(cp.college_name) LIKE LOWER(%s) OR LOWER(cp.degree) LIKE LOWER(%s))"
            params.extend([f"%{education}%", f"%{education}%", f"%{education}%"])
        
        if min_rating:
            query += " AND cp.rating >= %s"
            params.append(min_rating)
        
        if experience: # General experience search
            query += " AND LOWER(cp.experience) LIKE LOWER(%s)"
            params.append(f"%{experience}%")

        if core_interest_domains_filter: # Filter by specific core interests
            # Assuming core_interest_domains_filter is a list of strings
            # This part needs adjustment based on how you store core_interest_domains (comma-separated or JSON)
            # For comma-separated:
            domain_conditions = []
            for domain in core_interest_domains_filter:
                domain_conditions.append("LOWER(cp.core_interest_domains) LIKE LOWER(%s)")
                params.append(f"%{domain}%")
            if domain_conditions:
                query += " AND (" + " OR ".join(domain_conditions) + ")"
        
        if admin_tags_filter: # Filter by admin-applied tags
            # Similar to core_interest_domains_filter
            tag_conditions = []
            for tag in admin_tags_filter:
                tag_conditions.append("LOWER(cp.admin_tags) LIKE LOWER(%s)")
                params.append(f"%{tag}%")
            if tag_conditions:
                query += " AND (" + " OR ".join(tag_conditions) + ")"

        query += " ORDER BY cp.rating DESC NULLS LAST, u.created_at DESC"
        
        cur.execute(query, params)
        candidates = []
        for row in cur.fetchall():
            candidate = dict(row) # Convert DictRow to dict for easier template access
            candidates.append(candidate)
        return candidates

def get_pending_companies():
    """Get all companies waiting for approval"""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT id, email, full_name, phone, linkedin, github, created_at
            FROM users 
            WHERE role = 'company' AND is_approved = false
            ORDER BY created_at DESC
        """)
        companies = []
        for row in cur.fetchall():
            company = {
                'id': row['id'],
                'email': row['email'],
                'full_name': row['full_name'],
                'phone': row['phone'],
                'linkedin': row['linkedin'],
                'github': row['github'],
                'created_at': row['created_at']
            }
            companies.append(company)
        return companies

def approve_company(company_id):
    """Approve a company account"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE users SET is_approved = true 
            WHERE id = %s AND role = 'company'
        """, (company_id,))
        conn.commit()
        return cur.rowcount > 0

def delete_job(job_id):
    """Delete a job"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
        conn.commit()

def get_job_by_id(job_id):
    """Get job by ID"""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Select all columns including the new job_tags
        cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
        row = cur.fetchone()
        if row:
            from models import Job
            return Job(
                job_id=row['id'],
                title=row['title'],
                company=row['company'],
                location=row['location'],
                description=row['description'],
                requirements=row['requirements'],
                salary_range=row['salary_range'],
                job_type=row['job_type'],
                posted_by=row['posted_by'],
                created_at=row['created_at'],
                linkedin_url=row['linkedin_url'],
                job_tags=row['job_tags'] # Added job_tags
            )
        return None
def update_job(job_id, **kwargs):
    """Update job"""
    with get_db() as conn:
        cur = conn.cursor()
        
        # Build dynamic update query
        set_clauses = []
        values = []
        
        for key, value in kwargs.items():
            if value is not None:
                set_clauses.append(f"{key} = %s")
                values.append(value)
        
        if set_clauses:
            values.append(job_id)
            query = f"UPDATE jobs SET {', '.join(set_clauses)} WHERE id = %s"
            cur.execute(query, values)
            conn.commit()

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
        
        # Create candidate_profiles table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS candidate_profiles (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                summary TEXT,
                education TEXT,
                experience TEXT,
                skills TEXT,
                cv_filename VARCHAR(255),
                id_card_filename VARCHAR(255),
                marksheet_filename VARCHAR(255),
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                admin_feedback TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create jobs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                company VARCHAR(255) NOT NULL,
                location VARCHAR(255),
                description TEXT,
                requirements TEXT,
                salary_range VARCHAR(100),
                job_type VARCHAR(50),
                posted_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                linkedin_url TEXT
            )
        """)
        
        # Create admin user if not exists
        from werkzeug.security import generate_password_hash
        admin_password_hash = generate_password_hash('admin123')
        cur.execute("""
            INSERT INTO users (email, password_hash, role, full_name, is_approved)
            SELECT 'admin@jobportal.com', %s, 'admin', 'System Administrator', TRUE
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'admin@jobportal.com')
        """, (admin_password_hash,))
        
        # Update existing admin user with correct hash if needed
        cur.execute("""
            UPDATE users SET password_hash = %s 
            WHERE email = 'admin@jobportal.com' AND (password_hash IS NULL OR password_hash = '')
        """, (admin_password_hash,))
        
        conn.commit()
        logging.info("Database initialized successfully")

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
    """Create a new user"""
    from models import User
    password_hash = User.create_password_hash(password)
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (email, password_hash, role, full_name, phone, linkedin, github, is_approved)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (email, password_hash, role, full_name, phone, linkedin, github, role != 'company'))
        
        user_id = cur.fetchone()[0]
        
        # Create candidate profile if role is candidate
        if role == 'candidate':
            cur.execute("""
                INSERT INTO candidate_profiles (user_id)
                VALUES (%s)
            """, (user_id,))
        
        conn.commit()
        return user_id

def get_candidate_profile(user_id):
    """Get candidate profile"""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM candidate_profiles WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        if row:
            from models import CandidateProfile
            return CandidateProfile(
                user_id=row['user_id'],
                summary=row['summary'],
                education=row['education'],
                experience=row['experience'],
                skills=row['skills'],
                cv_filename=row['cv_filename'],
                id_card_filename=row['id_card_filename'],
                marksheet_filename=row['marksheet_filename'],
                rating=row['rating'],
                admin_feedback=row['admin_feedback']
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

def get_all_jobs():
    """Get all jobs"""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT j.*, u.full_name as posted_by_name 
            FROM jobs j 
            LEFT JOIN users u ON j.posted_by = u.id 
            ORDER BY j.created_at DESC
        """)
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
                linkedin_url=row['linkedin_url']
            )
            job.posted_by_name = row['posted_by_name']
            jobs.append(job)
        return jobs

def create_job(title, company, location, description, requirements, 
               posted_by, salary_range=None, job_type=None, linkedin_url=None):
    """Create a new job"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO jobs (title, company, location, description, requirements, 
                            salary_range, job_type, posted_by, linkedin_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (title, company, location, description, requirements, 
              salary_range, job_type, posted_by, linkedin_url))
        
        result = cur.fetchone()
        job_id = result[0] if result else None
        conn.commit()
        return job_id

def get_all_candidates():
    """Get all candidates with their profiles"""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT u.*, cp.summary, cp.education, cp.experience, cp.skills, 
                   cp.cv_filename, cp.id_card_filename, cp.marksheet_filename,
                   cp.rating, cp.admin_feedback
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
                'education': row['education'],
                'experience': row['experience'],
                'skills': row['skills'],
                'cv_filename': row['cv_filename'],
                'id_card_filename': row['id_card_filename'],
                'marksheet_filename': row['marksheet_filename'],
                'rating': row['rating'],
                'admin_feedback': row['admin_feedback'],
                'created_at': row['created_at']
            }
            candidates.append(candidate)
        return candidates

def update_candidate_rating_feedback(user_id, rating, feedback):
    """Update candidate rating and feedback"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE candidate_profiles 
            SET rating = %s, admin_feedback = %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (rating, feedback, user_id))
        conn.commit()

def search_candidates(skills=None, education=None, min_rating=None, experience=None):
    """Search candidates with filters"""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        query = """
            SELECT u.*, cp.summary, cp.education, cp.experience, cp.skills, 
                   cp.cv_filename, cp.rating, cp.admin_feedback
            FROM users u
            LEFT JOIN candidate_profiles cp ON u.id = cp.user_id
            WHERE u.role = 'candidate' AND u.is_approved = TRUE
        """
        params = []
        
        if skills:
            query += " AND LOWER(cp.skills) LIKE LOWER(%s)"
            params.append(f"%{skills}%")
        
        if education:
            query += " AND LOWER(cp.education) LIKE LOWER(%s)"
            params.append(f"%{education}%")
        
        if min_rating:
            query += " AND cp.rating >= %s"
            params.append(min_rating)
        
        if experience:
            query += " AND LOWER(cp.experience) LIKE LOWER(%s)"
            params.append(f"%{experience}%")
        
        query += " ORDER BY cp.rating DESC NULLS LAST, u.created_at DESC"
        
        cur.execute(query, params)
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
                'education': row['education'],
                'experience': row['experience'],
                'skills': row['skills'],
                'cv_filename': row['cv_filename'],
                'rating': row['rating'],
                'admin_feedback': row['admin_feedback']
            }
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
                linkedin_url=row['linkedin_url']
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

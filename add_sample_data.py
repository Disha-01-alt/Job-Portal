#!/usr/bin/env python3
"""
One-time script to populate the job portal database with sample data.
Run this once to add sample jobs and candidates to your database.
"""

import psycopg2
from datetime import datetime

def add_sample_data():
    try:
        # Connect to database
        conn = psycopg2.connect("postgresql://postgres:Admin@localhost:5432/job_data")
        cur = conn.cursor()
        
        print("Adding sample jobs...")
        
        # Adapted job data to match your table columns
        jobs_data = [
            (
                'Senior Software Engineer',          # job_title
                'Tech Innovation Inc',               # company_name
                'San Francisco, CA',                 # location
                "Bachelor's degree in Computer Science, 5+ years experience with Python/JavaScript, Experience with React and Node.js",  # required_skills
                '2024-05-01',                       # publication_date (as text to match your schema)
                'HR Team',                         # author
                'https://techinnovation.example/jobs/123',  # url
                '3+ years',                       # experience_required
                '$120,000 - $150,000',             # salary_range
                'Not Applied',                     # application_status (default but explicit here)
                '{}',                             # additional_info as empty JSON string
                datetime.now()                    # created_at
            ),
            (
                'Data Scientist',
                'DataCorp Analytics',
                'New York, NY',
                "Master's degree in Data Science or related field, Proficiency in Python, R, SQL, Experience with machine learning frameworks",
                '2024-05-02',
                'HR Team',
                'https://datacorp.example/jobs/456',
                '2+ years',
                '$100,000 - $130,000',
                'Not Applied',
                '{}',
                datetime.now()
            ),
            (
                'Frontend Developer',
                'Creative Digital Agency',
                'Austin, TX',
                "Bachelor's degree in Web Development or related field, Expert knowledge of HTML, CSS, JavaScript, Experience with Vue.js or React",
                '2024-05-03',
                'HR Team',
                'https://creativeagency.example/jobs/789',
                '2+ years',
                '$80,000 - $110,000',
                'Not Applied',
                '{}',
                datetime.now()
            ),
            (
                'Product Manager',
                'StartupXYZ',
                'Seattle, WA',
                "MBA or equivalent experience, 3+ years product management experience, Strong analytical and communication skills",
                '2024-05-04',
                'HR Team',
                'https://startupxyz.example/jobs/101',
                '3+ years',
                '$110,000 - $140,000',
                'Not Applied',
                '{}',
                datetime.now()
            ),
            (
                'DevOps Engineer',
                'CloudTech Solutions',
                'Remote',
                "Bachelor's degree in Engineering, Experience with AWS/Azure, Docker, Kubernetes, Jenkins or similar CI/CD tools",
                '2024-05-05',
                'HR Team',
                'https://cloudtech.example/jobs/202',
                '3+ years',
                '$95,000 - $125,000',
                'Not Applied',
                '{}',
                datetime.now()
            )
        ]
        
        for job in jobs_data:
            cur.execute("""
                INSERT INTO jobs (
                    job_title, company, location, required_skills, publication_date, author, url,
                    experience_required, salary_range, application_status, additional_info, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
            """, job)
        
        print("Adding sample candidates...")
        
        # Sample candidates - adjust columns as needed if your users table differs
        candidates_data = [
            ('sarah.johnson@email.com', '', 'candidate', 'Sarah Johnson', '+1-555-0123', 
             'https://linkedin.com/in/sarahjohnson', 'https://github.com/sarahjohnson', True),
            ('mike.chen@email.com', '', 'candidate', 'Mike Chen', '+1-555-0124',
             'https://linkedin.com/in/mikechen', 'https://github.com/mikechen', True),
            ('emily.davis@email.com', '', 'candidate', 'Emily Davis', '+1-555-0125',
             'https://linkedin.com/in/emilydavis', '', True),
            ('alex.wilson@email.com', '', 'candidate', 'Alex Wilson', '+1-555-0126',
             'https://linkedin.com/in/alexwilson', 'https://github.com/alexwilson', True)
        ]
        
        for candidate in candidates_data:
            cur.execute("""
                INSERT INTO users (
                    email, password_hash, role, full_name, phone, linkedin, github, created_at, is_approved
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            """, candidate)
        
        # Commit changes
        conn.commit()
        cur.close()
        conn.close()
        
        print("✅ Sample data added successfully!")
        print("Your database now has:")
        print("- 5 sample job postings")
        print("- 4 sample candidate profiles")
        print("- Ready for demo and testing!")
        
    except Exception as e:
        print(f"❌ Error adding sample data: {e}")
        print("Make sure your DATABASE_URL environment variable is set correctly.")

if __name__ == "__main__":
    add_sample_data()


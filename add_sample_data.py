#!/usr/bin/env python3
"""
One-time script to populate the job portal database with sample data.
Run this once to add sample jobs and candidates to your database.
"""

import os
import psycopg2
from datetime import datetime

def add_sample_data():
    try:
        # Connect to database using environment variable
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cur = conn.cursor()
        
        print("Adding sample jobs...")
        
        # Add sample jobs
        jobs_data = [
            ('Senior Software Engineer', 'Tech Innovation Inc', 'San Francisco, CA', 
             'We are looking for a senior software engineer to join our dynamic team. You will be responsible for developing scalable web applications and mentoring junior developers.',
             'Bachelor\'s degree in Computer Science, 5+ years experience with Python/JavaScript, Experience with React and Node.js',
             '$120,000 - $150,000', 'Full-time', 3),
            
            ('Data Scientist', 'DataCorp Analytics', 'New York, NY',
             'Join our data science team to analyze large datasets and build machine learning models that drive business decisions.',
             'Master\'s degree in Data Science or related field, Proficiency in Python, R, SQL, Experience with machine learning frameworks',
             '$100,000 - $130,000', 'Full-time', 3),
            
            ('Frontend Developer', 'Creative Digital Agency', 'Austin, TX',
             'We need a creative frontend developer to build stunning user interfaces and ensure excellent user experience across our web applications.',
             'Bachelor\'s degree in Web Development or related field, Expert knowledge of HTML, CSS, JavaScript, Experience with Vue.js or React',
             '$80,000 - $110,000', 'Full-time', 3),
            
            ('Product Manager', 'StartupXYZ', 'Seattle, WA',
             'Lead product development from conception to launch. Work closely with engineering and design teams to build products users love.',
             'MBA or equivalent experience, 3+ years product management experience, Strong analytical and communication skills',
             '$110,000 - $140,000', 'Full-time', 3),
            
            ('DevOps Engineer', 'CloudTech Solutions', 'Remote',
             'Help us build and maintain our cloud infrastructure. You will work with containerization, CI/CD pipelines, and monitoring systems.',
             'Bachelor\'s degree in Engineering, Experience with AWS/Azure, Docker, Kubernetes, Jenkins or similar CI/CD tools',
             '$95,000 - $125,000', 'Remote', 3)
        ]
        
        for job in jobs_data:
            cur.execute("""
                INSERT INTO jobs (title, company, location, description, requirements, salary_range, job_type, posted_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, job)
        
        print("Adding sample candidates...")
        
        # Add sample candidates
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
                INSERT INTO users (email, password_hash, role, full_name, phone, linkedin, github, created_at, is_approved)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            """, candidate)
        
        # Commit all changes
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

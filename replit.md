# Job Portal - Flask Application

## Overview

This is a Flask-based web portal that connects job candidates (students), company representatives, and administrators. The platform facilitates job searching, candidate management, and application processing through role-based access control.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask with Blueprint-based modular structure
- **Authentication**: Flask-Login for session management with role-based access control
- **Database**: PostgreSQL with raw SQL queries (no ORM)
- **File Handling**: Local file uploads with secure filename handling
- **AI Integration**: Google Gemini API for LinkedIn job extraction
- **Deployment**: Gunicorn WSGI server with autoscale deployment

### Frontend Architecture
- **Templates**: Jinja2 templating engine
- **Styling**: Bootstrap with custom CSS
- **JavaScript**: Vanilla JS with Bootstrap components
- **Responsive Design**: Mobile-first approach with Bootstrap grid

## Key Components

### 1. User Roles and Access Control
- **Candidates**: Students who create profiles and browse jobs
- **Companies**: HR representatives who search candidates (requires admin approval)
- **Admins**: Platform administrators who manage jobs and review candidates

### 2. Authentication System
- Email/password-based authentication
- Role-based route protection using decorators
- Company accounts require admin approval before access

### 3. File Upload System
- Secure file handling with type validation
- Separate upload directories for different document types
- Support for CV (PDF/DOCX), ID cards, and marksheets

### 4. Job Management
- AI-powered job extraction from LinkedIn URLs using Gemini API
- Manual job creation and editing capabilities
- Job search and browsing functionality

### 5. Candidate Management
- Profile creation with education, experience, and skills
- Document upload and management
- Admin rating and feedback system
- Company search and filtering capabilities

## Data Flow

### User Registration and Authentication
1. User registers with role selection (candidate/company)
2. Company accounts await admin approval
3. Authenticated users access role-specific dashboards
4. Session management via Flask-Login

### Job Posting Process
1. Admin provides LinkedIn job URL
2. System extracts job details using Gemini API
3. Job information parsed and stored in PostgreSQL
4. Jobs become available for candidate browsing

### Candidate Profile Management
1. Candidates complete profile information
2. File uploads processed and stored securely
3. Admins review and rate candidate profiles
4. Companies search and view approved candidates

## External Dependencies

### Required APIs
- **Google Gemini API**: Job information extraction from LinkedIn
- **PostgreSQL**: Primary database for all application data

### Python Dependencies
- Flask ecosystem (Flask, Flask-Login, Flask-SQLAlchemy)
- Database: psycopg2-binary for PostgreSQL connectivity
- AI: google-generativeai for Gemini integration
- Web scraping: requests, beautifulsoup4 for LinkedIn parsing
- Security: werkzeug for password hashing and file handling
- Deployment: gunicorn for production server

### Frontend Dependencies
- Bootstrap CSS framework via CDN
- Font Awesome icons via CDN
- Vanilla JavaScript for interactivity

## Deployment Strategy

### Replit Configuration
- Python 3.11 runtime environment
- Nix packages: openssl, postgresql
- Autoscale deployment target for production
- Gunicorn server binding to 0.0.0.0:5000

### Environment Variables Required
- `PGHOST`: PostgreSQL host
- `PGDATABASE`: Database name
- `PGUSER`: Database username
- `PGPASSWORD`: Database password
- `PGPORT`: Database port (default: 5432)
- `GOOGLE_API_KEY`: Gemini API key for job extraction
- `SESSION_SECRET`: Flask session secret key

### File Storage
- Local file system storage in `uploads/` directory
- Organized subdirectories: `cvs/`, `id_cards/`, `marksheets/`
- 16MB maximum file size limit
- Secure filename handling to prevent path traversal

### Database Schema
The application uses PostgreSQL with raw SQL queries. Key tables include:
- `users`: User authentication and basic information
- `candidate_profiles`: Extended candidate information and documents
- `jobs`: Job postings and requirements
- Additional tables for ratings, feedback, and applications

The system is designed for easy deployment on Replit with minimal configuration required, while maintaining security and scalability for a job portal application.
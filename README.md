# Job Portal - Render Deployment

## Quick Deploy to Render

### 1. Database Setup
- Create a PostgreSQL database on Render
- Copy the database connection string

### 2. Environment Variables
Set these in your Render web service:
- `DATABASE_URL`: Your PostgreSQL connection string
- `GOOGLE_API_KEY`: Your Google Gemini API key  
- `SESSION_SECRET`: Any random string for Flask sessions

### 3. Deploy
- Connect your GitHub repo to Render
- Use these settings:
  - **Build Command**: `pip install -r pyproject.toml`
  - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --workers 1 main:app`

### 4. Admin Access
- Email: admin@jobportal.com
- Password: admin123

## Features
- Multi-role authentication (candidates, companies, admins)
- AI-powered job extraction from LinkedIn URLs
- Document management (CV, ID cards, marksheets)
- Candidate rating and feedback system
- Company search and filtering

## Tech Stack
- Flask + PostgreSQL
- Google Gemini AI
- Bootstrap UI
- psycopg2 for database connectivity
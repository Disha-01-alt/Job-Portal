import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import re
import logging
import json

def extract_job_from_linkedin(job_url):
    """
    Extract job information from any job posting URL using Gemini AI
    Works with LinkedIn and other job posting websites
    """
    try:
        # Configure Gemini API
        api_key = os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            raise Exception("Google API key not found")
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Get page content with improved scraping
        content = get_page_content(job_url)
        
        if "requires authentication" in content:
            return {
                'title': 'Authentication Required',
                'company': 'Login wall detected',
                'location': 'Not accessible',
                'description': 'This content requires authentication to access',
                'requirements': 'Unable to extract due to authentication',
                'salary_range': 'Not specified',
                'job_type': 'Not specified'
            }
        
        # Generate response using enhanced prompt
        gemini_response = generate_gemini_response(content, job_url)
        
        # Parse the response into structured data
        parsed_data = parse_gemini_response(gemini_response)
        
        return {
            'title': parsed_data.get('job_title', 'Not specified'),
            'company': parsed_data.get('company_name', 'Not specified'), 
            'location': parsed_data.get('location', 'Not specified'),
            'description': f"Skills: {parsed_data.get('required_skills', 'Not specified')}",
            'requirements': parsed_data.get('required_skills', 'Not specified'),
            'salary_range': parsed_data.get('salary_range', 'Not specified'),
            'job_type': parsed_data.get('additional_info', {}).get('job_type', 'Not specified')
        }
        
    except Exception as e:
        logging.error(f"Error extracting job from URL: {e}")
        return {
            'title': 'Extraction Failed',
            'company': 'Error occurred',
            'location': 'Not available',
            'description': f'Failed to extract job information: {str(e)}',
            'requirements': 'Check original URL for details',
            'salary_range': 'Not specified',
            'job_type': 'Not specified'
        }

def get_page_content(url):
    """Enhanced page content extraction that works with various job sites"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        print(f"Fetching URL: {url}")
        response = requests.get(url, headers=headers, timeout=20)
        print(f"Response status code: {response.status_code}")
        
        if "authwall" in response.url or "signup" in response.url:
            print("Authentication wall detected")
            return "Website requires authentication to access this content. Unable to extract job data."
            
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        # First, try to find the post content with LinkedIn-specific selectors
        post_text_elements = soup.select(
            '.feed-shared-update-v2__description, '
            '.feed-shared-text, '
            '.feed-shared-update-v2__commentary, '
            '.share-update-card__update-text, '
            '.feed-shared-text__text-view'
        )
        
        if post_text_elements:
            post_content = ' '.join([element.get_text(strip=True) for element in post_text_elements])
            
            # Ensure post_content is a string
            if not isinstance(post_content, str):
                post_content = str(post_content)
                
            # Clean up the text
            post_content = re.sub(r'\s+', ' ', post_content)
            
            # Preserve bullet points
            post_content = post_content.replace('• ', '\n• ')
            post_content = post_content.replace('•', '\n•')
            
            # Remove common LinkedIn text patterns at the beginning
            post_content = re.sub(r'^.*?(Skip to main content)', '', post_content)
            
            # Remove comment section indicators
            post_content = re.sub(r'\d+ Comments.*?(Share|Copy|LinkedIn|Facebook|Twitter)', '', post_content)
            
            return post_content.strip()
        
        # Try generic job site selectors
        job_content_selectors = [
            '.job-description, .job-details, .posting-content',
            'article, .post-content, .content',
            'main, .main-content, .primary-content'
        ]
        
        for selector in job_content_selectors:
            elements = soup.select(selector)
            if elements:
                content = ' '.join([elem.get_text(strip=True) for elem in elements])
                if content and len(content) > 100:  # Ensure we have substantial content
                    return clean_content(content)
        
        # If we couldn't extract post content with specific selectors, 
        # try to get just the main content without comments
        main_content = soup.select_one('main, .core-rail, .scaffold-layout__main')
        if main_content:
            # Remove comments section and social actions before extracting text
            for element in main_content.select('.comments-comments-list, .social-details-social-counts, ' +
                                               '.feed-shared-social-actions, .comments-comment-item, ' +
                                               '.feed-shared-comment-list, .social-details-social-activity'):
                element.extract()
            
            # Get just the text of what remains
            content = main_content.get_text(strip=True, separator=' ')
            
            # Ensure content is a string
            if not isinstance(content, str):
                content = str(content)
                
            return clean_content(content)
            
        # Last resort - try to get just the text without comments
        body = soup.body
        if body:
            # Remove all comment sections, social actions, etc.
            for unwanted in body.select('.comments-comments-list, .comments-container, .social-footer-stats-container, ' +
                                        '.feed-shared-social-actions, .comments-comment-item, .feed-shared-comment-list'):
                unwanted.extract()
                
            content = body.get_text(strip=True, separator=' ')
            
            # Ensure content is a string
            if not isinstance(content, str):
                content = str(content)
                
            return clean_content(content)
            
        return "Could not extract content from the job posting page."
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error fetching URL: {e}")

def clean_content(content):
    """Clean and format extracted content"""
    if not isinstance(content, str):
        content = str(content)
        
    # Remove excessive whitespace
    content = re.sub(r'\s+', ' ', content)
    
    # Preserve bullet points
    content = content.replace('• ', '\n• ')
    content = content.replace('•', '\n•')
    
    # Remove common UI text
    content = re.sub(r'Agree & Join LinkedIn.*?Cookie Policy \. Skip to main content', '', content)
    content = re.sub(r'\d+ Comments Like Comment Share Copy LinkedIn Facebook Twitter', '', content)
    content = re.sub(r'Report this post', '', content)
    
    # Clean up spaces and preserve bullet points
    content = re.sub(r'\s+', ' ', content)
    content = content.replace('• ', '\n• ')
    content = content.replace('•', '\n•')
    
    return content.strip()

def generate_gemini_response(content, url):
    """Generate structured response using Gemini AI"""
    prompt = f"""
You are a web page data extractor specializing in job posts. Analyze the content of the following job posting page and extract specific information into a structured format.

Web Page URL: {url}

Web Page Content:
---
{content}
---

Specifically look for job-related information in the content. Extract as much detail as possible, even if the format is conversational rather than a traditional job posting.

If the content contains bullet points with skills, technical requirements, or research areas, make sure to capture those in the Required Skills section.

Please extract the information according to the following constraints and format it as a table. If you cannot find a specific piece of information, mark it as "not found".

| Column Name      | Description                                          | Extraction Guidance                                                                 |
| ---------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Job Title        | The title of the job.                                | Look for position names or roles mentioned. If multiple jobs, list all of them.      |
| Company Name     | The name of the company posting the job.             | Try to extract from the post author or content. For LinkedIn, check for mentions.    |
| Required Skills  | A list of skills needed for the job.                 | Look for "skills", "requirements", "qualifications", or bullet points in the content.|
| Publication Date | The date the job posting or article was published.   | Try to extract date information. Format as YYYY-MM-DD if possible.                   |
| Author           | The author of the article.                           | Usually the person who posted the content on LinkedIn.                               |
| Experience       | Years of experience required for the role.           | Look for mentions of education or experience requirements, including PhD references. |
| Salary          | Compensation or salary information.                  | Look for any mentions of salary, pay range, or compensation.                         |
| Location        | Where the job is located.                           | Look for city, state, country or remote work information.                           |
| Job Type        | Full-time, part-time, contract, etc.                | Extract the employment type if mentioned.                                            |
| Education       | Required education level or degree.                  | Look for educational requirements, especially PhD or specialized degrees.           |
| Research Focus  | The research focus or specialty areas.              | Look for mentions of specialized research areas or domains.                          |
| Application Status | The current application status.                      | Default to "Not Applied" unless specified otherwise.                                 |

Present the information only as a standard markdown table with a header row and one data row. Don't include any other text or explanation.
"""
    
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise Exception(f"Gemini API Error: {e}")

def parse_gemini_response(response_text):
    """Parse the markdown table response from Gemini into a dictionary"""
    # Default values for main fields
    result = {
        "job_title": "not found",
        "company_name": "not found", 
        "required_skills": "not found",
        "publication_date": "not found",
        "author": "not found",
        "experience_required": "not found",
        "salary_range": "not found",
        "location": "not found",
        "application_status": "Not Applied",
        "additional_info": {}
    }
    
    # Extract job title
    job_title_patterns = [
        r'\|\s*Job Title\s*\|\s*([^|]+)\s*\|',
        r'\|\s*Title\s*\|\s*([^|]+)\s*\|'
    ]
    for pattern in job_title_patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            result["job_title"] = match.group(1).strip()
            break
    
    # Extract company name
    company_patterns = [
        r'\|\s*Company Name\s*\|\s*([^|]+)\s*\|',
        r'\|\s*Company\s*\|\s*([^|]+)\s*\|'
    ]
    for pattern in company_patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            result["company_name"] = match.group(1).strip()
            break
    
    # Extract required skills
    skills_patterns = [
        r'\|\s*Required Skills\s*\|\s*([^|]+)\s*\|',
        r'\|\s*Skills\s*\|\s*([^|]+)\s*\|'
    ]
    for pattern in skills_patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            result["required_skills"] = match.group(1).strip()
            break
    
    # Extract publication date
    date_patterns = [
        r'\|\s*Publication Date\s*\|\s*([^|]+)\s*\|',
        r'\|\s*Date\s*\|\s*([^|]+)\s*\|'
    ]
    for pattern in date_patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            result["publication_date"] = match.group(1).strip()
            break
    
    # Extract author
    author_patterns = [
        r'\|\s*Author\s*\|\s*([^|]+)\s*\|'
    ]
    for pattern in author_patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            result["author"] = match.group(1).strip()
            break
    
    # Extract experience required
    experience_patterns = [
        r'\|\s*(?:Experience|Experience Required|Work Experience)\s*\|\s*([^|]+)\s*\|',
        r'Experience:?\s*([^\n]+)'
    ]
    for pattern in experience_patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            result["experience_required"] = match.group(1).strip()
            break
    
    # Extract salary range
    salary_patterns = [
        r'\|\s*(?:Salary|Compensation|Salary Range|Pay)\s*\|\s*([^|]+)\s*\|',
        r'Salary:?\s*([^\n]+)',
        r'Compensation:?\s*([^\n]+)'
    ]
    for pattern in salary_patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            result["salary_range"] = match.group(1).strip()
            break
            
    # Extract location
    location_patterns = [
        r'\|\s*(?:Location|Job Location|Work Location)\s*\|\s*([^|]+)\s*\|',
        r'Location:?\s*([^\n]+)'
    ]
    for pattern in location_patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            result["location"] = match.group(1).strip()
            break
    
    # Extract job type into additional_info
    job_type_patterns = [
        r'\|\s*(?:Job Type|Employment Type)\s*\|\s*([^|]+)\s*\|',
        r'Job Type:?\s*([^\n]+)'
    ]
    for pattern in job_type_patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            job_type = match.group(1).strip()
            if job_type.lower() != "not found":
                result["additional_info"]["job_type"] = job_type
            break
    
    return result
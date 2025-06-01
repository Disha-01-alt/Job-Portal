import os
import requests
from bs4 import BeautifulSoup
import openai # Using OpenAI
import re
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- OpenAI API Configuration ---
# API Key will be fetched from the environment variable 'OPENAI_API_KEY'
_OPENAI_CLIENT = None

def _initialize_openai_client():
    """Initializes the OpenAI client if not already done. Reads API key from environment."""
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is None:
        # Fetch API key from environment variable
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise Exception(
                "OpenAI API key not found in environment variables (OPENAI_API_KEY). "
                "Please set it in your environment (e.g., on Render)."
            )
        try:
            _OPENAI_CLIENT = openai.OpenAI(api_key=api_key)
            # Test connectivity (optional, but good for immediate feedback)
            _OPENAI_CLIENT.models.list() 
            logging.info("OpenAI client initialized successfully using environment variable.")
        except openai.AuthenticationError as e:
            logging.error(f"OpenAI API Key from environment is invalid: {e}")
            raise Exception(f"OpenAI API Key from environment is invalid. Original error: {e}")
        except Exception as e:
            logging.error(f"Failed to initialize OpenAI client using environment key: {e}")
            raise Exception(f"Failed to initialize OpenAI client using environment key. Original error: {e}")
    return _OPENAI_CLIENT

def extract_job_from_linkedin(job_url): # This function name is from your old script
    """
    Extract job information from any job posting URL using OpenAI API
    (API key from environment) and formats output for site integration.
    """
    try:
        client = _initialize_openai_client() # Initializes client using env var
        content = get_page_content(job_url)

        default_return_on_issue = {
            'title': 'Authentication Required or Content Issue',
            'company': 'Access or Extraction Problem',
            'location': 'Not accessible',
            'description': 'This content requires authentication or could not be extracted.',
            'requirements': 'Unable to extract',
            'salary_range': 'Not specified',
            'job_type': 'Not specified',
            'publication_date': 'Not specified',
            'author': 'Not specified',
            'experience_required': 'Not specified',
            'education': 'Not specified',
            'research_focus': 'Not specified',
            'application_status': 'Not Applied',
            'raw_llm_response': 'No LLM call due to content issue.',
            'url': job_url
        }

        if "requires authentication" in content.lower() or "could not extract substantial content" in content.lower():
            logging.warning(f"Content issue for URL: {job_url} - {content}")
            if "requires authentication" in content.lower():
                default_return_on_issue['description'] = 'This content requires authentication to access.'
            elif "could not extract substantial content" in content.lower():
                default_return_on_issue['description'] = 'Could not extract substantial content from the job posting page.'
            return default_return_on_issue

        llm_response = generate_openai_response(client, content, job_url)
        parsed_data = parse_llm_response_table(llm_response)

        return {
            'title': parsed_data.get('job_title', 'Not specified'),
            'company': parsed_data.get('company_name', 'Not specified'),
            'location': parsed_data.get('location', 'Not specified'),
            'description': f"Skills: {parsed_data.get('required_skills', 'Not specified')}",
            'requirements': parsed_data.get('required_skills', 'Not specified'),
            'salary_range': parsed_data.get('salary_range', 'Not specified'),
            'job_type': parsed_data.get('additional_info', {}).get('job_type', 'Not specified'),
            'publication_date': parsed_data.get('publication_date', 'Not specified'),
            'author': parsed_data.get('author', 'Not specified'),
            'experience_required': parsed_data.get('experience_required', 'Not specified'),
            'education': parsed_data.get('additional_info', {}).get('education', 'Not specified'),
            'research_focus': parsed_data.get('additional_info', {}).get('research_focus', 'Not specified'),
            'application_status': parsed_data.get('application_status', 'Not Applied'),
            'raw_llm_response': llm_response,
            'url': job_url
        }

    except Exception as e:
        logging.error(f"Error extracting job from URL {job_url}: {e}", exc_info=True)
        return {
            'title': 'Extraction Failed',
            'company': 'Error occurred',
            'location': 'Not available',
            'description': f'Failed to extract job information: {str(e)}',
            'requirements': 'Check original URL for details',
            'salary_range': 'Not specified',
            'job_type': 'Not specified',
            'publication_date': 'Not specified',
            'author': 'Not specified',
            'experience_required': 'Not specified',
            'education': 'Not specified',
            'research_focus': 'Not specified',
            'application_status': 'Not Applied',
            'raw_llm_response': f'Error: {str(e)}',
            'url': job_url
        }

# --- get_page_content, clean_content, generate_openai_response, parse_llm_response_table ---
# These functions remain identical to the previous version (OpenAI API, Site Format Output)
# as they correctly implement the scraping, cleaning, OpenAI prompting, and parsing.
# For brevity, I will not repeat them here, but assume they are the same as in
# the script from my previous response ending with:
# print(f"Details: {e}")
# --- --- --- --- --- --- --- --- --- --- --- --- ---

def get_page_content(url):
    # This function is taken from the robust OpenAI version and remains unchanged
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
        logging.info(f"Fetching URL: {url}")
        response = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        logging.info(f"Response status code for {url}: {response.status_code}, Final URL: {response.url}")

        if "authwall" in response.url or "login" in response.url or "signup" in response.url or "checkpoint" in response.url:
            logging.warning(f"Authentication wall detected for {url} based on redirect URL: {response.url}")
            return "Website requires authentication to access this content. Unable to extract job data."

        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        job_desc_selectors = [
            '.jobs-description__content', '.jobs-description', '.job-details__description',
            '.jobsearch-JobComponent-description', '#job-details', '#job_description', '.jobdescp',
            '.job-details-content', '.jobad-description-container',
            'div[class*="jobDescription"]', 'section[class*="job-description"]',
            'article[class*="job-description"]'
        ]
        if 'linkedin.com/jobs/view' in url or 'linkedin.com/posts/' in url :
             job_desc_selectors.extend([
                '.feed-shared-update-v2__description', '.feed-shared-text', 
                '.feed-shared-update-v2__commentary', '.share-update-card__update-text', 
                '.feed-shared-text__text-view', '.show-more-less-html__markup'
            ])
        for selector in job_desc_selectors:
            elements = soup.select(selector)
            if elements:
                elements.sort(key=lambda el: len(el.get_text(strip=True)), reverse=True)
                content = elements[0].get_text(separator=' ', strip=True)
                if content and len(content) > 100:
                    logging.info(f"Extracted content using specific job selector: {selector}")
                    return clean_content(content)
        logging.info(f"No specific job description selector matched well for {url}. Trying generic selectors.")
        generic_content_selectors = [
            'article', 'main', '.job-description, .job-details, .posting-content, .job-content, .adp-job-description',
            'div[class*="job"], section[class*="description"]', '.main-content, .primary-content, .content'
        ]
        for selector in generic_content_selectors:
            elements = soup.select(selector)
            if elements:
                elements.sort(key=lambda el: len(el.get_text(strip=True)), reverse=True)
                for el in elements:
                    for unwanted_selector in ['.similar-jobs', '.related-jobs', 'footer', 'header', '.job-footer', '.company-info', 'nav', 'aside', '.sidebar', '#sidebar', '.comments-comments-list', '.social-footer-stats-container', '.feed-shared-social-actions', '.related-articles', '.site-footer', '.site-header', '.modal']:
                        for unwanted_el in el.select(unwanted_selector): unwanted_el.extract()
                    for unwanted_tag in el.find_all(['script', 'style']): unwanted_tag.extract()
                    content = el.get_text(separator=' ', strip=True)
                    if content and len(content) > 200:
                        logging.info(f"Extracted content using generic selector: {selector}")
                        return clean_content(content)
        logging.info(f"Generic selectors failed for {url}. Falling back to full body text cleaning.")
        body = soup.body
        if body:
            for unwanted_tag_name in ['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'iframe', 'noscript']:
                for unwanted_tag in body.find_all(unwanted_tag_name): unwanted_tag.extract()
            common_noisy_selectors = [
                '.comments-comments-list', '.comments-container', '.social-footer-stats-container', 
                '.feed-shared-social-actions', '.comments-comment-item', '.feed-shared-comment-list', 
                '.related-articles', '.sidebar', '#sidebar', '.site-footer', '.site-header', 
                '[role="navigation"]', '[role="search"]', '.modal', '.popup', '.cookie-banner',
                'div[aria-modal="true"]'
            ]
            for noisy_selector in common_noisy_selectors:
                for item in body.select(noisy_selector): item.extract()
            content = body.get_text(separator=' ', strip=True)
            if content.strip() and len(content.strip()) > 50:
                logging.info("Extracted content using fallback (cleaned body text)")
                return clean_content(content)
        logging.warning(f"Could not extract substantial content from the job posting page: {url}")
        return "Could not extract substantial content from the job posting page."
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching URL {url}: {e}")
        raise Exception(f"Error fetching URL: {e}")
    except Exception as e:
        logging.error(f"Error processing page content for {url}: {e}")
        raise Exception(f"Error processing page content: {e}")

def clean_content(content):
    # This function is taken from the robust OpenAI version and remains unchanged
    if not isinstance(content, str): content = str(content)
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = BeautifulSoup(content, "html.parser").get_text(separator=' ')
    content = re.sub(r'\s*\n\s*', '\n', content)
    content = re.sub(r'[ \t]+', ' ', content)
    content = content.replace(' \n', '\n').replace('\n ', '\n')
    common_ui_phrases = [
        r'Skip to main content', r'Agree & Join LinkedIn', r'Cookie Policy',
        r'\b(?:Share|Like|Comment|Report)\b', r'Apply now', r'Save job', 
        r'View all jobs at .*?', r'More jobs from .*?', r'Similar jobs', r'Back to job results', 
        r'Sign in', r'Create account', r'Learn more', r'Privacy Policy', r'Terms of Service',
        r'(?:LinkedIn)?\s*(?:Facebook)?\s*(?:Twitter)?', r'Show more', r'Show less', r'Read more', r'See more',
        r'©\s*\d{4}\s*.*?(?:LLC|Inc\.?|Ltd\.?|Corporation)?(?:.\s*All rights reserved\.?)?',
    ]
    for phrase_pattern in common_ui_phrases:
        content = re.sub(phrase_pattern, '', content, flags=re.IGNORECASE | re.UNICODE)
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = content.strip()
    return content

def generate_openai_response(client, content, url):
    """Generate structured response using OpenAI API, asking for fields needed by the site."""
    prompt_instructions = f"""
You are a web page data extractor specializing in job posts. Analyze the content of the following job posting page and extract specific information.

Web Page URL: {url}

Web Page Content (may be truncated or contain irrelevant text, focus on job details):
---
{content[:15000]} 
---

Your task is to extract the information and format it ONLY as a standard markdown table with a header row and one data row. 
The header row must use exactly these column names in this order:
Job Title | Company Name | Required Skills | Publication Date | Author | Experience | Salary | Location | Job Type | Education | Research Focus | Application Status

Example of the EXACT output format (your entire response must be only this table):
| Job Title        | Company Name     | Required Skills  | Publication Date | Author    | Experience       | Salary    | Location      | Job Type  | Education        | Research Focus   | Application Status |
|------------------|------------------|------------------|------------------|-----------|------------------|-----------|---------------|-----------|------------------|------------------|--------------------|
| Extracted Title  | Extracted Co.    | Skill1, Skill2   | YYYY-MM-DD       | John Doe  | 3+ years         | $X - $Y   | City, Country | Full-time | Bachelor's       | NLP              | Not Applied        |

If you cannot find a specific piece of information, use "not found" in its cell.
Do not include any other text, explanations, or apologies.

Detailed guidance for each field:
- Job Title: The title of the job. Look for position names or roles mentioned. If multiple, list primary one.
- Company Name: The name of the company posting the job. Try to extract from the post author or content.
- Required Skills: A comma-separated list of skills needed. Look for "skills", "requirements", "qualifications", or bullet points. Summarize.
- Publication Date: Date posted (YYYY-MM-DD if possible). Try to extract date information. If relative (e.g., "2 weeks ago"), state that.
- Author: Person/recruiter posting (if clearly identifiable). Usually the person who posted content on LinkedIn. If not a person or company, use "not found".
- Experience: Years/level of experience required. E.g., "3+ years", "Senior level", "Entry level", "PhD required".
- Salary: Compensation or salary information. Look for any mentions of salary, pay range, or compensation.
- Location: Where the job is located (City, State, Country). Look for city, state, country or remote work information.
- Job Type: Full-time, part-time, contract, intern, etc. Extract the employment type if mentioned.
- Education: Required education level or degree. E.g., "Bachelor's degree", "PhD in CS".
- Research Focus: Specific research areas/domains (if applicable). For research roles, list focus areas like "NLP", "Computer Vision".
- Application Status: The current application status. Default to "Not Applied" unless the content clearly indicates otherwise (e.g., "Applications closed", "Applied").
"""
    try:
        logging.info(f"Sending request to OpenAI for URL: {url} (Content length: {len(content)})")
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert data extractor. Your task is to analyze web page content and return information structured as a markdown table, following the user's specific instructions precisely. Output ONLY the markdown table."},
                {"role": "user", "content": prompt_instructions}
            ],
            temperature=0.05 
        )
        response_text = completion.choices[0].message.content
        if response_text.startswith("```markdown\n"): response_text = response_text[len("```markdown\n"):]
        if response_text.endswith("\n```"): response_text = response_text[:-len("\n```")]
        if response_text.startswith("```"): response_text = response_text[3:]
        if response_text.endswith("```"): response_text = response_text[:-3]
        logging.info(f"Received OpenAI response for URL: {url}")
        return response_text.strip()
    except openai.APIConnectionError as e: logging.error(f"OpenAI API Connection Error: {e}"); raise
    except openai.RateLimitError as e: logging.error(f"OpenAI API Rate Limit Error: {e}"); raise
    except openai.APIError as e: logging.error(f"OpenAI API Error: {e}"); raise
    except Exception as e: logging.error(f"Unexpected error during OpenAI call: {e}"); raise

def parse_llm_response_table(response_text):
    """Parse the markdown table response from an LLM (OpenAI) into a dictionary"""
    result = {
        "job_title": "not found", "company_name": "not found", "required_skills": "not found",
        "publication_date": "not found", "author": "not found", "experience_required": "not found",
        "salary_range": "not found", "location": "not found", "application_status": "Not Applied",
        "additional_info": {"job_type": "not found", "education": "not found", "research_focus": "not found"}
    }
    lines = [line for line in response_text.strip().split('\n') if line.strip() and not line.strip().startswith('---')]
    
    field_to_key_map = {
        "job title": "job_title", "company name": "company_name", "required skills": "required_skills",
        "publication date": "publication_date", "author": "author", 
        "experience": "experience_required",
        "salary": "salary_range", "location": "location", "job type": "job_type",
        "education": "education", "research focus": "research_focus", 
        "application status": "application_status"
    }
    additional_info_keys = ["job_type", "education", "research_focus"]
    direct_result_keys = ["application_status"]

    parsed_successfully = False

    if len(lines) > 2 and \
       ("column name" in lines[0].lower() or "field" in lines[0].lower()) and \
       ("description" in lines[0].lower() or "guidance" in lines[0].lower() or "value" in lines[0].lower()):
        logging.info("Attempting to parse LLM response as 3-column descriptive table format.")
        temp_parsed_count = 0
        for line_num in range(1, len(lines)):
            if lines[line_num].strip().startswith('|--') or not lines[line_num].strip().startswith('|'): continue
            parts = [p.strip() for p in lines[line_num].strip('|').split('|')]
            if len(parts) >= 2:
                key_from_llm = parts[0].lower().strip()
                value_from_llm = ""
                if len(parts) >= 3 and parts[2]: value_from_llm = parts[2]
                elif len(parts) == 2 and parts[1]: value_from_llm = parts[1]

                if key_from_llm in field_to_key_map and value_from_llm:
                    target_key = field_to_key_map[key_from_llm]
                    actual_value = value_from_llm if value_from_llm.lower() != "not found" else "not found"
                    if actual_value != "not found": temp_parsed_count +=1
                    if target_key in additional_info_keys: result["additional_info"][target_key] = actual_value
                    elif target_key in direct_result_keys: result[target_key] = actual_value
                    else: result[target_key] = actual_value
        if temp_parsed_count > 0:
            logging.info(f"Successfully parsed {temp_parsed_count} fields from 3-column format.")
            parsed_successfully = True

    if not parsed_successfully and len(lines) >= 2:
        logging.info("Attempting to parse LLM response as standard 2-row (Header | Values) table format.")
        header_idx, data_idx = -1, -1
        for i, line in enumerate(lines):
            if line.strip().startswith('|') and not line.strip().startswith('|--'):
                if header_idx == -1: header_idx = i
                elif data_idx == -1 and header_idx != -1 : data_idx = i; break
        
        if header_idx != -1 and data_idx != -1 and data_idx > header_idx :
            headers_raw = [h.strip().lower() for h in lines[header_idx].strip('|').split('|')]
            values_raw = [v.strip() for v in lines[data_idx].strip('|').split('|')]

            if len(headers_raw) == len(values_raw) and len(headers_raw) > 0:
                temp_parsed_count = 0
                for i, header_text in enumerate(headers_raw):
                    if header_text in field_to_key_map:
                        target_key = field_to_key_map[header_text]
                        actual_value = values_raw[i] if values_raw[i].lower() != "not found" else "not found"
                        if actual_value != "not found": temp_parsed_count +=1
                        
                        if target_key in additional_info_keys: result["additional_info"][target_key] = actual_value
                        elif target_key in direct_result_keys: result[target_key] = actual_value
                        else: result[target_key] = actual_value
                if temp_parsed_count > 0:
                    logging.info(f"Successfully parsed {temp_parsed_count} fields from 2-row format.")
                    parsed_successfully = True
            else:
                logging.warning(f"Header/Value count mismatch in 2-row parse. Headers: {len(headers_raw)} ({headers_raw}), Values: {len(values_raw)} ({values_raw})")
        else:
            logging.warning("Could not identify clear header and data rows for 2-row parse.")

    if not parsed_successfully:
        logging.warning(f"Could not parse LLM response as a known table format. Raw response (first 500 chars): {response_text[:500]}")

    for key_template in result.keys():
        if key_template == "additional_info":
            for add_key in result["additional_info"].keys():
                if result["additional_info"].get(add_key) is None or result["additional_info"].get(add_key) == "":
                    result["additional_info"][add_key] = "not found"
        elif result.get(key_template) is None or result.get(key_template) == "":
            result[key_template] = "not found"
            if key_template == "application_status" and result[key_template] == "not found":
                result[key_template] = "Not Applied"
            
    return result

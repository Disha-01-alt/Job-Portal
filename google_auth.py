# jobportal/google_auth.py
import json
import os
import requests
from flask import Blueprint, redirect, request, url_for, session, flash
from flask_login import login_user, logout_user, current_user, login_required # Ensure all are imported
from oauthlib.oauth2 import WebApplicationClient
from database import get_user_by_email, create_user, get_user_by_id # create_user and get_user_by_id are crucial
from models import User
import logging

# --- Environment Variable Handling for OAuthLib ---
# For local development with HTTP, OAUTHLIB_INSECURE_TRANSPORT must be '1'.
# For production on Render (HTTPS), this should NOT be '1'.
if os.environ.get("FLASK_ENV") == "development" or not os.environ.get("RENDER_EXTERNAL_URL"): # Heuristic for local
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    logging.warning("OAUTHLIB_INSECURE_TRANSPORT enabled. Ensure HTTPS and this is disabled in production.")

# --- Google OAuth Configuration ---
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# --- Blueprint Definition ---
google_auth = Blueprint("google_auth", __name__)

# --- OAuth Client Initialization ---
if not GOOGLE_CLIENT_ID:
    logging.critical("CRITICAL: GOOGLE_OAUTH_CLIENT_ID is NOT SET in environment variables. Google OAuth will fail.")
    client = None # Application will likely fail or behave unexpectedly
else:
    client = WebApplicationClient(GOOGLE_CLIENT_ID)

# --- Helper Functions ---
def get_google_provider_cfg():
    """Fetches Google's OpenID configuration."""
    try:
        response = requests.get(GOOGLE_DISCOVERY_URL, timeout=10)
        response.raise_for_status() # Will raise an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch Google's OpenID configuration: {e}")
        return None

def get_redirect_url():
    """
    Determines the correct OAuth2 redirect URI based on the environment.
    For Render, it's crucial that this matches the "Authorized redirect URIs"
    in your Google Cloud Console.
    """
    # Preferred: Explicitly set redirect URI in environment (best for production)
    env_redirect_uri = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI")
    if env_redirect_uri:
        logging.debug(f"Using GOOGLE_OAUTH_REDIRECT_URI from environment: {env_redirect_uri}")
        return env_redirect_uri

    # Fallback for Render if RENDER_EXTERNAL_URL is set
    render_external_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_external_url:
        # Ensure it's HTTPS for production
        proto = "https" # Render services are typically HTTPS
        domain = render_external_url.replace('https://', '').replace('http://', '')
        redirect_uri = f"{proto}://{domain}/google_login/callback"
        logging.info(f"Using Render auto-detected redirect URI: {redirect_uri}")
        return redirect_uri
    
    # Fallback for local development (HTTP)
    # Note: If your local dev runs on a different port, adjust accordingly.
    local_redirect_uri = "http://127.0.0.1:5000/google_login/callback"
    logging.info(f"Using local development redirect URI: {local_redirect_uri}")
    return local_redirect_uri

# --- Routes ---
@google_auth.route("/google_login")
def login():
    if not client:
        flash("Google OAuth is not configured on the server. Please contact support.", "error")
        return redirect(url_for('index'))

    google_provider_cfg = get_google_provider_cfg()
    if not google_provider_cfg or "authorization_endpoint" not in google_provider_cfg:
        flash("Could not connect to Google for authentication (config error). Please try again later.", "error")
        return redirect(url_for("index"))
        
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    redirect_uri = get_redirect_url() # This is critical
    
    logging.debug(f"Google OAuth: Initiating login. Redirect URI will be: {redirect_uri}")

    try:
        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=redirect_uri, # Must exactly match one in Google Console
            scope=["openid", "email", "profile"],
        )
    except Exception as e:
        logging.error(f"Error preparing Google request URI: {e}. Check client_id and redirect_uri config.")
        flash("Error initiating Google Sign-In. Please ensure OAuth is correctly configured.", "error")
        return redirect(url_for('index'))
        
    return redirect(request_uri)

@google_auth.route("/google_login/callback")
def callback():
    if not client:
        flash("Google OAuth is not configured on the server (callback). Please contact support.", "error")
        return redirect(url_for('index'))

    code = request.args.get("code")
    if not code:
        error_reason = request.args.get("error_description") or request.args.get("error")
        logging.error(f"Google OAuth callback error: Missing 'code'. Reason from Google: {error_reason}")
        flash(f"Authentication failed with Google. Reason: {error_reason or 'Authorization code not provided.'}", "error")
        return redirect(url_for("google_auth.login")) 

    google_provider_cfg = get_google_provider_cfg()
    if not google_provider_cfg or "token_endpoint" not in google_provider_cfg:
        flash("Could not verify authentication with Google (server config error). Please try again later.", "error")
        return redirect(url_for("index"))

    token_endpoint = google_provider_cfg["token_endpoint"]
    redirect_uri_for_token = get_redirect_url() # Must be same as used in the initial auth request

    try:
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url, 
            redirect_url=redirect_uri_for_token, 
            code=code
        )
        logging.debug(f"Requesting token. URL: {token_url}, Redirect URL for token: {redirect_uri_for_token}")

        token_response = requests.post(
            token_url, headers=headers, data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET), timeout=10
        )
        token_response.raise_for_status()
        client.parse_request_body_response(json.dumps(token_response.json()))

        userinfo_endpoint = google_provider_cfg.get("userinfo_endpoint")
        if not userinfo_endpoint: 
            raise ValueError("Userinfo endpoint not found in Google OAuth configuration.")
        
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body, timeout=10)
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()

    except requests.exceptions.HTTPError as e:
        logging.error(f"Google OAuth HTTPError during token/userinfo exchange: {e.response.status_code} - {e.response.text}")
        flash(f"Authentication with Google failed (HTTP {e.response.status_code}). Please ensure your OAuth Redirect URI is correctly set in Google Cloud Console and matches server configuration. Error: {e.response.reason}", "error")
        return redirect(url_for("google_auth.login"))
    except requests.exceptions.RequestException as e:
        logging.error(f"Google OAuth network error during token/userinfo exchange: {e}")
        flash("A network error occurred while authenticating with Google. Please check your connection and try again.", "error")
        return redirect(url_for("google_auth.login"))
    except Exception as e: 
        logging.exception(f"Unexpected error processing Google OAuth callback: {e}")
        flash("An unexpected error occurred during Google sign-in. Please try again or contact support.", "error")
        return redirect(url_for("google_auth.login"))

    if not userinfo.get("email_verified"):
        flash("Your Google email is not verified. Please verify your email with Google and try again.", "warning")
        return redirect(url_for("google_auth.login"))

    unique_id = userinfo.get("sub")
    users_email = userinfo.get("email","").lower() 
    users_name_from_google = userinfo.get("given_name") or (userinfo.get("name", "New User").split(" ")[0])
    picture = userinfo.get("picture")

    if not unique_id or not users_email:
        logging.error(f"Google OAuth response missing essential user info (sub or email). Userinfo: {userinfo}")
        flash("Could not retrieve essential profile information from Google. Authentication failed.", "error")
        return redirect(url_for("google_auth.login"))

    existing_user_model = get_user_by_email(users_email)
    logging.info(f"Google login for {users_email}. User found in DB: {existing_user_model is not None}")

    if existing_user_model:
        login_user(existing_user_model)
        session['google_id'] = unique_id 
        session['google_name'] = existing_user_model.full_name or users_name_from_google
        session['google_picture'] = picture
        session.pop('pending_registration', None)
        session.pop('needs_registration_completion', None) 

        flash(f'Welcome back, {existing_user_model.full_name or existing_user_model.email}!', 'success')
        
        if existing_user_model.role == 'admin': return redirect(url_for('admin_routes.dashboard'))
        if existing_user_model.role == 'company':
            return redirect(url_for('company_routes.dashboard')) if existing_user_model.is_approved else redirect(url_for('index')) # Or pending page
        if existing_user_model.role == 'candidate': return redirect(url_for('candidate_routes.dashboard'))
        if existing_user_model.role == 'pending_setup': # Existing user still in pending_setup state
            session['needs_registration_completion'] = True
            flash('Welcome back! Please complete your registration to access all features.', 'info')
            return redirect(url_for('candidate_routes.jobs')) # Send to jobs page
        
        logging.warning(f"Existing user {users_email} has an unexpected role: {existing_user_model.role}. Redirecting to index.")
        return redirect(url_for('index')) 
    else: # New user
        try:
            logging.info(f"New user from Google: {users_email}. Creating basic 'pending_setup' user entry.")
            temp_role = "pending_setup" 
            # Your create_user function should handle password='' (e.g., by creating an unusable hash or allowing NULL)
            # and set is_approved=True for 'pending_setup' role.
            user_id = create_user(
                email=users_email, 
                password='', # Password not set via Google
                role=temp_role, 
                full_name=users_name_from_google
            )
            
            newly_created_user_model = get_user_by_id(user_id)
            if not newly_created_user_model:
                logging.critical(f"CRITICAL: Failed to fetch newly created user (ID: {user_id}) for {users_email} immediately after creation.")
                flash("Error setting up your initial account. Please try signing in again.", "error")
                return redirect(url_for('google_auth.login'))

            login_user(newly_created_user_model) 
            
            session['google_id'] = unique_id
            session['google_name'] = users_name_from_google 
            session['google_picture'] = picture
            session['needs_registration_completion'] = True # Flag for base.html and protected routes
            session.pop('pending_registration', None) # Clean up older flag if it existed

            flash(f'Welcome, {users_name_from_google}! Please complete your registration to use all features.', 'info')
            return redirect(url_for('candidate_routes.jobs')) # <<-- REDIRECT NEW AUTHENTICATED USER TO JOBS PAGE
        
        except Exception as e:
            logging.exception(f"Error creating initial 'pending_setup' user for {users_email} from Google login:")
            flash("An error occurred while setting up your account. Please try signing in again or contact support.", "error")
            return redirect(url_for('google_auth.login'))

@google_auth.route("/logout")
@login_required 
def logout():
    user_email_for_log = current_user.email if current_user.is_authenticated else "Unknown user"
    logout_user() 
    
    keys_to_pop = ['google_id', 'google_email', 'google_name', 'google_picture', 
                   'pending_registration', 'needs_registration_completion', '_flashes'] 
    for key in keys_to_pop:
        session.pop(key, None)
    
    flash('You have been logged out successfully.', 'info')
    logging.info(f"User {user_email_for_log} logged out.")
    return redirect(url_for('index'))

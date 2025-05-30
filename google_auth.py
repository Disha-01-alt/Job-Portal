# jobportal/google_auth.py
import json
import os
import requests
from flask import Blueprint, redirect, request, url_for, session, flash
from flask_login import login_user, logout_user, current_user,login_required # Added current_user for logout
from oauthlib.oauth2 import WebApplicationClient
from database import get_user_by_email, create_user # Assuming create_user is needed if registration completion creates user
from models import User
import logging

# --- Environment Variable Handling ---
# For local development with HTTP, OAUTHLIB_INSECURE_TRANSPORT must be set.
# For production on Render (HTTPS), this should NOT be '1'.
# Render automatically provides HTTPS, so this line is mainly for local http testing.
if os.environ.get("FLASK_ENV") == "development" or not os.environ.get("RENDER"):
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    logging.warning("OAUTHLIB_INSECURE_TRANSPORT enabled for development. Ensure HTTPS in production.")

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

google_auth = Blueprint("google_auth", __name__)

if not GOOGLE_CLIENT_ID:
    logging.critical("GOOGLE_OAUTH_CLIENT_ID is NOT SET. Google OAuth will fail.")
    # You might want to raise an error here or have the app refuse to start
    # For now, we'll let it proceed but client will be None.
    client = None
else:
    client = WebApplicationClient(GOOGLE_CLIENT_ID)

# Helper to fetch Google's OpenID configuration
def get_google_provider_cfg():
    try:
        response = requests.get(GOOGLE_DISCOVERY_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch Google's OpenID configuration: {e}")
        return None

# Your existing get_redirect_url function, with minor logging improvement
def get_redirect_url():
    """Get redirect URI depending on environment."""
    # Prefer RENDER_EXTERNAL_URL if available for production on Render
    render_external_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_external_url:
        # Ensure it's HTTPS for production
        redirect_uri = f"https://{render_external_url.replace('https://', '').replace('http://', '')}/google_login/callback"
        logging.info(f"Using Render redirect URI: {redirect_uri}")
        return redirect_uri

    # Fallback for your "Production_domain" variable or localhost
    production_domain_env = os.environ.get("Production_domain") # Renamed for clarity
    if production_domain_env:
        # Ensure it's HTTPS if it's a real production domain
        redirect_uri = f"https://{production_domain_env}/google_login/callback"
        logging.info(f"ID is saying (using Production_domain): {redirect_uri}")
        return redirect_uri
    
    # Default for local development
    local_redirect_uri = "http://127.0.0.1:5000/google_login/callback"
    logging.info(f"Using local redirect URI: {local_redirect_uri}")
    return local_redirect_uri


@google_auth.route("/google_login")
def login():
    if not client:
        flash("Google OAuth is not configured correctly. Please contact support.", "error")
        return redirect(url_for('index'))

    google_provider_cfg = get_google_provider_cfg()
    if not google_provider_cfg or "authorization_endpoint" not in google_provider_cfg:
        flash("Could not connect to Google for authentication. Please try again later.", "error")
        return redirect(url_for("index"))
        
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    redirect_uri = get_redirect_url()
    
    # Ensure the generated redirect_uri is exactly what's in your Google Cloud Console
    logging.debug(f"Google OAuth: Preparing login request with redirect_uri: {redirect_uri}")

    try:
        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=redirect_uri,
            scope=["openid", "email", "profile"], # Standard scopes
        )
    except Exception as e:
        logging.error(f"Error preparing Google request URI: {e}. Check client_id and redirect_uri.")
        flash("Error initiating Google Sign-In. Please try again.", "error")
        return redirect(url_for('index'))
        
    return redirect(request_uri)


@google_auth.route("/google_login/callback")
def callback():
    if not client:
        flash("Google OAuth is not configured correctly (callback). Please contact support.", "error")
        return redirect(url_for('index'))

    code = request.args.get("code")
    if not code:
        error_reason = request.args.get("error")
        logging.error(f"Google OAuth callback error: Missing 'code'. Reason from Google: {error_reason}")
        flash(f"Authentication failed. Google did not return an authorization code. Reason: {error_reason or 'Unknown'}", "error")
        return redirect(url_for("google_auth.login")) # Send back to login

    google_provider_cfg = get_google_provider_cfg()
    if not google_provider_cfg or "token_endpoint" not in google_provider_cfg:
        flash("Could not verify authentication with Google (config error). Please try again later.", "error")
        return redirect(url_for("index"))

    token_endpoint = google_provider_cfg["token_endpoint"]
    redirect_uri = get_redirect_url() # Must be the same as used in the login request

    try:
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url, # Full callback URL from browser
            redirect_url=redirect_uri,
            code=code
        )
        logging.debug(f"Requesting token from: {token_url} with redirect_url: {redirect_uri}")

        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET), # Client credentials for token request
            timeout=10
        )
        token_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        client.parse_request_body_response(json.dumps(token_response.json()))

        userinfo_endpoint = google_provider_cfg.get("userinfo_endpoint")
        if not userinfo_endpoint:
            logging.error("Userinfo endpoint not found in Google provider config.")
            flash("Could not fetch user details from Google.", "error")
            return redirect(url_for("index"))

        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body, timeout=10)
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()

    except requests.exceptions.HTTPError as e:
        logging.error(f"Google OAuth HTTPError during token/userinfo exchange: {e.response.text}")
        flash(f"Authentication with Google failed: {e.response.reason}. Please try again.", "error")
        return redirect(url_for("google_auth.login"))
    except requests.exceptions.RequestException as e:
        logging.error(f"Google OAuth network error during token/userinfo exchange: {e}")
        flash("A network error occurred while authenticating with Google. Please check your connection and try again.", "error")
        return redirect(url_for("google_auth.login"))
    except Exception as e: # Catch other potential errors during parsing or OAuth flow
        logging.exception(f"Error processing Google OAuth callback: {e}") # Use .exception for full traceback
        flash("An unexpected error occurred during Google sign-in. Please try again.", "error")
        return redirect(url_for("google_auth.login"))

    if not userinfo.get("email_verified"):
        flash("Your Google email is not verified. Please verify your email with Google and try again.", "warning")
        return redirect(url_for("google_auth.login"))

    unique_id = userinfo.get("sub")
    users_email = userinfo.get("email","").lower() # Normalize to lowercase
    # Try to get 'given_name', fall back to splitting 'name', then to a default
    users_name = userinfo.get("given_name") or (userinfo.get("name", "User").split(" ")[0])
    picture = userinfo.get("picture")

    if not unique_id or not users_email:
        logging.error(f"Google OAuth response missing essential user info (sub or email). Userinfo: {userinfo}")
        flash("Could not retrieve essential profile information from Google. Authentication failed.", "error")
        return redirect(url_for("google_auth.login"))

    existing_user = get_user_by_email(users_email) # Returns User object or None
    logging.info(f"Google login callback for {users_email}. Existing user in DB: {existing_user is not None}")

    if existing_user:
        # User exists, log them in
        # The User object from get_user_by_email should be complete for login_user
        login_user(existing_user)
        
        session['google_id'] = unique_id # Update session with potentially new Google ID if it changed (unlikely)
        session['google_name'] = existing_user.full_name or users_name # Prefer name from DB
        session['google_picture'] = picture
        session.pop('pending_registration', None) # Clear if it was somehow set

        flash(f'Welcome back, {existing_user.full_name or existing_user.email}!', 'success')
        
        if existing_user.role == 'admin':
            return redirect(url_for('admin_routes.dashboard'))
        elif existing_user.role == 'company':
            if not existing_user.is_approved:
                flash('Your company account is pending admin approval. Please contact support if this persists.', 'warning')
                return redirect(url_for('index')) 
            return redirect(url_for('company_routes.dashboard'))
        elif existing_user.role == 'candidate':
            return redirect(url_for('candidate_routes.dashboard'))
        else:
            logging.warning(f"User {users_email} with existing account has unknown role: {existing_user.role}")
            return redirect(url_for('index')) # Fallback
    else:
        # New user, store info in session and redirect to complete registration
        logging.info(f"New user from Google: {users_email}. Redirecting to complete registration.")
        session['google_id'] = unique_id
        session['google_email'] = users_email
        session['google_name'] = users_name # This name will be pre-filled on the registration form
        session['google_picture'] = picture
        session['pending_registration'] = True 
        
        return redirect(url_for('auth_routes.complete_registration'))

@google_auth.route("/logout")
@login_required # Good practice: user should be logged in to log out
def logout():
    user_email_for_log = current_user.email if current_user.is_authenticated else "Unknown user"
    logout_user() # Clears user from session and Flask-Login
    
    # Clear specific session keys related to Google auth and registration
    keys_to_pop = ['google_id', 'google_email', 'google_name', 'google_picture', 'pending_registration', '_flashes']
    for key in keys_to_pop:
        session.pop(key, None)
    
    flash('You have been logged out successfully.', 'info')
    logging.info(f"User {user_email_for_log} logged out.")
    return redirect(url_for('index'))

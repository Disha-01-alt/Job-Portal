# jobportal/google_auth.py
import json
import os
import requests
from flask import Blueprint, redirect, request, url_for, session, flash
from flask_login import login_user, logout_user, current_user, login_required
from oauthlib.oauth2 import WebApplicationClient
from database import get_user_by_email, create_user, get_user_by_id # Ensure get_user_by_id is available
from models import User
import logging

# ... (Environment variable handling, GOOGLE constants, client initialization, get_google_provider_cfg, get_redirect_url as before) ...
# Ensure all these helper functions and constants are correctly set up from previous responses.

@google_auth.route("/google_login")
def login():
    # ... (login function as previously corrected) ...
    if not client:
        flash("Google OAuth is not configured correctly. Please contact support.", "error")
        return redirect(url_for('index'))
    google_provider_cfg = get_google_provider_cfg()
    if not google_provider_cfg or "authorization_endpoint" not in google_provider_cfg:
        flash("Could not connect to Google for authentication. Please try again later.", "error")
        return redirect(url_for("index"))
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    redirect_uri = get_redirect_url()
    logging.debug(f"Google OAuth: Preparing login request with redirect_uri: {redirect_uri}")
    try:
        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=redirect_uri,
            scope=["openid", "email", "profile"],
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
    # ... (error handling for missing code, provider_cfg, token_endpoint as before) ...
    if not code:
        error_reason = request.args.get("error")
        logging.error(f"Google OAuth callback error: Missing 'code'. Reason from Google: {error_reason}")
        flash(f"Authentication failed. Google did not return an authorization code. Reason: {error_reason or 'Unknown'}", "error")
        return redirect(url_for("google_auth.login"))

    google_provider_cfg = get_google_provider_cfg()
    if not google_provider_cfg or "token_endpoint" not in google_provider_cfg:
        flash("Could not verify authentication with Google (config error). Please try again later.", "error")
        return redirect(url_for("index"))
    token_endpoint = google_provider_cfg["token_endpoint"]
    redirect_uri = get_redirect_url()

    try:
        # ... (Token exchange and userinfo fetching logic as before) ...
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url, 
            redirect_url=redirect_uri,
            code=code
        )
        token_response = requests.post(token_url, headers=headers, data=body, auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET), timeout=10)
        token_response.raise_for_status()
        client.parse_request_body_response(json.dumps(token_response.json()))
        userinfo_endpoint = google_provider_cfg.get("userinfo_endpoint")
        if not userinfo_endpoint: raise ValueError("Userinfo endpoint not found in Google config.")
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body, timeout=10)
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()

    except Exception as e: # Generic catch for OAuth flow errors
        logging.exception(f"Error processing Google OAuth callback during token/userinfo: {e}")
        flash("An error occurred during Google sign-in. Please try again.", "error")
        return redirect(url_for("google_auth.login"))

    if not userinfo.get("email_verified"):
        flash("Your Google email is not verified. Please verify it and try again.", "warning")
        return redirect(url_for("google_auth.login"))

    unique_id = userinfo.get("sub")
    users_email = userinfo.get("email","").lower()
    users_name = userinfo.get("given_name") or (userinfo.get("name", "User").split(" ")[0])
    picture = userinfo.get("picture")

    if not unique_id or not users_email:
        logging.error(f"Google OAuth: Missing sub or email. Userinfo: {userinfo}")
        flash("Could not retrieve essential profile information from Google.", "error")
        return redirect(url_for("google_auth.login"))

    existing_user_model = get_user_by_email(users_email)
    logging.info(f"Google login for {users_email}. Existing user in DB: {existing_user_model is not None}")

    if existing_user_model:
        # --- EXISTING USER ---
        login_user(existing_user_model)
        session['google_id'] = unique_id
        session['google_name'] = existing_user_model.full_name or users_name
        session['google_picture'] = picture
        session.pop('pending_registration', None) # Clear any old pending flag

        flash(f'Welcome back, {existing_user_model.full_name or existing_user_model.email}!', 'success')
        
        # Redirect to appropriate dashboard
        if existing_user_model.role == 'admin': return redirect(url_for('admin_routes.dashboard'))
        if existing_user_model.role == 'company':
            return redirect(url_for('company_routes.dashboard')) if existing_user_model.is_approved else redirect(url_for('index')) # Or pending page
        if existing_user_model.role == 'candidate': return redirect(url_for('candidate_routes.dashboard'))
        # Fallback if role is somehow undefined after being an existing user
        return redirect(url_for('index')) 
    else:
        # --- NEW USER ---
        # Create a basic user entry immediately with a temporary/default role,
        # or a specific role that indicates they need to complete registration.
        # Let's use 'pending_role_selection' as a placeholder role.
        try:
            logging.info(f"New user from Google: {users_email}. Creating basic user entry.")
            # For password_hash, your create_user function must handle an empty string
            # or you generate a temporary unguessable hash.
            # The role here is temporary until they complete registration.
            # The `is_approved` flag for 'pending_role_selection' should allow login but gate features.
            temp_role = "pending_setup" # A new role to signify incomplete registration

            user_id = create_user(
                email=users_email,
                password='', # Will be hashed if create_user does that, or ignored
                role=temp_role, 
                full_name=users_name,
                # No phone, linkedin, github yet
                # is_approved for this temp_role should be True to allow login
            )
            
            # Fetch the newly created user to log them in
            newly_created_user_model = get_user_by_id(user_id)
            if not newly_created_user_model:
                logging.critical(f"Failed to fetch newly created user (ID: {user_id}) immediately after creation for {users_email}.")
                flash("Error setting up your initial account. Please try again.", "error")
                return redirect(url_for('google_auth.login'))

            login_user(newly_created_user_model) # Log them in
            
            session['google_id'] = unique_id
            session['google_name'] = users_name # Use Google's name for now
            session['google_picture'] = picture
            session['needs_registration_completion'] = True # New session flag

            flash(f'Welcome, {users_name}! Please complete your registration to access all features.', 'info')
            # Redirect to jobs page or a simplified dashboard
            return redirect(url_for('candidate_routes.jobs')) # <<-- REDIRECT TO JOBS PAGE
            # OR, redirect to a dashboard that prominently features "Complete Registration" and "Browse Jobs"
            # return redirect(url_for('candidate_routes.dashboard')) 

        except Exception as e:
            logging.exception(f"Error creating initial user for {users_email} from Google login:")
            flash("An error occurred while setting up your account. Please try signing in again.", "error")
            return redirect(url_for('google_auth.login'))

@google_auth.route("/logout")
@login_required
def logout():
    # ... (logout logic as previously corrected)
    user_email_for_log = current_user.email if current_user.is_authenticated else "Unknown user"
    logout_user() 
    keys_to_pop = ['google_id', 'google_email', 'google_name', 'google_picture', 
                   'pending_registration', 'needs_registration_completion', '_flashes'] # Added needs_registration_completion
    for key in keys_to_pop:
        session.pop(key, None)
    flash('You have been logged out successfully.', 'info')
    logging.info(f"User {user_email_for_log} logged out.")
    return redirect(url_for('index'))

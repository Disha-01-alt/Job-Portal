# Google Authentication for Job Portal
import json
import os
import requests
from flask import Blueprint, redirect, request, url_for, session, flash
from flask_login import login_user, logout_user, current_user
from oauthlib.oauth2 import WebApplicationClient
from database import get_user_by_email, create_user
from models import User

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Get the current domain for redirect URL
def get_redirect_url():
    base_url = os.environ.get("REPLIT_DEV_DOMAIN")
    if base_url:
        return f'https://{base_url}/google_login/callback'
    else:
        return 'http://localhost:5000/google_login/callback'

client = WebApplicationClient(GOOGLE_CLIENT_ID)
google_auth = Blueprint("google_auth", __name__)

print(f"""
Google Authentication Setup Instructions:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new OAuth 2.0 Client ID
3. Add {get_redirect_url()} to Authorized redirect URIs

For detailed instructions, see:
https://docs.replit.com/additional-resources/google-auth-in-flask#set-up-your-oauth-app--client
""")

@google_auth.route("/google_login")
def login():
    # Find out what URL to hit for Google login
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url.replace("http://", "https://") + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@google_auth.route("/google_login/callback")
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")

    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send a request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url.replace("http://", "https://"),
        redirect_url=request.base_url.replace("http://", "https://"),
        code=code,
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Now that you have tokens (yay) let's find and hit the URL
    # from Google that gives you the user's profile information,
    # including their Google profile image and email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    # You want to make sure their email is verified.
    # The user authenticated with Google, authorized your
    # app, and now you've verified their email through Google!
    userinfo = userinfo_response.json()
    if userinfo.get("email_verified"):
        unique_id = userinfo["sub"]
        users_email = userinfo["email"]
        users_name = userinfo["given_name"]
        picture = userinfo["picture"]
    else:
        return "User email not available or not verified by Google.", 400

    # Check if user exists in database
    existing_user = get_user_by_email(users_email)
    
    if existing_user:
        # User exists, log them in
        user = User(
            user_id=existing_user['id'],
            email=existing_user['email'],
            password_hash='',  # Not needed for Google auth
            role=existing_user['role'],
            full_name=existing_user['full_name'],
            phone=existing_user['phone'],
            linkedin=existing_user['linkedin'],
            github=existing_user['github'],
            is_approved=existing_user['is_approved']
        )
        login_user(user)
        
        # Store Google info in session
        session['google_id'] = unique_id
        session['google_name'] = users_name
        session['google_picture'] = picture
        
        # Redirect based on role
        if user.role == 'admin':
            return redirect(url_for('admin_routes.dashboard'))
        elif user.role == 'company':
            if user.is_approved:
                return redirect(url_for('company_routes.dashboard'))
            else:
                flash('Your company account is pending admin approval.', 'info')
                return redirect(url_for('index'))
        else:
            return redirect(url_for('candidate_routes.dashboard'))
    else:
        # New user - store Google info and redirect to registration
        session['google_id'] = unique_id
        session['google_email'] = users_email
        session['google_name'] = users_name
        session['google_picture'] = picture
        session['pending_registration'] = True
        
        return redirect(url_for('auth_routes.complete_registration'))

@google_auth.route("/logout")
def logout():
    logout_user()
    # Clear all Google-related session data
    session.pop('google_id', None)
    session.pop('google_email', None)
    session.pop('google_name', None)
    session.pop('google_picture', None)
    session.pop('pending_registration', None)
    
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

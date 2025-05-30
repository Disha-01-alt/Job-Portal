import json
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

import requests
from flask import Blueprint, redirect, request, url_for, session, flash
from flask_login import login_user, logout_user
from oauthlib.oauth2 import WebApplicationClient
from database import get_user_by_email
from models import User

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

google_auth = Blueprint("google_auth", __name__)
client = WebApplicationClient(GOOGLE_CLIENT_ID)
print("I am here",GOOGLE_CLIENT_ID)
def get_redirect_url():
    """Get redirect URI depending on environment."""
    Production_domain = os.environ.get("Production_domain")
    if Production_domain:
        print("ID is saying","https://{Production_domain}/google_login/callback")
        return f"https://{Production_domain}/google_login/callback"
    return "http://localhost:5000/google_login/callback"

@google_auth.route("/google_login")
def login():
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    redirect_uri = get_redirect_url()

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=redirect_uri,
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@google_auth.route("/google_login/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Error: Missing code parameter in callback. Check your redirect URI configuration.", 400

    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    token_endpoint = google_provider_cfg["token_endpoint"]

    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=get_redirect_url(),
        code=code,
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    client.parse_request_body_response(json.dumps(token_response.json()))
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    userinfo = userinfo_response.json()
    if not userinfo.get("email_verified"):
        return "User email not available or not verified by Google.", 400

    unique_id = userinfo["sub"]
    users_email = userinfo["email"]
    users_name = userinfo["given_name"]
    picture = userinfo["picture"]

    existing_user = get_user_by_email(users_email)
    if existing_user:
        user = User(
            user_id=existing_user.id,
            email=existing_user.email,
            password_hash='',
            role=existing_user.role,
            full_name=existing_user.full_name,
            phone=existing_user.phone,
            linkedin=existing_user.linkedin,
            github=existing_user.github,
            is_approved=existing_user.is_approved
        )
        login_user(user)
        session.update({
            'google_id': unique_id,
            'google_name': users_name,
            'google_picture': picture
        })
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
        session.update({
            'google_id': unique_id,
            'google_email': users_email,
            'google_name': users_name,
            'google_picture': picture,
            'pending_registration': True
        })
        return redirect(url_for('auth_routes.complete_registration'))

@google_auth.route("/logout")
def logout():
    logout_user()
    session_keys = [
        'google_id', 'google_email', 'google_name',
        'google_picture', 'pending_registration'
    ]
    for key in session_keys:
        session.pop(key, None)
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))


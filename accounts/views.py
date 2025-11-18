from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
import json
import requests
import re
from supabase import create_client
from django.conf import settings
import logging
from django.template import TemplateDoesNotExist
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import uuid
import time
from django.views.decorators.http import require_GET
from pathlib import Path
from django.conf import settings
import json

supabase_admin = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create your views here.
def login_view(request):
    saved_email = request.COOKIES.get('saved_email', '')
    saved_password = request.COOKIES.get('saved_password', '')
    remember_checked = 'checked' if saved_email else ''

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        remember = request.POST.get("remember")

        context = {
            'saved_email': email,
            'saved_password': password,
            'remember_checked': 'checked' if remember else ''
        }

        error_msg = None
        if not email or not password:
            error_msg = "All fields are required."
        elif not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            error_msg = "Invalid email format."

        if error_msg:
            logger.debug(f"login_view: Validation failed: {error_msg}")
            messages.error(request, error_msg)
            response = render(request, "accounts/login.html", context)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response

        try:
            response_auth = supabase_admin.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            logger.debug(f"login_view: Auth response: user_id={getattr(response_auth, 'user', None).id if getattr(response_auth, 'user', None) else 'None'}, "
                        f"session={getattr(response_auth, 'session', None)}")

            if getattr(response_auth, "user", None) and response_auth.user.id and response_auth.session:
                session = response_auth.session
                access_token = session.access_token
                refresh_token = session.refresh_token
                expires_at = session.expires_at
                max_age = int(expires_at - time.time()) if expires_at else 3600

                logger.debug(f"login_view: Login successful for user: {response_auth.user.id}, "
                            f"access_token: {access_token[:10]}..., max_age: {max_age}")

                storage = messages.get_messages(request)
                for _ in storage:
                    pass
                storage.used = True

                request.session['just_logged_in'] = True
                response = redirect("home")

                response.set_cookie('sb-access-token', access_token, max_age=max_age, httponly=True, secure=False, samesite='Lax', path='/')
                response.set_cookie('sb-refresh-token', refresh_token, max_age=60*60*24*30, httponly=True, secure=False, samesite='Lax', path='/')
                
                if remember:
                    response.set_cookie('saved_email', email, max_age=30*24*60*60, httponly=False, secure=False, path='/')
                    response.set_cookie('saved_password', password, max_age=30*24*60*60, httponly=False, secure=False, path='/')

                logger.debug("login_view: Cookies set, redirecting to /landing")
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
                return response
            else:
                error_msg = "Invalid email or password, or email not verified."
                logger.debug(f"login_view: Login failed: {error_msg}")
                messages.error(request, error_msg)
                response = render(request, "accounts/login.html", context)
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
                return response
        except Exception as e:
            logger.error(f"login_view: Error: {str(e)}")
            messages.error(request, f"Login failed: {str(e)}")
            response = render(request, "accounts/login.html", context)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response

    storage = messages.get_messages(request)
    for _ in storage:
        pass
    storage.used = True

    context = {
        'saved_email': saved_email,
        'saved_password': saved_password,
        'remember_checked': remember_checked
    }
    response = render(request, "accounts/login.html", context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def register_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm-password")
        first_name = request.POST.get("first_name", "").strip()
        middle_name = request.POST.get("middle_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        age = request.POST.get("age")
        birthdate = request.POST.get("birthdate")

        errors = {}

        if not email:
            errors["email"] = "Email is required."
        if not password:
            errors["password"] = "Password is required."
        if not confirm_password:
            errors["confirm"] = "Please confirm your password."
        if not first_name:
            errors["first_name"] = "First name is required."
        if not last_name:
            errors["last_name"] = "Last name is required."

        if first_name:
            name_error = validate_name_field(first_name, "First name")
            if name_error:
                errors["first_name"] = name_error
        
        if middle_name:
            name_error = validate_name_field(middle_name, "Middle name")
            if name_error:
                errors["middle_name"] = name_error
        
        if last_name:
            name_error = validate_name_field(last_name, "Last name")
            if name_error:
                errors["last_name"] = name_error

        if email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            errors["email"] = "Invalid email format."

        if password and len(password) < 8:
            errors["password"] = "Password must be at least 8 characters long."

        if password and not re.search(r"[A-Z]", password):
            errors["password"] = "Password must contain at least one uppercase letter."

        if password and not re.search(r"[a-z]", password):
            errors["password"] = "Password must contain at least one lowercase letter."

        if password and not re.search(r"[0-9]", password):
            errors["password"] = "Password must contain at least one number."

        if password and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors["password"] = "Password must contain at least one special character."

        if password and confirm_password and password != confirm_password:
            errors["confirm"] = "Passwords do not match."

        if age:
            try:
                age_int = int(age)
                if age_int < 0 or age_int > 120:
                    errors["age"] = "Age must be between 0 and 120."
            except ValueError:
                errors["age"] = "Age must be a valid number."

        if errors:
            response = render(request, "accounts/register.html", {"errors": errors})
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response

        try:
            response = supabase_admin.auth.sign_up({
                "email": email,
                "password": password
            })

            error_detail = getattr(response, "error", None)
            if error_detail:
                err_msg = error_detail.message if hasattr(error_detail, "message") else str(error_detail)
                if "already" in err_msg.lower() or "duplicate" in err_msg.lower():
                    errors["email"] = "Failed to create account. Email may already be registered."
                    response = render(request, "accounts/register.html", {"errors": errors})
                    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    response['Pragma'] = 'no-cache'
                    response['Expires'] = '0'
                    return response
                else:
                    errors["general"] = err_msg
                    response = render(request, "accounts/register.html", {"errors": errors})
                    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    response['Pragma'] = 'no-cache'
                    response['Expires'] = '0'
                    return response

            if response.user and response.user.id:
                display_name = f"{first_name} {last_name}"
                initials = "".join([part[0].upper() for part in display_name.split()[:2]])
                avatar_url = f"https://placehold.co/100x100/E2E8F0/4A5568?text={initials}"

                user_data = {
                    "id": response.user.id,
                    "email": email,
                    "first_name": first_name,
                    "middle_name": middle_name if middle_name else None,
                    "last_name": last_name,
                    "age": int(age) if age else None,
                    "birthdate": birthdate or None,
                    "avatar_url": avatar_url,
                    "contact_number": None,
                    "gender": None,
                    "marital_status": None,
                    "religion": None,
                    "birthplace": None,
                    "purok": None,
                    "city": None,
                }

                result = supabase_admin.table("users").insert(user_data).execute()

                if result.data:
                    messages.success(request, "Account created successfully. Please check your email to verify.")
                    response = redirect("login")
                    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    response['Pragma'] = 'no-cache'
                    response['Expires'] = '0'
                    return response
                else:
                    supabase_admin.auth.admin.delete_user(response.user.id)
                    errors["general"] = "Failed to save user data. Please try again."
                    response = render(request, "accounts/register.html", {"errors": errors})
                    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    response['Pragma'] = 'no-cache'
                    response['Expires'] = '0'
                    return response

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            err_msg = str(e)
            if "duplicate" in err_msg.lower():
                errors["email"] = "Email already registered."
            else:
                errors["general"] = err_msg
            response = render(request, "accounts/register.html", {"errors": errors})
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response

    response = render(request, "accounts/register.html")
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def register_success_view(request):
    response = render(request, 'accounts/register_success.html')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
    
def validate_name_field(name, field_label):
    """Validate that a name field contains only letters, spaces, hyphens, and apostrophes"""
    if not name:
        return None
    if not re.match(r"^[a-zA-Z\s'-]+$", name):
        return f"{field_label} should only contain letters, spaces, hyphens, and apostrophes."
    return None
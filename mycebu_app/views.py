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

supabase_admin = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_authed_user(request):
    access_token = request.COOKIES.get('sb-access-token')
    logger.debug(f"get_authed_user: sb-access-token={'present' if access_token else 'missing'}")
    
    if not access_token:
        logger.debug("get_authed_user: No sb-access-token found in cookies")
        return None

    supabase_user = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    try:
        user_resp = supabase_user.auth.get_user(access_token)
        logger.debug(f"get_authed_user: get_user response={user_resp}")
        
        user = getattr(user_resp, "user", None)
        if not user or not getattr(user, "id", None):
            logger.debug("get_authed_user: No valid user found for token")
            return None

        meta = getattr(user, "user_metadata", {}) or {}
        email = getattr(user, "email", None) or meta.get("email")

        try:
            user_data_resp = supabase_admin.table("users").select(
                "first_name, middle_name, last_name, age, birthdate, avatar_url, contact_number, gender, marital_status, religion, birthplace, purok, city"
            ).eq("id", user.id).execute()
            
            if user_data_resp.data:
                ud = user_data_resp.data[0]
                display_name_parts = [part for part in [ud.get("first_name"), ud.get("last_name")] if part]
                display_name = " ".join(display_name_parts) if display_name_parts else (email.split("@")[0] if email else "User")
            else:
                display_name = email.split("@")[0] if email else "User"

            avatar_url = ud.get("avatar_url") if user_data_resp.data else meta.get("avatar_url")
        except Exception as e:
            logger.error(f"get_authed_user: Error querying users table: {str(e)}")
            display_name = email.split("@")[0] if email else "User"
            avatar_url = None

        if not avatar_url and display_name:
            initials = "".join([part[0].upper() for part in display_name.split()[:2]])
            avatar_url = f"https://placehold.co/100x100/E2E8F0/4A5568?text={initials}"

        return {
            "id": user.id,
            "email": email,
            "first_name": ud.get("first_name") if user_data_resp.data else None,
            "middle_name": ud.get("middle_name") if user_data_resp.data else None,
            "last_name": ud.get("last_name") if user_data_resp.data else None,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "age": ud.get("age") if user_data_resp.data else None,
            "birthdate": ud.get("birthdate") if user_data_resp.data else None,
            "contact_number": ud.get("contact_number") if user_data_resp.data else None,
            "gender": ud.get("gender") if user_data_resp.data else None,
            "marital_status": ud.get("marital_status") if user_data_resp.data else None,
            "religion": ud.get("religion") if user_data_resp.data else None,
            "birthplace": ud.get("birthplace") if user_data_resp.data else None,
            "purok": ud.get("purok") if user_data_resp.data else None,
            "city": ud.get("city") if user_data_resp.data else None,
        }
    except Exception as e:
        logger.error(f"get_authed_user: Error validating token: {str(e)}")
        return None

@require_GET
def root_router_view(request):
    user = get_authed_user(request)
    if user:
        return redirect("landing_tab", tab="dashboard")
    return redirect("landing_tab", tab="landing")
                    
def profile_view(request):
    user = get_authed_user(request)
    logger.debug(f"profile_view: User: {user}")
    if not user:
        logger.debug("profile_view: Redirecting to login, no authenticated user")
        return redirect("login")

    if request.method == "GET" and request.headers.get('Accept') == 'application/json':
        return JsonResponse({'user': user})

    if request.method == "POST":
        try:
            first_name = request.POST.get("first_name")
            last_name = request.POST.get("last_name")
            email = request.POST.get("email")
            contact_number = request.POST.get("contact_number")
            birthdate = request.POST.get("birthdate")
            age = request.POST.get("age")
            gender = request.POST.get("gender")
            marital_status = request.POST.get("marital_status")
            religion = request.POST.get("religion")
            birthplace = request.POST.get("birthplace")
            purok = request.POST.get("purok")
            city = request.POST.get("city")

            errors = {}
            if not first_name or not last_name:
                errors["name"] = "First name and last name are required."
            if email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                errors["email"] = "Invalid email format."
            if age:
                try:
                    age_int = int(age)
                    if age_int < 0 or age_int > 120:
                        errors["age"] = "Age must be between 0 and 120."
                except ValueError:
                    errors["age"] = "Age must be a valid number."

            if errors:
                messages.error(request, "Please correct the errors in the form.")
                response = render(request, "mycebu_app/pages/profile.html", {"user": user, "errors": errors})
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
                return response

            avatar_url = user["avatar_url"]
            if "avatar" in request.FILES:
                avatar_file = request.FILES["avatar"]
                file_name = f"avatars/{user['id']}/{uuid.uuid4()}{os.path.splitext(avatar_file.name)[1]}"
                file_path = default_storage.save(file_name, ContentFile(avatar_file.read()))
                avatar_url = default_storage.url(file_path)

            user_data = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "contact_number": contact_number or None,
                "birthdate": birthdate or None,
                "age": int(age) if age else None,
                "gender": gender or None,
                "marital_status": marital_status or None,
                "religion": religion or None,
                "birthplace": birthplace or None,
                "purok": purok or None,
                "city": city or None,
                "avatar_url": avatar_url,
            }

            logger.debug(f"profile_view: Updating user {user['id']} with data: {user_data}")
            result = supabase_admin.table("users").update(user_data).eq("id", user["id"]).execute()
            logger.debug(f"profile_view: Update result: {result}")

            if result.data:
                messages.success(request, "Profile updated successfully.")
                user = get_authed_user(request)
                if not user:
                    logger.error("profile_view: Failed to refresh user data after update")
                    messages.error(request, "Profile updated, but failed to refresh user data.")
            else:
                logger.error(f"profile_view: Update failed, result: {result}")
                messages.error(request, "Failed to update profile in database.")

            response = render(request, "mycebu_app/pages/profile.html", {"user": user})
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
        except Exception as e:
            logger.error(f"profile_view: Update error: {str(e)}")
            messages.error(request, f"An error occurred while updating the profile: {str(e)}")
            response = render(request, "mycebu_app/pages/profile.html", {"user": user})
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response

    response = render(request, "mycebu_app/pages/profile.html", {"user": user})
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

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
            response = render(request, "mycebu_app/login.html", context)
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
                response = render(request, "mycebu_app/login.html", context)
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
                return response
        except Exception as e:
            logger.error(f"login_view: Error: {str(e)}")
            messages.error(request, f"Login failed: {str(e)}")
            response = render(request, "mycebu_app/login.html", context)
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
    response = render(request, "mycebu_app/login.html", context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def register_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm-password")
        first_name = request.POST.get("first_name")
        middle_name = request.POST.get("middle_name")
        last_name = request.POST.get("last_name")
        age = request.POST.get("age")
        birthdate = request.POST.get("birthdate")

        errors = {}

        if not all([email, password, confirm_password, first_name, last_name]):
            errors["name"] = "Email, password, first name, and last name are required."

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
            response = render(request, "mycebu_app/register.html", {"errors": errors})
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
                    response = render(request, "mycebu_app/register.html", {"errors": errors})
                    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    response['Pragma'] = 'no-cache'
                    response['Expires'] = '0'
                    return response
                else:
                    errors["general"] = err_msg
                    response = render(request, "mycebu_app/register.html", {"errors": errors})
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
                    "middle_name": middle_name or None,
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
                    response = render(request, "mycebu_app/register.html", {"errors": errors})
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
            response = render(request, "mycebu_app/register.html", {"errors": errors})
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response

    response = render(request, "mycebu_app/register.html")
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

@csrf_exempt
def chat_view(request):
    if request.method != 'POST':
        logger.debug("chat_view: Non-POST request received")
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user = get_authed_user(request)
    if not user or not user.get("id"):
        logger.debug("chat_view: Authentication required")
        return JsonResponse({'error': 'Authentication required'}, status=401)

    try:
        data = json.loads(request.body)
        prompt = data.get('prompt', '').strip()

        if not prompt:
            logger.debug("chat_view: Prompt is empty")
            return JsonResponse({'error': 'Prompt is required'}, status=400)

        api_url = "https://router.huggingface.co/novita/v3/openai/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "model": "deepseek/deepseek-v3-0324",
            "stream": False
        }

        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        api_response = response.json()

        bot_message = api_response.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        success = bool(bot_message)

        if not success or not bot_message:
            logger.error(f"chat_view: API failed - HTTP: {response.status_code}, Response: {response.text[:200]}")
            bot_message = "I'm having trouble connecting to my AI brain right now. Can you try asking again?"

        logger.debug(f"chat_view: Success, bot_message: {bot_message[:50]}...")
        return JsonResponse({
            'success': True,
            'message': bot_message
        })

    except requests.exceptions.RequestException as e:
        logger.error(f"chat_view: API Request Error: {str(e)}")
        return JsonResponse({'error': f'Failed to process request: {str(e)}'}, status=500)
    except Exception as e:
        logger.error(f"chat_view: General Error: {str(e)}")
        return JsonResponse({'error': f'Failed to process request: {str(e)}'}, status=500)

def chatbot_page(request):
    user = get_authed_user(request)
    logger.debug(f"chatbot_page: User: {user}")
    if not user:
        logger.debug("chatbot_page: Redirecting to login, no authenticated user")
        return redirect("login")
    
    response = render(request, 'mycebu_app/test.html', {"user": user})
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
                    
def landing_view(request, tab='landing'):
    if request.session.pop('just_logged_in', False):
        messages.success(request, "Welcome back, you are now logged in.")
    
    context = {'current_tab': tab, 'services_data': None, 'authed_user': get_authed_user(request)}
    try:
        response = render(request, f"mycebu_app/pages/{tab}.html", context)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    except TemplateDoesNotExist:
        response = render(request, "mycebu_app/pages/coming_soon.html", context)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

def dashboard_view(request):
    user = get_authed_user(request)
    if not user:
        return redirect("login")
    ctx = {"user": user, "authed_user": user, "current_tab": "dashboard"}
    response = render(request, "mycebu_app/pages/dashboard.html", ctx)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def register_success_view(request):
    response = render(request, 'mycebu_app/register_success.html')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def password_reset_email_view(request):
    if request.method == "POST":
        response = redirect("/password-reset-new-password")
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    response = render(request, 'mycebu_app/password_reset/email_form.html')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def password_reset_new_password_view(request):
    if request.method == "POST":
        response = redirect("/password-reset-success")
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    response = render(request, 'mycebu_app/password_reset/new_password.html')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def password_reset_success_view(request):
    if request.method == "POST":
        response = redirect("/login")
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    response = render(request, 'mycebu_app/password_reset/reset_success.html')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def logout_view(request):
    logger.debug(f"logout_view: Request method: {request.method}, cookies: {request.COOKIES}")
    if request.method == "POST":
        try:
            access_token = request.COOKIES.get('sb-access-token')
            if access_token:
                supabase_user = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                supabase_user.auth.sign_out()
                logger.debug("logout_view: Supabase sign_out called")
        except Exception as e:
            logger.error(f"logout_view: Supabase sign_out error: {str(e)}")
        
        request.session.flush()
        storage = messages.get_messages(request)
        for _ in storage:
            pass
        storage.used = True

        response = redirect('login')
        response.delete_cookie('sb-access-token', path='/')
        response.delete_cookie('sb-refresh-token', path='/')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        logger.debug("logout_view: Logout successful, cookies cleared")
        return response
    
    logger.debug("logout_view: Non-POST request, redirecting to login")
    return redirect('login')

def dashboard_view(request):
    user = get_authed_user(request)
    logger.debug(f"dashboard_view: User: {user}")
    if not user:
        logger.debug("dashboard_view: Redirecting to login, no authenticated user")
        return redirect("login")
    
    response = render(request, "mycebu_app/pages/dashboard.html", {"user": user})
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
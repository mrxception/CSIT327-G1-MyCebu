from django.http import JsonResponse
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

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def get_authed_user():
    try:
        session = supabase.auth.get_session()
        user = getattr(session, "user", None)
        if not user or not getattr(user, "id", None):
            return None

        meta = getattr(user, "user_metadata", {}) or {}
        email = getattr(user, "email", None) or meta.get("email")

        user_data_resp = supabase.table("users").select("first_name, middle_name, last_name").eq("id", user.id).execute()
        if user_data_resp.data:
            ud = user_data_resp.data[0]
            display_name_parts = [part for part in [ud.get("first_name"), ud.get("middle_name"), ud.get("last_name")] if part]
            display_name = " ".join(display_name_parts) if display_name_parts else (email.split("@")[0] if email else "User")
        else:
            display_name = email.split("@")[0] if email else "User"

        avatar_url = meta.get("avatar_url")

        return {
            "id": user.id,
            "email": email,
            "display_name": display_name,
            "avatar_url": avatar_url,
        }
    except Exception:
        return None
    
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
            messages.error(request, error_msg)
            response = render(request, "mycebu_app/login.html", context)
        else:
            try:
                response_auth = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })

                if getattr(response_auth, "user", None) and response_auth.user.id:
                    storage = messages.get_messages(request)
                    for _ in storage:
                        pass  
                    storage.used = True

                    request.session['just_logged_in'] = True
                    response = redirect("/landing")
                else:
                    error_msg = "Invalid email or password, or email not verified."
                    messages.error(request, error_msg)
                    response = render(request, "mycebu_app/login.html", context)
            except Exception as e:
                messages.error(request, f"{str(e)}")
                response = render(request, "mycebu_app/login.html", context)

        if remember:
            response.set_cookie('saved_email', email, max_age=30*24*60*60, httponly=False, secure=False)
            response.set_cookie('saved_password', password, max_age=30*24*60*60, httponly=False, secure=False)
        else:
            response.delete_cookie('saved_email')
            response.delete_cookie('saved_password')

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
    return render(request, "mycebu_app/login.html", context)

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
            return render(request, "mycebu_app/register.html", {"errors": errors})

        try:
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            error_detail = getattr(response, "error", None)
            if error_detail:
                err_msg = error_detail.message if hasattr(error_detail, "message") else str(error_detail)
                if "already" in err_msg.lower() or "duplicate" in err_msg.lower():
                    errors["email"] = "Failed to create account. Email may already be registered."
                    return render(request, "mycebu_app/register.html", {"errors": errors})
                else:
                    errors["general"] = err_msg
                    return render(request, "mycebu_app/register.html", {"errors": errors})

            if response.user and response.user.id:
                user_data = {
                    "id": response.user.id,
                    "email": email,
                    "password": password, 
                    "first_name": first_name,
                    "middle_name": middle_name or None,
                    "last_name": last_name,
                    "age": int(age) if age else None,
                    "birthdate": birthdate or None
                }

                result = supabase.table("users").insert(user_data).execute()

                if result.data:
                    messages.success(request, "Account created successfully. Please check your email to verify.")
                    return redirect("login")
                else:
                    supabase.auth.admin.delete_user(response.user.id)
                    errors["general"] = "Failed to save user data. Please try again."
                    return render(request, "mycebu_app/register.html", {"errors": errors})

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            err_msg = str(e)
            if "duplicate" in err_msg.lower():
                errors["email"] = "Email already registered."
            else:
                errors["general"] = err_msg
            return render(request, "mycebu_app/register.html", {"errors": errors})

    return render(request, "mycebu_app/register.html")

@csrf_exempt
def chat_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    session = supabase.auth.get_session()
    if not session or not session.user or not session.user.id:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    try:
        data = json.loads(request.body)
        prompt = data.get('prompt', '').strip()

        if not prompt:
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
            logger.error(f"API failed - HTTP: {response.status_code}, Response: {response.text[:200]}")
            bot_message = "I'm having trouble connecting to my AI brain right now. Can you try asking again?"

        return JsonResponse({
            'success': True,
            'message': bot_message
        })

    except requests.exceptions.RequestException as e:
        logger.error(f"API Request Error: {str(e)}")
        return JsonResponse({'error': f'Failed to process request: {str(e)}'}, status=500)
    except Exception as e:
        logger.error(f"General Error: {str(e)}")
        return JsonResponse({'error': f'Failed to process request: {str(e)}'}, status=500)

def chatbot_page(request):
    session = supabase.auth.get_session()
    if not session or not session.user or not session.user.id:
        return redirect("login")
    return render(request, 'mycebu_app/test.html')

def landing_view(request, tab='landing'):
    if request.session.pop('just_logged_in', False):
        messages.success(request, "Welcome back, you are now logged in.")
    
    context = {'current_tab': tab, 'services_data': None, 'authed_user': get_authed_user()}
    template = f"mycebu_app/pages/{tab}.html"
    try:
        return render(request, template, context)
    except TemplateDoesNotExist:
        return render(request, "mycebu_app/pages/coming_soon.html", context)

def register_success_view(request):
    return render(request, 'mycebu_app/register_success.html')

def password_reset_email_view(request):
    if request.method == "POST":
        return redirect("/password-reset-new-password")
    return render(request, 'mycebu_app/password_reset/email_form.html')

def password_reset_new_password_view(request):
    if request.method == "POST":
        return redirect("/password-reset-success")
    return render(request, 'mycebu_app/password_reset/new_password.html')

def password_reset_success_view(request):
    if request.method == "POST":
        return redirect("/login")
    return render(request, 'mycebu_app/password_reset/reset_success.html')

def logout_view(request):
    if request.method == "POST":
        try:
            supabase.auth.sign_out()
        except Exception as e:
            print(f"Supabase sign_out error: {e}")
        
        request.session.flush()

        storage = messages.get_messages(request)
        for _ in storage:
            pass
        storage.used = True

        response = redirect('login')
        return response
    
    return redirect('login')
def dashboard_view(request):
    context = {'current_tab': 'dashboard'}
    return render(request, 'mycebu_app/pages/dashboard.html', context)

def profile_view(request):
    return render(request, 'mycebu_app/pages/profile.html')


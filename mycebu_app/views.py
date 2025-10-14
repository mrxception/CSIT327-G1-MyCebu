from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
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

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            if not all([email, password]):
                messages.error(request, "All fields are required.")
                return redirect("login")

            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                messages.error(request, "Invalid email format.")
                return redirect("login")

            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if getattr(response, "user", None) and response.user.id:
                messages.success(request, "Welcome back, you are now logged in.")
                return redirect("/test")
            else:
                messages.error(request, "Invalid email or password, or email not verified.")
                return redirect("login")

        except Exception as e:
            messages.error(request, f"Login failed: {str(e)}")
            return redirect("login")

    return render(request, "mycebu_app/login.html")

def register_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        username = request.POST.get("username")
        confirm_password = request.POST.get("confirm-password")

        try:
            if not all([email, password, username, confirm_password]):
                messages.error(request, "All fields are required.")
                return redirect("register")

            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                messages.error(request, "Invalid email format.")
                return redirect("register")

            if len(password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
                return redirect("register")

            if not re.search(r"[A-Z]", password):
                messages.error(request, "Password must contain at least one uppercase letter.")
                return redirect("register")

            if not re.search(r"[a-z]", password):
                messages.error(request, "Password must contain at least one lowercase letter.")
                return redirect("register")

            if not re.search(r"[0-9]", password):
                messages.error(request, "Password must contain at least one number.")
                return redirect("register")

            if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
                messages.error(request, "Password must contain at least one special character.")
                return redirect("register")

            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            if not response.user or not response.user.id:
                messages.error(request, "Failed to create account. Email may already be registered.")
                return redirect("register")

            messages.success(request, "Account created successfully. Please check your email to verify.")
            return redirect("login")

        except Exception as e:
            messages.error(request, f"Registration failed: {str(e)}")
            return redirect("register")

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
    context = {'current_tab': tab, 'services_data': None}
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
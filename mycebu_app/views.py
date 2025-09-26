from django.shortcuts import render, redirect
from django.contrib import messages
from supabase import create_client
from django.conf import settings
import time
import re

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

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
                return redirect("/")
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

            existing_email = supabase.table("users").select("id").eq("email", email).execute()
            if existing_email.data:
                messages.error(request, "Email already taken.")
                return redirect("register")

            existing_username = supabase.table("users").select("id").eq("username", username).execute()
            if existing_username.data:
                messages.error(request, "Username already taken.")
                return redirect("register")

            if password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return redirect("register")

            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            if not response.user or not response.user.id:
                messages.error(request, "Failed to create account. Email may already be registered.")
                return redirect("register")

            user_id = response.user.id

            time.sleep(1)

            user_data = {
                "id": str(user_id),
                "email": email,
                "username": username,
                "password": password  
            }
            insert_result = supabase.table("users").insert(user_data).execute()

            if not insert_result.data:
                messages.error(request, "Failed to create profile. Please try again.")
                return redirect("register")

            messages.success(request, "Account created successfully. Please check your email to verify.")
            return redirect("login")

        except Exception as e:
            messages.error(request, f"Registration failed: {str(e)}")
            return redirect("register")

    return render(request, "mycebu_app/register.html")
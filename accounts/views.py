from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import re

# -------------------------
# LOGIN
# -------------------------
def login_view(request):
    saved_email = request.COOKIES.get("saved_email", "")
    saved_password = request.COOKIES.get("saved_password", "")
    remember_checked = "checked" if saved_email else ""

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        remember = request.POST.get("remember")

        context = {
            "saved_email": email,
            "saved_password": password,
            "remember_checked": "checked" if remember else "",
        }

        if not email or not password:
            messages.error(request, "All fields are required.")
            return render(request, "accounts/login.html", context)

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            messages.error(request, "Invalid email format.")
            return render(request, "accounts/login.html", context)

        try:
            user = User.objects.filter(email=email).first()
            if not user:
                messages.error(request, "Invalid email or password.")
                return render(request, "accounts/login.html", context)

            user = authenticate(request, username=user.username, password=password)
            if not user:
                messages.error(request, "Invalid email or password.")
                return render(request, "accounts/login.html", context)

            login(request, user)
            request.session["just_logged_in"] = True

            response = redirect("home")

            if remember:
                response.set_cookie("saved_email", email, max_age=30 * 24 * 60 * 60)
                response.set_cookie("saved_password", password, max_age=30 * 24 * 60 * 60)

            return response

        except Exception as e:
            messages.error(request, f"Login failed: {str(e)}")
            return render(request, "accounts/login.html", context)

    return render(request, "accounts/login.html", {
        "saved_email": saved_email,
        "saved_password": saved_password,
        "remember_checked": remember_checked,
    })


# -------------------------
# REGISTER
# -------------------------
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
        if password != confirm_password:
            errors["confirm"] = "Passwords do not match."
        if not first_name:
            errors["first_name"] = "First name is required."
        if not last_name:
            errors["last_name"] = "Last name is required."

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

        if User.objects.filter(email=email).exists():
            errors["email"] = "Email is already registered."

        if errors:
            return render(request, "accounts/register.html", {"errors": errors})

        try:
            username = email.split("@")[0]

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                date_joined=timezone.now(),
            )

            messages.success(request, "Account created successfully. You may now log in.")
            return redirect("login")

        except Exception as e:
            errors["general"] = str(e)
            return render(request, "accounts/register.html", {"errors": errors})

    return render(request, "accounts/register.html")


# -------------------------
# REGISTER SUCCESS
# -------------------------
def register_success_view(request):
    return render(request, "accounts/register_success.html")


# -------------------------
# LOGOUT
# -------------------------
def logout_view(request):
    logout(request)
    response = redirect("login")
    response.delete_cookie("saved_email")
    response.delete_cookie("saved_password")
    return response


# -------------------------
# VALIDATION
# -------------------------
def validate_name_field(name, field_label):
    if not name:
        return None
    if not re.match(r"^[a-zA-Z\s'-]+$", name):
        return f"{field_label} should only contain letters, spaces, hyphens, and apostrophes."
    return None

import os
import re
import time
import random
import logging
import requests
import ssl
import smtplib

from django.shortcuts import render, redirect
from django.core.cache import cache
from django.contrib import messages
from django.conf import settings
from email.message import EmailMessage

logger = logging.getLogger(__name__)

OTP_TTL_SECONDS = 10 * 60  
OTP_LENGTH = 6


def _send_otp_email(to_email: str, otp: str):
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    if not smtp_user or not smtp_pass:
        raise RuntimeError("SMTP_USER or SMTP_PASS missing in environment")

    subject = "MyCebu Password Reset OTP"
    body = f"""
Your MyCebu password reset OTP is: {otp}
This OTP expires in {OTP_TTL_SECONDS // 60} minutes.

If you did not request this, please ignore this message.
"""

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content(body)

    ctx = ssl.create_default_context()

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls(context=ctx)
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


def _store_otp(email: str, otp: str):
    cache.set(
        f"otp_{email.lower()}",
        {"otp": otp, "timestamp": int(time.time())},
        timeout=OTP_TTL_SECONDS,
    )


def _verify_otp(email: str, otp: str) -> bool:
    payload = cache.get(f"otp_{email.lower()}")
    if not payload:
        return False

    if str(payload["otp"]) != str(otp):
        return False

    cache.delete(f"otp_{email.lower()}")
    return True


def _get_supabase_service_role_key():
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY missing")
    return key


def _find_supabase_user(email: str):
    """
    Find user in Supabase Auth (not SQL).
    Supabase's GET /admin/users?email= is unreliable and returns ALL users,
    so we must manually filter.
    """
    service_role = _get_supabase_service_role_key()

    url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/admin/users?email={email}"
    headers = {
        "apikey": service_role,
        "Authorization": f"Bearer {service_role}",
    }

    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()

    print("RAW SUPABASE RESPONSE:", data)

    if isinstance(data, dict) and "users" in data:
        for user in data["users"]:
            if user.get("email", "").lower() == email.lower():
                return user

    if isinstance(data, list):
        for user in data:
            if user.get("email", "").lower() == email.lower():
                return user

    return None


def _update_supabase_password(user_id: str, new_password: str, email: str):
    """Update user password using Supabase Admin API (must use PUT)."""
    service_role = _get_supabase_service_role_key()

    url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/admin/users/{user_id}"
    headers = {
        "apikey": service_role,
        "Authorization": f"Bearer {service_role}",
        "Content-Type": "application/json",
    }

    payload = {
        "email": email,
        "password": new_password,
    }

    r = requests.put(url, headers=headers, json=payload)
    r.raise_for_status()
    return r.json()


def password_reset_email_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if not email:
            messages.error(request, "Email is required.")
            return render(request, "reset/email_form.html")

        user = _find_supabase_user(email)
        if not user:
            messages.error(request, "No account found in MyCebu for that email.")
            return render(request, "reset/email_form.html")

        otp = str(random.randint(10**(OTP_LENGTH - 1), 10**OTP_LENGTH - 1))
        _store_otp(email, otp)

        try:
            _send_otp_email(email, otp)
        except Exception as e:
            logger.error("Email sending failed: %s", e)
            messages.error(request, "Failed to send email. Try again later.")
            return render(request, "reset/email_form.html")

        request.session["reset_email"] = email
        request.session.set_expiry(OTP_TTL_SECONDS)

        return redirect("password_reset_new_password")

    return render(request, "reset/email_form.html")


def password_reset_new_password_view(request):

    email = request.session.get("reset_email")

    if request.method == "POST":
        otp = request.POST.get("otp", "")
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm-password", "")

        if not _verify_otp(email, otp):
            messages.error(request, "Invalid or expired OTP.")
            return render(request, "reset/new_password.html")

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, "reset/new_password.html")

        user = _find_supabase_user(email)
        if not user:
            messages.error(request, "No user found.")
            return render(request, "reset/new_password.html")

        try:
            _update_supabase_password(user["id"], password, email)

        except Exception as e:
            logger.error("Password update failed: %s", e)
            messages.error(request, "Failed to update password. Please try again later.")
            return render(request, "reset/new_password.html")

        request.session.pop("reset_email", None)
        messages.success(request, "Password updated successfully!")

        return redirect("password_reset_success")

    return render(request, "reset/new_password.html")


def password_reset_success_view(request):
    return render(request, "reset/reset_success.html")

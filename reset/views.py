import os
import time
import random
import logging
import ssl
import smtplib
from email.message import EmailMessage

from django.shortcuts import render, redirect
from django.core.cache import cache
from django.contrib import messages
from django.contrib.auth.models import User  # IMPORT DJANGO USER MODEL
from django.conf import settings

logger = logging.getLogger(__name__)

OTP_TTL_SECONDS = 10 * 60  
OTP_LENGTH = 6

# ==========================================
# OTP HELPERS (SMTP & CACHE)
# ==========================================

def _send_otp_email(to_email: str, otp: str):
    """Sends OTP via SMTP (Gmail or other providers)"""
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    if not smtp_user or not smtp_pass:
        # Log error but don't crash app if env vars missing, just raise to be caught
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

    # Create secure SSL context
    ctx = ssl.create_default_context()

    try:
        # Connect to Gmail SMTP (adjust host/port if using different provider)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    except Exception as e:
        logger.error(f"SMTP Error: {e}")
        raise e


def _store_otp(email: str, otp: str):
    """Stores OTP in Django Cache (Redis or LocalMem)"""
    cache.set(
        f"otp_{email.lower()}",
        {"otp": otp, "timestamp": int(time.time())},
        timeout=OTP_TTL_SECONDS,
    )


def _verify_otp(email: str, otp: str) -> bool:
    """Verifies OTP from Cache"""
    payload = cache.get(f"otp_{email.lower()}")
    if not payload:
        return False

    if str(payload["otp"]) != str(otp):
        return False

    # Optional: Delete OTP after successful use to prevent replay
    cache.delete(f"otp_{email.lower()}")
    return True


# ==========================================
# PASSWORD RESET VIEWS
# ==========================================


def password_reset_email_view(request):
    """
    Step 1: User enters email. We check DB, generate OTP, send Email.
    """
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if not email:
            messages.error(request, "Email is required.")
            return render(request, "reset/email_form.html")

        # CHANGED: Use Django ORM instead of Supabase API
        # Check if user exists in the PostgreSQL database
        if not User.objects.filter(email=email).exists():
            messages.error(request, "No account found in MyCebu for that email.")
            return render(request, "reset/email_form.html")

        # Generate OTP
        otp = str(random.randint(10**(OTP_LENGTH - 1), 10**OTP_LENGTH - 1))
        
        # Store in Cache
        _store_otp(email, otp)

        try:
            # Send Email
            _send_otp_email(email, otp)
        except Exception as e:
            logger.error("Email sending failed: %s", e)
            messages.error(request, "Failed to send email. Please check your SMTP settings.")
            return render(request, "reset/email_form.html")

        # Save email to session for the next step
        request.session["reset_email"] = email
        request.session.set_expiry(OTP_TTL_SECONDS)

        return redirect("password_reset_new_password")

    return render(request, "reset/email_form.html")


def password_reset_new_password_view(request):
    """
    Step 2: User enters OTP and New Password. We verify and update DB.
    """
    email = request.session.get("reset_email")

    # If session expired or user accessed directly without step 1
    if not email:
        messages.error(request, "Session expired. Please start over.")
        return redirect("password_reset_email")

    if request.method == "POST":
        otp = request.POST.get("otp", "")
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm-password", "")

        # 1. Verify OTP
        if not _verify_otp(email, otp):
            messages.error(request, "Invalid or expired OTP.")
            return render(request, "reset/new_password.html")

        # 2. Validate Password Match
        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, "reset/new_password.html")

        try:
            # CHANGED: Use Django ORM to update password
            user = User.objects.get(email=email)
            user.set_password(password) # set_password handles hashing automatically
            user.save()

            # Clean up session
            request.session.pop("reset_email", None)
            
            messages.success(request, "Password updated successfully!")
            return redirect("password_reset_success")

        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return render(request, "reset/new_password.html")
        except Exception as e:
            logger.error("Password update failed: %s", e)
            messages.error(request, "An error occurred while updating the password.")
            return render(request, "reset/new_password.html")

    return render(request, "reset/new_password.html")


def password_reset_success_view(request):
    """
    Step 3: Success page.
    """
    return render(request, "reset/reset_success.html")
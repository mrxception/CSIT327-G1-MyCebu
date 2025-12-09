import os
import time
import logging
# Removed ssl, smtplib, EmailMessage as they are not needed for bypass

from django.shortcuts import render, redirect
from django.core.cache import cache
from django.contrib import messages
from django.contrib.auth.models import User
from django.conf import settings

logger = logging.getLogger(__name__)

OTP_TTL_SECONDS = 10 * 60  
OTP_LENGTH = 6
HARDCODED_OTP = "2459"  # <--- Hardcoded OTP

# ==========================================
# OTP HELPERS (CACHE ONLY - NO SMTP)
# ==========================================

def _store_otp(email: str, otp: str):
    """Stores OTP in Django Cache"""
    # We store the hardcoded OTP regardless of input to ensure verification works
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

    # Optional: Delete OTP after successful use
    cache.delete(f"otp_{email.lower()}")
    return True


# ==========================================
# PASSWORD RESET VIEWS
# ==========================================


def password_reset_email_view(request):
    """
    Step 1: User enters email. We check DB, set hardcoded OTP, SKIP EMAIL.
    """
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if not email:
            messages.error(request, "Email is required.")
            return render(request, "reset/email_form.html")

        # Check if user exists in the PostgreSQL database
        if not User.objects.filter(email=email).exists():
            messages.error(request, "No account found in MyCebu for that email.")
            return render(request, "reset/email_form.html")

        # USE HARDCODED OTP
        otp = HARDCODED_OTP
        
        # Store in Cache
        _store_otp(email, otp)

        # LOG INSTEAD OF SENDING EMAIL
        logger.info(f"BYPASS: OTP for {email} is {otp}. No email sent.")

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

        # 1. Verify OTP (Will check against 2459)
        if not _verify_otp(email, otp):
            messages.error(request, "Invalid or expired OTP.")
            return render(request, "reset/new_password.html")

        # 2. Validate Password Match
        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, "reset/new_password.html")

        try:
            # Update password using Django ORM
            user = User.objects.get(email=email)
            user.set_password(password) # Handles hashing
            user.save()

            # Clean up session
            request.session.pop("reset_email", None)
            
            messages.success(request, "Password updated successfully!")
            return redirect("password_reset_success")

        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return render(request, "reset/new_password.html")
        except Exception as e:
            logger.error(f"Password update failed: {e}")
            messages.error(request, "An error occurred while updating the password.")
            return render(request, "reset/new_password.html")

    return render(request, "reset/new_password.html")


def password_reset_success_view(request):
    """
    Step 3: Success page.
    """
    return render(request, "reset/reset_success.html")
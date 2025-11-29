import os
import uuid
import json
import time
import logging
import re
import requests
from pathlib import Path
from datetime import datetime

# Cloudinary Imports
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Django Imports
from django.db import connection
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.template import TemplateDoesNotExist
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

# Auth Imports
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User as DjangoAuthUser

# === MODEL IMPORTS ===
from .models import Complaint, Ordinance, ServiceApplication

# Try to import the Custom User model from 'accounts' app, fallback to 'mycebu_app' if not found
try:
    from accounts.models import User as DbUser
except ImportError:
    from mycebu_app.models import User as DbUser

# ==========================================
# SETUP & LOGGING
# ==========================================

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ==========================================
# CLOUDINARY UPLOAD HELPER
# ==========================================
def upload_to_cloudinary(file_obj, folder="profiles"):
    """
    Uploads a file object to Cloudinary.
    NO ERROR HANDLING - We want it to crash if it fails so we see why.
    """
    # 1. Print keys to console to verify they are loaded (Check your terminal!)
    print(f"DEBUG: Cloud Name: {settings.CLOUDINARY_STORAGE['CLOUD_NAME']}")
    print(f"DEBUG: API Key: {settings.CLOUDINARY_STORAGE['API_KEY']}")
    
    # 2. Configure
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_STORAGE['CLOUD_NAME'],
        api_key=settings.CLOUDINARY_STORAGE['API_KEY'],
        api_secret=settings.CLOUDINARY_STORAGE['API_SECRET']
    )
    
    # 3. Upload
    upload_result = cloudinary.uploader.upload(
        file_obj,
        folder=f"mycebu/{folder}",
        resource_type="auto"
    )
    
    return upload_result.get("secure_url")

# ==========================================
# DATA LOADING HELPERS
# ==========================================

def _load_services_data():
    data_path = Path(settings.BASE_DIR) / "static" / "mycebu_app" / "data" / "services.json"
    if not data_path.exists():
        return []
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("services", [])
    except Exception:
        return []

def _load_directory_data():
    data_path = Path(settings.BASE_DIR) / "static" / "mycebu_app" / "data" / "directory.json"
    if not data_path.exists():
        return {"officials": [], "positions": [], "districts": [], "emergencyContacts": []}
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"officials": [], "positions": [], "districts": [], "emergencyContacts": []}

def get_authed_user(request):
    """
    Combines the Login User (DjangoAuthUser) with your Custom Data User (DbUser).
    Linked by Email.
    """
    if not request.user.is_authenticated:
        return None

    # 1. Get basic info from the currently logged in session
    auth_user = request.user
    
    # 2. Find the corresponding record in your custom 'users' table
    db_user = DbUser.objects.filter(email=auth_user.email).first()

    # 3. Construct the full profile dictionary
    user_id = auth_user.id
    if db_user:
        user_id = db_user.id # Use the UUID from your custom table if available

    display_name = f"{auth_user.first_name} {auth_user.last_name}".strip()
    if not display_name:
        display_name = auth_user.username

    # Avatar logic
    avatar_url = f"https://ui-avatars.com/api/?name={auth_user.username}&background=random"
    if db_user and db_user.avatar_url:
        avatar_url = db_user.avatar_url

    return {
        # IDs
        "id": user_id,
        
        # Standard Fields (From Django Auth)
        "username": auth_user.username,
        "email": auth_user.email,
        "first_name": auth_user.first_name,
        "last_name": auth_user.last_name,
        "display_name": display_name,
        
        # Custom Fields (From your 'users' table)
        "avatar_url": avatar_url,
        "middle_name": db_user.middle_name if db_user else None,
        "age": db_user.age if db_user else None,
        "birthdate": str(db_user.birthdate) if (db_user and db_user.birthdate) else None,
        "contact_number": db_user.contact_number if db_user else None,
        "gender": db_user.gender if db_user else None,
        "marital_status": db_user.marital_status if db_user else None,
        "religion": db_user.religion if db_user else None,
        "birthplace": db_user.birthplace if db_user else None,
        "purok": db_user.purok if db_user else None,
        "city": db_user.city if db_user else None,
    }

def validate_name_field(name, field_label):
    if not name:
        return None
    if not re.match(r"^[a-zA-Z\s'-]+$", name):
        return f"{field_label} should only contain letters, spaces, hyphens, and apostrophes."
    return None

def _get_service_by_id(service_id):
    services = _load_services_data()
    return next((s for s in services if s.get("id") == service_id), None)

# ==========================================
# AUTH VIEWS
# ==========================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect("landing_tab", tab="dashboard")

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

        try:
            # Login uses Django's default User table
            user_obj = DjangoAuthUser.objects.filter(email=email).first()
            if not user_obj:
                messages.error(request, "Invalid email or password.")
                return render(request, "accounts/login.html", context)

            user = authenticate(request, username=user_obj.username, password=password)
            if not user:
                messages.error(request, "Invalid email or password.")
                return render(request, "accounts/login.html", context)

            login(request, user)
            request.session["just_logged_in"] = True

            response = redirect("landing_tab", tab="dashboard")

            if remember:
                response.set_cookie("saved_email", email, max_age=30 * 24 * 60 * 60)
                response.set_cookie("saved_password", password, max_age=30 * 24 * 60 * 60)
            else:
                response.delete_cookie("saved_email")
                response.delete_cookie("saved_password")

            return response

        except Exception as e:
            messages.error(request, f"Login failed: {str(e)}")
            return render(request, "accounts/login.html", context)

    return render(request, "accounts/login.html", {
        "saved_email": saved_email,
        "saved_password": saved_password,
        "remember_checked": remember_checked,
    })


def register_view(request):
    if request.user.is_authenticated:
        return redirect("landing_tab", tab="dashboard")

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm-password")
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        
        errors = {}

        if not email: errors["email"] = "Email is required."
        if not password: errors["password"] = "Password is required."
        if password != confirm_password: errors["confirm"] = "Passwords do not match."
        if not first_name: errors["first_name"] = "First name is required."
        if not last_name: errors["last_name"] = "Last name is required."

        if DjangoAuthUser.objects.filter(email=email).exists():
            errors["email"] = "Email is already registered."

        if errors:
            return render(request, "accounts/register.html", {"errors": errors})

        try:
            # 1. Create in Django Auth Table (for login)
            username = email.split("@")[0] + "_" + str(uuid.uuid4())[:8]
            
            d_user = DjangoAuthUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                date_joined=timezone.now(),
            )

            # 2. Create in Your Custom 'users' Table (for profile data)
            DbUser.objects.create(
                id=uuid.uuid4(),
                email=email,
                first_name=first_name,
                last_name=last_name,
                created_at=timezone.now()
            )

            messages.success(request, "Account created successfully. You may now log in.")
            return redirect("login")

        except Exception as e:
            errors["general"] = str(e)
            return render(request, "accounts/register.html", {"errors": errors})

    return render(request, "accounts/register.html")


def logout_view(request):
    logout(request)
    response = redirect("login")
    return response

# ==========================================
# APP VIEWS
# ==========================================

@require_GET
def root_router_view(request):
    user = get_authed_user(request)
    if user:
        return redirect("landing_tab", tab="dashboard")
    return redirect("landing_tab", tab="landing")
                    
def profile_view(request):
    user_data = get_authed_user(request)
    if not user_data:
        return redirect("login")

    if request.method == "GET" and request.headers.get('Accept') == 'application/json':
        return JsonResponse({'user': user_data})

    if request.method == "POST":
        try:
            # 1. Capture Fields
            first_name = request.POST.get("first_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()
            email = request.POST.get("email", "").strip()
            middle_name = request.POST.get("middle_name", "").strip()
            age = request.POST.get("age")
            contact_number = request.POST.get("contact_number", "").strip()
            birthdate = request.POST.get("birthdate")
            gender = request.POST.get("gender")
            marital_status = request.POST.get("marital_status")
            religion = request.POST.get("religion", "").strip()
            birthplace = request.POST.get("birthplace", "").strip()
            purok = request.POST.get("purok", "").strip()
            city = request.POST.get("city", "").strip()

            errors = {}
            if not first_name or not last_name:
                errors["name"] = "First name and last name are required."
            
            if email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                errors["email"] = "Invalid email format."
            
            if age:
                try:
                    age = int(age)
                except ValueError:
                    errors["age"] = "Age must be a number"
            else:
                age = None

            if errors:
                messages.error(request, "Please correct the errors.")
                return render(request, "mycebu_app/pages/profile.html", {"user": user_data, "errors": errors})

            # A. Update Django Auth User
            auth_u = request.user
            auth_u.first_name = first_name
            auth_u.last_name = last_name
            old_email = auth_u.email
            auth_u.email = email 
            auth_u.save()

            # B. Update Custom 'users' Table
            db_user = DbUser.objects.filter(email=old_email).first()
            if not db_user:
                db_user = DbUser.objects.filter(email=email).first()
            
            if not db_user:
                db_user = DbUser(id=uuid.uuid4(), email=email)

            db_user.email = email
            db_user.first_name = first_name
            db_user.last_name = last_name
            db_user.middle_name = middle_name
            db_user.age = age
            db_user.contact_number = contact_number
            if birthdate:
                db_user.birthdate = birthdate
            db_user.gender = gender
            db_user.marital_status = marital_status
            db_user.religion = religion
            db_user.birthplace = birthplace
            db_user.purok = purok
            db_user.city = city

            # --- AVATAR UPLOAD LOGIC ---
            if "avatar" in request.FILES:
                print("DEBUG: Avatar file detected in request.FILES")
                avatar_file = request.FILES["avatar"]
                
                # Upload to Cloudinary
                uploaded_url = upload_to_cloudinary(avatar_file, folder=f"profiles/{auth_u.id}")
                
                if uploaded_url:
                    print(f"DEBUG: Saving URL to database: {uploaded_url}")
                    db_user.avatar_url = uploaded_url
                else:
                    print("DEBUG: Cloudinary returned None")
                    messages.warning(request, "Profile picture upload failed. Check server logs.")
            # ---------------------------

            db_user.save()
            print("DEBUG: Database saved successfully.")

            messages.success(request, "Profile updated successfully.")
            user_data = get_authed_user(request)

        except Exception as e:
            logger.error(f"profile_view: Update error: {str(e)}")
            messages.error(request, f"An error occurred: {str(e)}")

    response = render(request, "mycebu_app/pages/profile.html", {"user": user_data})
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@csrf_exempt
def chat_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user = get_authed_user(request)
    if not user:
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
        
        if not bot_message:
            bot_message = "I'm having trouble connecting to my AI brain right now. Can you try asking again?"

        return JsonResponse({
            'success': True,
            'message': bot_message
        })

    except Exception as e:
        logger.error(f"chat_view: Error: {str(e)}")
        return JsonResponse({'error': f'Failed to process request: {str(e)}'}, status=500)

def chatbot_page(request):
    user = get_authed_user(request)
    if not user:
        return redirect("login")
    
    response = render(request, 'mycebu_app/test.html', {"user": user})
    return response
                    
def landing_view(request, tab='landing'):
    user = get_authed_user(request)
    if tab == 'dashboard' and not user:
        return redirect("login")
    
    if request.session.pop('just_logged_in', False):
        messages.success(request, "Welcome back, you are now logged in.")

    context = {
        'current_tab': tab,
        'authed_user': user,
        'user': user,
        'services_data': None,
        'service_selected': None,
    }

    if tab == 'services':
        services_list = _load_services_data()
        for service in services_list:
            steps = service.get("steps", [])
            step_details = service.get("stepDetails", [])
            combined_steps = []
            for i, step in enumerate(steps):
                detail = step_details[i] if i < len(step_details) else f"Additional information about step {i + 1} will appear here."
                combined_steps.append({"step": step, "detail": detail})
            service["combined_steps"] = combined_steps

            forms = service.get("forms", [])
            downloads = service.get("formsDownload", [])
            pairs = []
            for i, name in enumerate(forms):
                link = downloads[i] if i < len(downloads) and downloads[i] else None
                pairs.append({"name": name, "link": link})
            service["forms_with_links"] = pairs
            
        selected_id = request.GET.get("id")
        service_selected = None
        if selected_id:
            service_selected = next((s for s in services_list if s.get("id") == selected_id), None)

        context.update({
            'services_data': services_list,
            'service_selected': service_selected,
        })

    if tab == 'directory':
        payload = _load_directory_data()
        officials_all = payload.get("officials", [])
        positions = payload.get("positions", [])
        districts = payload.get("districts", [])
        department_offices = payload.get("departmentOffices", [])
        emergency_contacts = payload.get("emergencyContacts", [])

        q = (request.GET.get("q", "") or "").lower()
        position = request.GET.get("position", "all")
        district = request.GET.get("district", "all")

        def match(o):
            name_pos = f"{o.get('name','')} {o.get('position','')}".lower()
            if q and q not in name_pos: return False
            if position != "all" and o.get("position") != position: return False
            if district != "all" and o.get("district") != district: return False
            return True

        officials = [o for o in officials_all if match(o)]

        context.update({
            "officials": officials,
            "positions": positions,
            "districts": districts,
            "department_offices": department_offices,
            "emergency_contacts": emergency_contacts,
            "q": q,
            "position": position,
            "district": district,
        })

    if tab == 'ordinances':
        query = request.GET.get("q", "").strip()
        category_filter = request.GET.get("category", "")
        author_filter = request.GET.get("author", "")

        # Fetch using Django ORM
        qs = Ordinance.objects.all()

        if query:
            qs = qs.filter(
                Q(name_or_ordinance__icontains=query) |
                Q(author__icontains=query) |
                Q(ordinance_number__icontains=query)
            )
        
        if category_filter:
            qs = qs.filter(category=category_filter)
        
        if author_filter:
            qs = qs.filter(author=author_filter)

        ordinances_data = list(qs.values())

        # Get distinct lists for filters
        categories_list = sorted(list(Ordinance.objects.exclude(category__isnull=True).values_list('category', flat=True).distinct()))
        authors_list = sorted(list(Ordinance.objects.exclude(author__isnull=True).values_list('author', flat=True).distinct()))

        context.update({
            "ordinances_data": ordinances_data,
            "categories_list": categories_list,
            "authors_list": authors_list,
        })

    try:
        response = render(request, f"mycebu_app/pages/{tab}.html", context)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    except TemplateDoesNotExist:
        response = render(request, "mycebu_app/pages/coming_soon.html", context)
        return response


def apply_permit_view(request, service: str):
    user = get_authed_user(request)
    if not user:
        return redirect("login")

    svc = _get_service_by_id(service)
    if not svc:
        return HttpResponse("Service not found", status=404)

    existing_app_id = None
    try:
        # Django ORM Query
        in_progress = ServiceApplication.objects.filter(
            user_id=user["id"],
            service_type=service
        ).filter(
            Q(progress__gt=0) | Q(step_index__gt=0)
        ).order_by('-updated_at').first()

        if in_progress:
            existing_app_id = in_progress.id
    except Exception as e:
        logger.debug("apply_permit_view: error checking service_applications: %s", e)

    return render(request, "mycebu_app/pages/apply_permit.html", {
        "authed_user": user,
        "user": user,
        "service": svc,
        "existing_app_id": existing_app_id,
        "current_tab": "services",
    })


@csrf_exempt
@require_POST
def start_service_application(request, service: str):
    user = get_authed_user(request)
    if not user:
        return JsonResponse({"success": False, "error": "Not authenticated"}, status=401)

    try:
        body = json.loads(request.body or "{}")
    except Exception:
        body = {}

    restart = bool(body.get("restart", False))
    reference = body.get("reference_number") or f"{service.upper()}-{int(time.time())}"

    # Lookup existing via ORM
    existing = ServiceApplication.objects.filter(
        user_id=user["id"],
        service_type=service
    ).first()

    if restart and existing:
        try:
            existing.progress = 0
            existing.step_index = 0
            existing.reference_number = reference
            existing.updated_at = timezone.now()
            existing.save()
            return JsonResponse({"success": True, "application_id": existing.id, "restarted": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": "Failed to restart application"}, status=500)

    # reuse in-progress if exists and not restarting
    if not restart and existing:
        if (existing.progress or 0) > 0 or (existing.step_index or 0) > 0:
            return JsonResponse({"success": True, "application_id": existing.id, "existing": True})

    # create new record (or reuse zeroed existing)
    try:
        if existing and (existing.progress or 0) == 0 and (existing.step_index or 0) == 0:
            existing.updated_at = timezone.now()
            existing.reference_number = reference
            existing.save()
            return JsonResponse({"success": True, "application_id": existing.id, "existing": True})

        new_app = ServiceApplication.objects.create(
            user_id=user["id"],
            service_type=service,
            reference_number=reference,
            progress=0,
            step_index=0,
            created_at=timezone.now(),
            updated_at=timezone.now()
        )
        return JsonResponse({"success": True, "application_id": new_app.id})

    except Exception as e:
        logger.error("start_service_application: create error: %s", e)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_POST
def update_service_application(request, service: str, app_id):
    user = get_authed_user(request)
    if not user:
        return JsonResponse({"success": False, "error": "Not authenticated"}, status=401)

    try:
        data = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    mark_completed = bool(data.get("mark_completed", False))
    new_step = data.get("step_index")

    svc = _get_service_by_id(service)
    total_steps = len(svc.get("steps", [])) if svc else 1

    try:
        app = ServiceApplication.objects.get(id=app_id)

        if mark_completed:
            app.step_index = 0
            app.progress = 0
            app.updated_at = timezone.now()
            app.save()
            return JsonResponse({"success": True, "progress": 0, "completed": True})

        if new_step is None:
            return JsonResponse({"success": False, "error": "step_index required"}, status=400)

        new_step = int(new_step)
        if new_step < 0: new_step = 0
        if new_step >= total_steps: new_step = total_steps - 1

        progress = int(((new_step + 1) / max(total_steps, 1)) * 100)

        app.step_index = new_step
        app.progress = progress
        app.updated_at = timezone.now()
        app.save()

        return JsonResponse({"success": True, "progress": progress, "step_index": new_step})
    except ServiceApplication.DoesNotExist:
         return JsonResponse({"success": False, "error": "Application not found"}, status=404)
    except Exception as e:
        logger.error("update_service_application: %s", e)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def permit_progress_view(request, service: str, app_id):
    user = get_authed_user(request)
    if not user:
        return redirect("login")

    try:
        app_obj = ServiceApplication.objects.get(id=app_id)
        # Manually constructing dict to match previous context structure
        application = {
            "id": app_obj.id,
            "reference_number": app_obj.reference_number,
            "progress": app_obj.progress,
            "step_index": app_obj.step_index,
            "updated_at": app_obj.updated_at,
            "service_type": app_obj.service_type
        }
        
        svc = _get_service_by_id(service)
        return render(request, "mycebu_app/pages/permit_progress.html", {
            "authed_user": user,
            "user": user,
            "service": svc,
            "app": application,
            "current_tab": "services",
        })
    except ServiceApplication.DoesNotExist:
        return HttpResponse("Application not found", status=404)
    except Exception as e:
        logger.error(f"permit_progress_view: {e}")
        return HttpResponse("Error loading application", status=500)


@csrf_exempt
@require_POST
def submit_complaint_view(request):
    user = get_authed_user(request)
    if not user or not user.get("id"):
        return JsonResponse({"success": False, "error": "Not authenticated"}, status=401)

    try:
        # Accept both JSON and form-data
        if request.content_type and "application/json" in request.content_type:
            payload = json.loads(request.body)
        else:
            payload = request.POST

        category = (payload.get("category") or "").strip()
        subcategory = payload.get("subcategory")
        subject = (payload.get("subject") or "").strip()
        location = (payload.get("location") or "").strip()
        description = (payload.get("description") or "").strip()
        is_anonymous = payload.get("is_anonymous") in (True, "true", "True", 1)

        name = payload.get("name", "").strip() if not is_anonymous else None
        email = payload.get("email", "").strip() if not is_anonymous else None
        phone = payload.get("phone", "").strip() if not is_anonymous else None

        attachments = payload.get("attachments", [])

        # Fallback: if no JSON attachments, try form-data files and upload to Cloudinary
        if not attachments:
            files = request.FILES.getlist("cmp-files") or request.FILES.getlist("attachments")
            attachments = []
            for f in files:
                # Upload to Cloudinary
                uploaded_url = upload_to_cloudinary(f, folder=f"complaints/{user['id']}")
                if uploaded_url:
                    attachments.append({
                        "name": f.name,
                        "url": uploaded_url,
                        "size": f.size,
                        "content_type": f.content_type,
                    })

        errors = {}
        if not category: errors["category"] = "Required"
        if not subject: errors["subject"] = "Required"
        if not location: errors["location"] = "Required"
        if not description: errors["description"] = "Required"
        if not is_anonymous and not (name or email or phone):
            errors["identity"] = "Provide at least one contact if not anonymous"

        if errors:
            return JsonResponse({"success": False, "errors": errors}, status=400)

        # Create using ORM
        complaint = Complaint.objects.create(
            user_id=user["id"],
            category=category,
            subcategory=subcategory or None,
            subject=subject,
            location=location,
            description=description,
            is_anonymous=is_anonymous,
            name=name,
            email=email,
            phone=phone,
            attachments=attachments if attachments else None,
            status="Submitted",
            created_at=timezone.now(),
            updated_at=timezone.now()
        )

        return JsonResponse({
            "success": True,
            "complaint": {
                "id": complaint.id,
                "status": complaint.status,
                "created_at": complaint.created_at,
                "attachments": complaint.attachments,
            }
        })

    except Exception as e:
        logger.error(f"submit_complaint_view error: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_GET
def list_complaints_view(request):
    user = get_authed_user(request)
    if not user or not user.get("id"):
        return JsonResponse({"success": False, "error": "Not authenticated"}, status=401)

    try:
        complaints = Complaint.objects.filter(user_id=user["id"]).order_by('-created_at').values(
            "id", "category", "subcategory", "subject", "status", "created_at", "location"
        )

        items = list(complaints)
        return JsonResponse({"success": True, "items": items})
    except Exception as e:
        logger.error(f"list_complaints_view: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_GET
def complaint_detail_view(request, complaint_id):
    user = get_authed_user(request)
    if not user or not user.get("id"):
        return JsonResponse({"success": False, "error": "Not authenticated"}, status=401)

    try:
        c = Complaint.objects.get(id=complaint_id, user_id=user["id"])
        
        return JsonResponse({
            "success": True,
            "complaint": {
                "id": c.id,
                "category": c.category,
                "subcategory": c.subcategory,
                "subject": c.subject,
                "location": c.location,
                "description": c.description,
                "is_anonymous": c.is_anonymous,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "status": c.status,
                "attachments": c.attachments,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
        })
    except Complaint.DoesNotExist:
        return JsonResponse({"success": False, "error": "Complaint not found"}, status=404)
    except Exception as e:
        logger.error(f"complaint_detail_view: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_POST
def update_complaint_status_view(request, complaint_id):
    user = get_authed_user(request)
    if not user or not user.get("id"):
        return JsonResponse({"success": False, "error": "Not authenticated"}, status=401)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON body"}, status=400)

    new_status = (payload.get("status") or "").strip()
    if not new_status:
        return JsonResponse({"success": False, "error": "Status is required"}, status=400)

    try:
        updated_count = Complaint.objects.filter(id=complaint_id, user_id=user["id"]).update(
            status=new_status,
            updated_at=timezone.now()
        )

        if updated_count == 0:
            return JsonResponse({"success": False, "error": "Complaint not found or not owned by user"}, status=404)

        c = Complaint.objects.get(id=complaint_id)
        return JsonResponse({
            "success": True,
            "complaint": {
                "id": c.id,
                "status": c.status,
                "updated_at": c.updated_at,
            }
        })
    except Exception as e:
        logger.error(f"update_complaint_status_view: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)
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
from .models import Complaint, Ordinance, ServiceApplication, Service, Official, Department, EmergencyContact, Service

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
    """
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_STORAGE['CLOUD_NAME'],
        api_key=settings.CLOUDINARY_STORAGE['API_KEY'],
        api_secret=settings.CLOUDINARY_STORAGE['API_SECRET']
    )
    
    upload_result = cloudinary.uploader.upload(
        file_obj,
        folder=f"mycebu/{folder}",
        resource_type="auto"
    )
    
    return upload_result.get("secure_url")

# ==========================================
# AUTH & USER HELPERS
# ==========================================

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
        user_id = db_user.id 

    display_name = f"{auth_user.first_name} {auth_user.last_name}".strip()
    if not display_name:
        display_name = auth_user.username

    # Avatar logic
    avatar_url = f"https://ui-avatars.com/api/?name={auth_user.username}&background=random"
    if db_user and db_user.avatar_url:
        avatar_url = db_user.avatar_url

    return {
        "id": user_id,
        "username": auth_user.username,
        "email": auth_user.email,
        "first_name": auth_user.first_name,
        "last_name": auth_user.last_name,
        "display_name": display_name,
        "avatar_url": avatar_url,
        "role": db_user.role if db_user else "user",
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

def _get_service_by_id(service_id):
    """Helper to fetch a specific service from DB by its string ID (e.g., 'business-permit')"""
    return Service.objects.filter(service_id=service_id).values().first()

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
        if user.get('role') == 'admin':
            return redirect("landing_tab", tab="admin_dashboard")
        return redirect("landing_tab", tab="dashboard")
    return redirect("landing_tab", tab="landing")

def landing_view(request, tab='landing'):
    user = get_authed_user(request)
    
    if tab in ['dashboard', 'admin_dashboard'] and not user:
        return redirect("login")
    
    # Security Check for Admin Tab
    if tab == 'admin_dashboard':
        if user.get('role') != 'admin':
            return redirect("landing_tab", tab="dashboard")

    if request.session.pop('just_logged_in', False):
        messages.success(request, "Welcome back, you are now logged in.")

    context = {
        'current_tab': tab,
        'authed_user': user,
        'user': user,
        'services_data': None,
        'service_selected': None,
    }

    # ==========================
    # ADMIN DASHBOARD TAB
    # ==========================
    if tab == 'admin_dashboard':
        # 1. Fetch Stats from DB
        total_complaints = Complaint.objects.count()
        pending_complaints = Complaint.objects.filter(status='Submitted').count()
        total_users = DbUser.objects.count()

        # 2. Fetch Data directly from DB
        all_complaints = Complaint.objects.all().order_by('-created_at')
        services_list = Service.objects.all().order_by('title')
        officials_list = Official.objects.all().order_by('name')
        ordinances_list = Ordinance.objects.all().order_by('-created_at')

        context.update({
            "admin_stats": {
                "total_complaints": total_complaints,
                "pending_complaints": pending_complaints,
                "total_users": total_users
            },
            "admin_complaints": all_complaints,
            "admin_services": services_list, 
            "admin_officials": officials_list,
            "admin_ordinances": ordinances_list,
        })

    # ==========================
    # SERVICES TAB (Public)
    # ==========================
    elif tab == 'services':
        # Fetch services from DB
        services_qs = Service.objects.all().order_by('title')
        
        # Convert QuerySet to list of dicts to process JSON fields easily
        # or process them as objects. Here we stick to objects but handle JSON logic.
        services_processed = []
        
        for svc in services_qs:
            # Prepare Steps
            # Note: JSONField automatically deserializes to Python lists/dicts
            steps = svc.steps if svc.steps else []
            step_details = svc.step_details if svc.step_details else []
            
            combined_steps = []
            for i, step in enumerate(steps):
                detail = step_details[i] if i < len(step_details) else ""
                combined_steps.append({"step": step, "detail": detail})
            
            # Prepare Forms
            forms = svc.forms if svc.forms else []
            downloads = svc.forms_download if svc.forms_download else []
            
            forms_with_links = []
            for i, name in enumerate(forms):
                link = downloads[i] if i < len(downloads) and downloads[i] else None
                forms_with_links.append({"name": name, "link": link})

            # Create a display object (using __dict__ copy or similar approach)
            svc_display = svc
            svc_display.combined_steps = combined_steps
            svc_display.forms_with_links = forms_with_links
            services_processed.append(svc_display)

        context['services_data'] = services_processed
        
        selected_id = request.GET.get("id")
        if selected_id:
            context['service_selected'] = next((s for s in services_processed if s.service_id == selected_id), None)

    # ==========================
    # DIRECTORY TAB (Public)
    # ==========================
    elif tab == 'directory':
        # Fetch from DB
        officials_all = Official.objects.all().order_by('name')
        department_offices = Department.objects.all().order_by('name')
        emergency_contacts = EmergencyContact.objects.all()
        
        # Get unique values for filters
        positions = sorted(list(set(Official.objects.values_list('position', flat=True))))
        districts = sorted(list(set(Official.objects.exclude(district__isnull=True).exclude(district="").values_list('district', flat=True))))

        q = (request.GET.get("q", "") or "").lower()
        position_filter = request.GET.get("position", "all")
        district_filter = request.GET.get("district", "all")

        # Filtering Logic
        officials_filtered = []
        for o in officials_all:
            name_pos = f"{o.name} {o.position}".lower()
            
            # Text search
            if q and q not in name_pos:
                continue
            # Position filter
            if position_filter != "all" and o.position != position_filter:
                continue
            # District filter
            if district_filter != "all" and o.district != district_filter:
                continue
            
            officials_filtered.append(o)

        context.update({
            "officials": officials_filtered,
            "positions": positions,
            "districts": districts,
            "department_offices": department_offices,
            "emergency_contacts": emergency_contacts,
            "q": q,
            "position": position_filter,
            "district": district_filter,
        })

    # ==========================
    # ORDINANCES TAB (Public)
    # ==========================
    elif tab == 'ordinances':
        query = request.GET.get("q", "").strip()
        category_filter = request.GET.get("category", "")
        author_filter = request.GET.get("author", "")

        qs = Ordinance.objects.all().order_by('-date_of_enactment', '-created_at')

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

        categories_list = sorted(list(Ordinance.objects.exclude(category__isnull=True).values_list('category', flat=True).distinct()))
        authors_list = sorted(list(Ordinance.objects.exclude(author__isnull=True).values_list('author', flat=True).distinct()))

        context.update({
            "ordinances_data": ordinances_data,
            "categories_list": categories_list,
            "authors_list": authors_list,
        })

    try:
        return render(request, f"mycebu_app/pages/{tab}.html", context)
    except TemplateDoesNotExist:
        return render(request, "mycebu_app/pages/coming_soon.html", context)

# ==========================================
# ADMIN ACTIONS (DB CONNECTED)
# ==========================================

@csrf_exempt
@require_POST
def admin_action_view(request, action_type):
    user = get_authed_user(request)
    if not user or user.get('role') != 'admin':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    try:
        if action_type == 'add_service':
            data = json.loads(request.body)
            # Create directly in DB
            # Note: For JSONField (requirements, steps, etc), pass the Python list directly. 
            # Do NOT use json.dumps() if your model uses models.JSONField.
            Service.objects.create(
                service_id=data['service_id'],
                icon=data.get('icon', 'file'),
                title=data['title'],
                description=data['description'],
                color=data.get('color', 'primary'),
                requirements=data.get('requirements', []),
                steps=data.get('steps', []),
                step_details=data.get('step_details', []),
                additional_info=data.get('additional_info') or {},
                forms=data.get('forms', []),
                forms_download=data.get('forms_download', []),
            )
            return JsonResponse({'success': True})

        elif action_type == 'edit_service':
            data = json.loads(request.body)
            svc = Service.objects.get(id=data['id'])
            
            svc.service_id = data['service_id']
            svc.title = data['title']
            svc.description = data['description']
            svc.icon = data.get('icon', svc.icon)
            svc.color = data.get('color', svc.color)
            
            # Update JSON fields
            svc.requirements = data.get('requirements', [])
            svc.steps = data.get('steps', [])
            svc.step_details = data.get('step_details', [])
            svc.additional_info = data.get('additional_info') or {}
            svc.forms = data.get('forms', [])
            svc.forms_download = data.get('forms_download', [])
            
            svc.save()
            return JsonResponse({'success': True})

        elif action_type == 'delete_service':
            data = json.loads(request.body)
            Service.objects.filter(id=data['id']).delete()
            return JsonResponse({'success': True})

        elif action_type == 'add_official':
            data = json.loads(request.body)
            Official.objects.create(
                name=data['name'],
                position=data['position'],
                office=data.get('office', ''),
                district=data.get('district', ''),
                email=data.get('email', ''),
                phone=data.get('phone', ''),
                initials=data.get('initials', ''.join([n[0] for n in data['name'].split() if n])[:2].upper()),
                photo=data.get('photo', '')
            )
            return JsonResponse({'success': True})

        elif action_type == 'edit_official':
            data = json.loads(request.body)
            off = Official.objects.get(id=data['id'])
            off.name = data['name']
            off.position = data['position']
            off.office = data.get('office', off.office)
            off.district = data.get('district', off.district)
            off.email = data.get('email', off.email)
            off.phone = data.get('phone', off.phone)
            off.initials = data.get('initials', off.initials)
            off.photo = data.get('photo', off.photo)
            off.save()
            return JsonResponse({'success': True})

        elif action_type == 'delete_official':
            data = json.loads(request.body)
            Official.objects.filter(id=data['id']).delete()
            return JsonResponse({'success': True})

        elif action_type == 'add_ordinance':
            # Ordinances involve files, so likely FormData (request.POST/FILES)
            data = request.POST
            pdf_url = ""
            if 'pdf_file' in request.FILES:
                pdf_url = upload_to_cloudinary(request.FILES['pdf_file'], folder="ordinances")
            
            Ordinance.objects.create(
                category=data.get('category', 'General'),
                ordinance_number=data.get('ordinance_number', ''),
                name_or_ordinance=data.get('title', ''),
                author=data.get('author', ''),
                date_of_enactment=data.get('date_enacted') or None,
                pdf_file_path=pdf_url,
                created_at=timezone.now()
            )
            return JsonResponse({'success': True})

        elif action_type == 'delete_ordinance':
            data = json.loads(request.body)
            Ordinance.objects.filter(id=data['id']).delete()
            return JsonResponse({'success': True})

        elif action_type == 'update_complaint':
            data = json.loads(request.body)
            Complaint.objects.filter(id=data['id']).update(
                status=data['status'],
                updated_at=timezone.now()
            )
            return JsonResponse({'success': True})

        return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)

    except Service.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Service not found'}, status=404)
    except Official.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Official not found'}, status=404)
    except Exception as e:
        logger.error(f"Admin Action Error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ==========================================
# OTHER VIEWS (Profile, Chat, Permit, etc.)
# ==========================================

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
                avatar_file = request.FILES["avatar"]
                uploaded_url = upload_to_cloudinary(avatar_file, folder=f"profiles/{auth_u.id}")
                if uploaded_url:
                    db_user.avatar_url = uploaded_url
                else:
                    messages.warning(request, "Profile picture upload failed. Check server logs.")
            # ---------------------------

            db_user.save()
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

        context_data = []
        q_term = prompt.strip()

        services = Service.objects.filter(
            Q(title__icontains=q_term) | 
            Q(description__icontains=q_term)
        )[:3]
        for s in services:
            context_data.append(f"[Service] {s.title}: {s.description}")

        officials = Official.objects.filter(
            Q(name__icontains=q_term) | 
            Q(position__icontains=q_term) |
            Q(office__icontains=q_term)
        )[:5]
        for o in officials:
            context_data.append(f"[Official] {o.name} ({o.position}) - {o.office}. Phone: {o.phone}")

        ordinances = Ordinance.objects.filter(
            Q(name_or_ordinance__icontains=q_term) |
            Q(ordinance_number__icontains=q_term)
        )[:3]
        for o in ordinances:
            context_data.append(f"[Ordinance] {o.ordinance_number} - {o.name_or_ordinance} by {o.author}")

        if any(x in q_term.lower() for x in ['emergency', 'hotline', 'police', 'fire', 'help']):
            emergencies = EmergencyContact.objects.all()
            for e in emergencies:
                nums = ", ".join(e.numbers) if isinstance(e.numbers, list) else str(e.numbers)
                context_data.append(f"[Emergency] {e.service}: {nums}")

        context_str = "\n".join(context_data)
        
        if not context_str:
            system_instruction = (
                "You are the Cebu City AI assistant. The user asked a question, but I found NO matching records "
                "in the database for Services, Officials, or Ordinances. "
                "Politely tell the user you couldn't find specific information in the system records."
            )
        else:
            system_instruction = (
                "You are the Cebu City AI assistant. Answer the user's question using ONLY the following database records. "
                "Do not make up information. If the answer is not in the records, say you don't know.\n\n"
                f"--- DATABASE RECORDS ---\n{context_str}\n------------------------"
            )

        api_url = "https://router.huggingface.co/novita/v3/openai/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "model": "deepseek/deepseek-v3-0324",
            "stream": False,
            "temperature": 0.2 
        }

        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        api_response = response.json()

        bot_message = api_response.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        
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
    return render(request, 'mycebu_app/test.html', {"user": user})

def apply_permit_view(request, service: str):
    user = get_authed_user(request)
    if not user:
        return redirect("login")

    svc = _get_service_by_id(service)
    if not svc:
        return HttpResponse("Service not found", status=404)

    existing_app_id = None
    try:
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

    if not restart and existing:
        if (existing.progress or 0) > 0 or (existing.step_index or 0) > 0:
            return JsonResponse({"success": True, "application_id": existing.id, "existing": True})

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
    # Handle both dict (if fetched via values()) and object
    if isinstance(svc, dict):
        steps_list = svc.get("steps", [])
    else:
        steps_list = svc.steps if svc else []
        
    total_steps = len(steps_list) if steps_list else 1

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

        if not attachments:
            files = request.FILES.getlist("cmp-files") or request.FILES.getlist("attachments")
            attachments = []
            for f in files:
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
        return JsonResponse({"success": True, "items": list(complaints)})
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
    
@require_GET
def service_list_api(request):
    """
    API endpoint to fetch all services from the database for the frontend search.
    """
    try:
        services = Service.objects.all().order_by('title')
        data = []
        
        for svc in services:
            data.append({
                # Map DB fields to the keys your frontend JS expects
                "id": svc.service_id,       # Important: This is the slug (e.g., 'business-permit')
                "title": svc.title,
                "description": svc.description,
                "icon": svc.icon,           # Optional, if you want to use icons later
            })
            
        return JsonResponse({"services": data})
    except Exception as e:
        return JsonResponse({"services": [], "error": str(e)}, status=500)
    
@require_GET
def directory_list_api(request):
    try:
        # 1. Officials
        officials_qs = Official.objects.all().order_by('name')
        officials_data = []
        positions = set()
        districts = set()

        for o in officials_qs:
            # Handle potential None values safely
            pos = o.position or "Official"
            dist = o.district or ""
            
            if pos: positions.add(pos)
            if dist: districts.add(dist)

            officials_data.append({
                "id": str(o.id),
                "name": o.name or "Unknown Name",
                "position": pos,
                "office": o.office or "",
                "district": dist,
                # IMPORTANT: Return empty string if no photo, never None
                "photo": o.photo if o.photo else "", 
                "initials": o.initials or (o.name[:2].upper() if o.name else "??"),
                "email": o.email or "",
                "phone": o.phone or ""
            })

        # 2. Departments
        dept_qs = Department.objects.all().order_by('name')
        dept_data = []
        for d in dept_qs:
            # Ensure contact_details is a dictionary
            contacts = d.contact_details if isinstance(d.contact_details, dict) else {}
            dept_data.append({
                "id": str(d.id),
                "name": d.name or "Unnamed Office",
                "head": d.head or "",
                "emails": contacts.get('emails', []) if contacts else [],
                "phones": contacts.get('phones', []) if contacts else []
            })

        # 3. Hotlines
        hotline_qs = EmergencyContact.objects.all().order_by('service')
        hotline_data = []
        for h in hotline_qs:
            # Ensure numbers is a list
            nums = h.numbers if isinstance(h.numbers, list) else [h.numbers] if h.numbers else []
            hotline_data.append({
                "id": str(h.id),
                "service": h.service or "Service",
                "numbers": nums
            })

        return JsonResponse({
            "success": True,
            "officials": officials_data,
            "offices": dept_data,
            "hotlines": hotline_data,
            "filters": {
                "positions": sorted(list(positions)),
                "districts": sorted(list(districts))
            }
        })

    except Exception as e:
        print(f"API Error: {e}") 
        return JsonResponse({"success": False, "error": str(e)}, status=500)
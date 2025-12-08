import os
import uuid
import json
import time
import logging
import re
import google.generativeai as genai
import requests
from pathlib import Path
from datetime import datetime

# Cloudinary Imports
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Django Imports
from django.db import connection
from django.db.models import Q, F
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
from django.core.paginator import Paginator
from collections import defaultdict

# Auth Imports
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User as DjangoAuthUser

# === MODEL IMPORTS ===
from .models import Complaint, Ordinance, ServiceApplication, Service, Official, Department, EmergencyContact, Service, ChatHistory

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


try:
    if settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)
    else:
        logger.error("GEMINI_API_KEY not found in settings.")
except Exception as e:
    logger.error(f"Failed to configure Gemini: {e}")
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
    Linked by Email. Creates DbUser if it doesn't exist to ensure consistency.
    """
    if not request.user.is_authenticated:
        return None

    auth_user = request.user
    
    # 2. Find the corresponding record in your custom 'users' table
    db_user = DbUser.objects.filter(email=auth_user.email).first()

    # FIXED: Create DbUser if it doesn't exist (ensures UUID id and basic fields)
    if not db_user:
        try:
            db_user = DbUser(
                email=auth_user.email,
                first_name=auth_user.first_name or "",
                last_name=auth_user.last_name or "",
                created_at=timezone.now(),
                role='user'
            )
            db_user.save()
        except Exception as e:
            if "violates foreign key constraint" in str(e):
                # DEV FIX: Auto-drop bad constraint
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_id_fkey;")
                # Retry
                db_user = DbUser(
                    email=auth_user.email,
                    first_name=auth_user.first_name or "",
                    last_name=auth_user.last_name or "",
                    created_at=timezone.now(),
                    role='user'
                )
                db_user.save()
            else:
                raise

    # 3. Construct the full profile dictionary (unchanged)
    user_id = db_user.id
    display_name = f"{auth_user.first_name} {auth_user.last_name}".strip()
    if not display_name:
        display_name = auth_user.username

    avatar_url = f"https://ui-avatars.com/api/?name={auth_user.username}&background=random"
    if db_user.avatar_url:
        avatar_url = db_user.avatar_url

    return {
        "id": user_id,
        "username": auth_user.username,
        "email": auth_user.email,
        "first_name": auth_user.first_name,
        "last_name": auth_user.last_name,
        "display_name": display_name,
        "avatar_url": avatar_url,
        "role": db_user.role,
        "middle_name": db_user.middle_name,
        "age": db_user.age,
        "birthdate": str(db_user.birthdate) if db_user.birthdate else None,
        "contact_number": db_user.contact_number,
        "gender": db_user.gender,
        "marital_status": db_user.marital_status,
        "religion": db_user.religion,
        "birthplace": db_user.birthplace,
        "purok": db_user.purok,
        "city": db_user.city,
    }

def _get_service_by_id(service_id):
    """Helper to fetch a specific service from DB by its string ID (e.g., 'business-permit')"""
    return Service.objects.filter(service_id=service_id).first()

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
        total_complaints = Complaint.objects.count()
        pending_complaints = Complaint.objects.filter(status='Submitted').count()
        
        try:
            total_users = DbUser.objects.count()
            all_users = DbUser.objects.all().order_by('-created_at')
        except:
            total_users = 0
            all_users = []

        all_complaints = Complaint.objects.all().order_by('-created_at')
        services_list = Service.objects.all().order_by('title')
        officials_list = Official.objects.all().order_by('name')
        ordinances_list = Ordinance.objects.all().order_by('-created_at')
        
        # NEW: Get all permit applications
        all_permits = ServiceApplication.objects.all().order_by('-created_at')
        pending_permits = ServiceApplication.objects.filter(document_status='pending').count()

        context.update({
            "admin_stats": {
                "total_complaints": total_complaints,
                "pending_complaints": pending_complaints,
                "total_users": total_users,
                "pending_permits": pending_permits  # NEW
            },
            "admin_complaints": all_complaints,
            "admin_services": services_list, 
            "admin_officials": officials_list,
            "admin_ordinances": ordinances_list,
            "admin_users": all_users,
            "admin_permits": all_permits,  # NEW
        })

    # ==========================
    # SERVICES TAB (Public)
    # ==========================
    elif tab == 'services':
        services_qs = Service.objects.all().order_by('title')
        
        services_processed = []
        
        # --- ROBUST JSON PARSING ---
        # This function ensures that if the DB returns a String representation of a list/dict, 
        # it is properly converted to a Python object.
        def safe_json_load(value, default):
            if value is None:
                return default
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return default
            # Already a list or dict
            return value

        for svc in services_qs:
            # 1. Parse JSON fields
            svc.requirements = safe_json_load(svc.requirements, [])
            svc.steps = safe_json_load(svc.steps, [])
            svc.step_details = safe_json_load(svc.step_details, [])
            svc.forms = safe_json_load(svc.forms, [])
            svc.forms_download = safe_json_load(svc.forms_download, [])
            svc.additional_info = safe_json_load(svc.additional_info, {})

            # 2. Combine Steps and Details for Display
            combined_steps = []
            steps = svc.steps
            step_details = svc.step_details
            
            for i, step in enumerate(steps):
                # Ensure we don't go out of bounds if details list is shorter
                detail = step_details[i] if i < len(step_details) else ""
                combined_steps.append({"step": step, "detail": detail})
            
            # 3. Combine Forms and Links
            forms_with_links = []
            forms = svc.forms
            downloads = svc.forms_download
            
            for i, name in enumerate(forms):
                link = downloads[i] if i < len(downloads) and downloads[i] else None
                forms_with_links.append({"name": name, "link": link})

            # Attach processed data to object for the template
            svc.combined_steps = combined_steps
            svc.forms_with_links = forms_with_links
            
            services_processed.append(svc)

        context['services_data'] = services_processed
        
        # --- ID MATCHING LOGIC ---
        selected_id = request.GET.get("id")
        if selected_id:
            # We look for the service where service_id (slug) matches the URL param
            context['service_selected'] = next(
                (s for s in services_processed if s.service_id == selected_id), 
                None
            )

    # ==========================
    # DIRECTORY TAB
    # ==========================
    elif tab == 'directory':
        officials_all = Official.objects.all().order_by('name')
        department_offices = Department.objects.all().order_by('name')
        emergency_contacts = EmergencyContact.objects.all()
        
        positions = sorted(list(set(Official.objects.values_list('position', flat=True))))
        districts = sorted(list(set(Official.objects.exclude(district__isnull=True).exclude(district="").values_list('district', flat=True))))

        q = (request.GET.get("q", "") or "").lower()
        position_filter = request.GET.get("position", "all")
        district_filter = request.GET.get("district", "all")

        officials_filtered = []
        for o in officials_all:
            name_pos = f"{o.name} {o.position}".lower()
            if q and q not in name_pos: continue
            if position_filter != "all" and o.position != position_filter: continue
            if district_filter != "all" and o.district != district_filter: continue
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
    # ORDINANCES TAB
    # ==========================
    elif tab == 'ordinances':
        query = request.GET.get("q", "").strip()
        category_filter = request.GET.get("category", "")
        author_filter = request.GET.get("author", "")
        view_all = request.GET.get("view_all", "").strip()
        page = request.GET.get("page", 1)

        qs = Ordinance.objects.all().order_by('name_or_ordinance')

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

        if view_all:
            qs = qs.filter(category=view_all)
            sort = request.GET.get("sort", "")
            if sort == 'newest':
                qs = qs.order_by(F('date_of_enactment').desc(nulls_last=True))
            elif sort == 'oldest':
                qs = qs.order_by(F('date_of_enactment').asc(nulls_last=True))
            elif sort == 'year':
                qs = qs.order_by(F('date_of_enactment__year').desc(nulls_last=True), F('date_of_enactment').desc(nulls_last=True))
            
            paginator = Paginator(qs, 9)
            ordinances_page = paginator.get_page(page)
            ordinances_data = list(ordinances_page.object_list.values())

            context.update({
                "ordinances_data": ordinances_data,
                "view_all": view_all,
                "paginator": paginator,
                "page_obj": ordinances_page,
                "is_paginated": paginator.num_pages > 1,
            })
        else:
            all_ordinances = list(qs.values())
            categories = defaultdict(list)
            for ord in all_ordinances:
                cat = ord['category'] or 'General'
                if len(categories[cat]) < 3:
                    categories[cat].append(ord)
            ordinances_data = []
            for cat, ords in categories.items():
                ordinances_data.extend(ords)

            context.update({
                "ordinances_data": ordinances_data,
                "view_all": None,
            })

        categories_list = sorted(list(Ordinance.objects.exclude(category__isnull=True).values_list('category', flat=True).distinct()))
        authors_list = sorted(list(Ordinance.objects.exclude(author__isnull=True).values_list('author', flat=True).distinct()))

        context.update({
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
            service = Service.objects.create(
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
            return JsonResponse({'success': True, 'new_id': str(service.id)})

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
            official = Official.objects.create(
                name=data['name'],
                position=data['position'],
                office=data.get('office', ''),
                district=data.get('district', ''),
                email=data.get('email', ''),
                phone=data.get('phone', ''),
                initials=data.get('initials', ''.join([n[0] for n in data['name'].split() if n])[:2].upper()),
                photo=data.get('photo', '')
            )
            return JsonResponse({'success': True, 'new_id': str(official.id)})

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
            
            ordinance = Ordinance.objects.create(
                category=data.get('category', 'General'),
                ordinance_number=data.get('ordinance_number', ''),
                name_or_ordinance=data.get('title', ''),
                author=data.get('author', ''),
                date_of_enactment=data.get('date_enacted') or None,
                pdf_file_path=pdf_url,
                created_at=timezone.now()
            )
            return JsonResponse({'success': True, 'new_id': str(ordinance.id)})

        elif action_type == 'delete_ordinance':
            data = json.loads(request.body)
            Ordinance.objects.filter(id=data['id']).delete()
            return JsonResponse({'success': True})
            
        elif action_type == 'delete_user':
            data = json.loads(request.body)
            user_id = data.get('id')
            
            # Find the Custom User
            try:
                db_user = DbUser.objects.get(id=user_id)
                email = db_user.email
                
                # If there's an email, try to find and delete the Django Auth User (Login)
                if email:
                    DjangoAuthUser.objects.filter(email=email).delete()
                
                # Delete the custom profile
                db_user.delete()
                
                return JsonResponse({'success': True})
            except DbUser.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'User not found'}, status=404)

        elif action_type == 'update_complaint':
            data = json.loads(request.body)
            new_status = data['status']
            
            # Optional: Add validation for new statuses
            VALID_COMPLAINT_STATUSES = ['Pending', 'In Progress', 'Resolved', 'Cancelled']
            if new_status not in VALID_COMPLAINT_STATUSES:
                return JsonResponse({'success': False, 'error': f'Invalid status: {new_status}'}, status=400)

            Complaint.objects.filter(id=data['id']).update(
                status=new_status,
                updated_at=timezone.now()
            )
            return JsonResponse({'success': True})
        
        # NEW: Update Permit Status
        elif action_type == 'update_permit_status':
            data = json.loads(request.body)
            permit_id = data.get('id')
            new_status = data.get('document_status')
            admin_notes = data.get('admin_notes', '')
            
            try:
                permit = ServiceApplication.objects.get(id=permit_id)
                permit.document_status = new_status
                permit.admin_notes = admin_notes
                permit.updated_at = timezone.now()
                
                if new_status == 'verified':
                    permit.completed_at = timezone.now()
                
                permit.save()
                return JsonResponse({'success': True})
            except ServiceApplication.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Permit application not found'}, status=404)

        return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)

    except Service.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Service not found'}, status=404)
    except Official.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Official not found'}, status=404)
    except ServiceApplication.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Permit application not found'}, status=404)
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

    if request.method == "POST":
        try:
            # Get values safely
            first_name = request.POST.get("first_name", "").strip()
            middle_name = request.POST.get("middle_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()
            email = request.POST.get("email", "").strip()

            # THESE WERE MISSING OR EMPTY BECAUSE OF DISABLED FIELD
            city = request.POST.get("city", "").strip()
            purok = request.POST.get("purok", "").strip()

            # Get current auth user and db user
            auth_user = request.user
            db_user = DbUser.objects.filter(email=auth_user.email).first()

            # Update Django Auth User
            auth_user.first_name = first_name
            auth_user.last_name = last_name
            auth_user.email = email
            auth_user.save()

            # Update Custom DbUser
            if db_user:
                db_user.first_name = first_name
                db_user.middle_name = middle_name
                db_user.last_name = last_name
                db_user.email = email
                db_user.city = city or None
                db_user.purok = purok or None

                db_user.contact_number = request.POST.get("contact_number", "").strip()
                db_user.gender = request.POST.get("gender")
                db_user.marital_status = request.POST.get("marital_status")
                db_user.religion = request.POST.get("religion", "").strip()
                db_user.birthplace = request.POST.get("birthplace", "").strip()

                age = request.POST.get("age")
                if age and age.isdigit():
                    db_user.age = int(age)
                else:
                    db_user.age = None

                bday = request.POST.get("birthdate")
                if bday:
                    try:
                        db_user.birthdate = datetime.strptime(bday, '%Y-%m-%d').date()
                    except:
                        pass

                # Avatar upload
                if "avatar" in request.FILES:
                    file = request.FILES["avatar"]
                    url = upload_to_cloudinary(file, folder=f"profiles/{auth_user.id}")
                    if url:
                        db_user.avatar_url = url

                db_user.save()

            messages.success(request, "Profile updated successfully!")
            # Force refresh user data
            user_data = get_authed_user(request)

        except Exception as e:
            logger.error(f"Profile update failed: {e}")
            messages.error(request, f"Update failed: {e}")

    return render(request, "mycebu_app/pages/profile.html", {"user": user_data})

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
        existing.progress = 0
        existing.step_index = 0
        existing.document_status = 'draft'  # <--- CHANGE THIS (Was 'pending')
        existing.document_url = None
        existing.admin_notes = None
        existing.completed_at = None
        existing.reference_number = reference
        existing.updated_at = timezone.now()
        existing.save()
        return JsonResponse({"success": True, "application_id": existing.id, "restarted": True})

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
            document_status='draft',  # <--- CHANGE THIS (Was 'pending')
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
        return JsonResponse({"success": False, "error": "Login required"}, status=401)

    try:
        data = json.loads(request.body.decode()) if request.body else {}
    except:
        data = {}

    mark_completed = data.get("mark_completed", False)
    new_step = data.get("step_index")

    try:
        app = ServiceApplication.objects.get(id=app_id, user_id=user["id"])
    except ServiceApplication.DoesNotExist:
        return JsonResponse({"success": False, "error": "Application not found"}, status=404)

    # When user clicks "Complete" → reset so they can upload
    # When user clicks "Complete" → reset so they can upload
    if mark_completed:
        app.step_index = 0
        app.progress = 0      
        app.document_status = 'draft' # <--- CHANGE THIS (Was 'pending')
        app.document_url = None
        app.admin_notes = None
        app.completed_at = None
        app.save()
        return JsonResponse({"success": True, "message": "Ready for upload"})

    if new_step is None:
        return JsonResponse({"success": False, "error": "step_index required"}, status=400)

    try:
        new_step = int(new_step)
    except:
        return JsonResponse({"success": False, "error": "Invalid step"}, status=400)

    svc = _get_service_by_id(service)
    steps = svc.steps if svc else []
    total = len(steps) or 1
    new_step = max(0, min(new_step, total - 1))
    progress = int((new_step + 1) / total * 100)

    app.step_index = new_step
    app.progress = progress
    app.save()

    return JsonResponse({"success": True, "progress": progress, "step_index": new_step})


@csrf_exempt
@require_POST
def upload_permit_document(request, service: str, app_id):
    user = get_authed_user(request)
    if not user:
        return JsonResponse({"success": False, "error": "Login required"}, status=401)

    try:
        app = ServiceApplication.objects.get(id=app_id, user_id=user["id"])
    except ServiceApplication.DoesNotExist:
        return JsonResponse({"success": False, "error": "App not found"}, status=404)

    if 'document' not in request.FILES:
        return JsonResponse({"success": False, "error": "No file"}, status=400)

    file = request.FILES['document']

    if file.size > 15 * 1024 * 1024:
        return JsonResponse({"success": False, "error": "File too big"}, status=400)

    try:
        url = upload_to_cloudinary(file, folder=f"permits/{service}/{app_id}")
        
        # THIS IS THE KEY FIX
        app.document_url = url
        app.document_status = "pending"   # ← THIS TRIGGERS YOUR TEMPLATE SUCCESS BOX
        app.progress = 100
        app.completed_at = timezone.now()
        app.save()

        return JsonResponse({
            "success": True,
            "message": "Application submitted!",
            "document_url": url
        })
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return JsonResponse({"success": False, "error": "Server error"}, status=500)

def permit_progress_view(request, service: str, app_id):
    user = get_authed_user(request)
    if not user:
        return redirect("login")

    try:
        # 1. Get the application (must belong to user + match service)
        app_obj = ServiceApplication.objects.get(
            id=app_id,
            user_id=user["id"],
            service_type=service
        )

        # 2. Get the Service object using the service_id string (e.g., 'business-permit')
        svc = Service.objects.get(service_id=service)

        # 3. Extract steps & details (JSONField → auto-decoded to Python list)
        steps = svc.steps or []
        step_details = svc.step_details or []

        total_steps = len(steps)
        current_idx = app_obj.step_index or 0

        # Clamp index
        if total_steps > 0 and current_idx >= total_steps:
            current_idx = total_steps - 1

        # Recalculate progress
        progress = 100 if total_steps == 0 else int(((current_idx + 1) / total_steps) * 100)

        # Optional: Fix outdated DB values
        if app_obj.progress != progress or app_obj.step_index != current_idx:
            app_obj.progress = progress
            app_obj.step_index = current_idx
            app_obj.save(update_fields=['progress', 'step_index'])

        context = {
            "authed_user": user,
            "user": user,
            "service": svc,
            "app": {
                "id": app_obj.id,
                "reference_number": app_obj.reference_number or "N/A",
                "progress": progress,
                "step_index": current_idx,
                "document_url": app_obj.document_url,
                "document_status": app_obj.document_status or 'pending',
                "admin_notes": app_obj.admin_notes,
            },
            "current_tab": "services",
        }

        return render(request, "mycebu_app/pages/permit_progress.html", context)

    except ServiceApplication.DoesNotExist:
        return HttpResponse("Application not found or you don't have access.", status=404)
    except Service.DoesNotExist:
        return HttpResponse(f"Service '{service}' configuration not found in database.", status=404)
    except Exception as e:
        logger.error(f"permit_progress_view error: {e}", exc_info=True)
        return HttpResponse("Internal server error.", status=500)

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
            status="Pending",
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
                "photo": o.photo if o.photo else None, 
                "initials": o.initials or (o.name[:2].upper() if o.name else "??"),
                "email": o.email or None,
                "phone": o.phone or None
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
    
@csrf_exempt
@require_POST
def chat_send_view(request):
    user = get_authed_user(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    try:
        data = json.loads(request.body)
        user_message = data.get('prompt', '').strip()
        conversation_id = data.get('conversation_id')
        
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        if not user_message:
            return JsonResponse({'error': 'Prompt is required'}, status=400)

        manual_content = ""
        
        try:
            file_path = os.path.join(
                settings.BASE_DIR, 
                'static', 
                'mycebu_app', 
                'data', 
                'AI_CHATBOT_GUIDE.txt'
            )
            
            if not os.path.exists(file_path):
                file_path = os.path.join(
                    settings.BASE_DIR,
                    'mycebu_app',
                    'static',
                    'mycebu_app',
                    'data',
                    'AI_CHATBOT_GUIDE.txt'
                )

            with open(file_path, 'r', encoding='utf-8') as f:
                manual_content = f.read()
                
        except Exception as e:
            logger.error(f"Error reading knowledge base at {file_path}: {e}")
            manual_content = "System Note: Knowledge base unavailable."

        recent_history_qs = ChatHistory.objects.filter(
            conversation_id=conversation_id, 
            user_id=user['id']
        ).order_by('-created_at')[:5]
        
        recent_history = list(recent_history_qs)[::-1]
        
        history_str = ""
        last_user_topic = ""
        
        for h in recent_history:
            history_str += f"User: {h.user_message}\nMyCebu AI: {h.bot_response}\n"
            if len(h.user_message.split()) > 2:
                last_user_topic = h.user_message

        search_query = user_message.lower()
        if len(search_query.split()) < 4 and last_user_topic:
            search_query += " " + last_user_topic.lower()

        context_data = []

        if any(w in search_query for w in ['permit', 'license', 'clearance', 'business', 'apply', 'service', 'registration']):
            services = Service.objects.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(title__icontains="Business")
            ).distinct()[:5]
            for s in services:
                reqs = ", ".join(s.requirements) if s.requirements else "See manual."
                context_data.append(f"[DB: Service] {s.title}: {s.description}. Req: {reqs}")

        roles = ['mayor', 'vice mayor', 'councilor', 'captain', 'chief', 'head', 'director', 'official']
        found_role = next((r for r in roles if r in search_query), None)
        
        if found_role:
            officials = Official.objects.filter(position__icontains=found_role)[:50]
        else:
            officials = Official.objects.filter(
                Q(name__icontains=search_query) | 
                Q(position__icontains=search_query)
            )[:5]

        for o in officials:
            context_data.append(f"[DB: Official] {o.name} ({o.position}) - {o.office}")

        if 'ordinance' in search_query or 'law' in search_query:
            ordinances = Ordinance.objects.filter(name_or_ordinance__icontains=search_query)[:3]
            for o in ordinances:
                context_data.append(f"[DB: Ordinance] {o.ordinance_number} - {o.name_or_ordinance}")

        if any(x in search_query for x in ['emergency', 'hotline', 'police', 'fire']):
            emergencies = EmergencyContact.objects.all()
            for e in emergencies:
                context_data.append(f"[DB: Emergency] {e.service}: {e.numbers}")

        db_records_str = "\n".join(context_data) if context_data else "No specific database records found."

        system_instruction = (
            "You are 'MyCebu', the Cebu City government assistant.\n"
            "You have access to a STATIC USER MANUAL (Local File) and DYNAMIC DATABASE RECORDS.\n\n"
            "INSTRUCTIONS:\n"
            "1. For general questions (how to apply, navigation, FAQs), use the USER MANUAL content below.\n"
            "2. For specific questions (who is the mayor, specific service requirements), use the DATABASE RECORDS.\n"
            "3. If the user asks for 'another one', check the CHAT HISTORY.\n"
            "4. Use **bold** for titles/names.\n"
            "\n"
            f"=== USER MANUAL (General Info) ===\n{manual_content[:30000]}\n\n"
            f"=== DATABASE RECORDS (Specific Data) ===\n{db_records_str}\n\n"
            f"=== CHAT HISTORY ===\n{history_str}\n"
        )

        model = genai.GenerativeModel('gemini-2.5-flash')
        full_prompt = f"{system_instruction}\n\nUser Question: {user_message}"
        
        response = model.generate_content(full_prompt)
        bot_reply = response.text

        ChatHistory.objects.create(
            user_id=user['id'],
            conversation_id=conversation_id,
            user_message=user_message,
            bot_response=bot_reply
        )

        return JsonResponse({
            'success': True,
            'message': bot_reply,
            'conversation_id': conversation_id
        })

    except Exception as e:
        logger.error(f"Gemini Chat Error: {str(e)}")
        return JsonResponse({'error': f'Failed to process request: {str(e)}'}, status=500)

@require_GET
def chat_history_view(request):
    user = get_authed_user(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        all_chats = ChatHistory.objects.filter(user_id=user['id']).order_by('-created_at')
        sessions = []
        seen_ids = set()
        
        for chat in all_chats:
            c_id = str(chat.conversation_id)
            if c_id not in seen_ids:
                seen_ids.add(c_id)
                sessions.append({
                    "conversation_id": c_id,
                    "title": chat.user_message[:50] + "...", 
                    "date": chat.created_at
                })
        
        return JsonResponse({'success': True, 'history': sessions})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_GET
def chat_session_detail_view(request, conversation_id):
    user = get_authed_user(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    try:
        messages = ChatHistory.objects.filter(
            user_id=user['id'], 
            conversation_id=conversation_id
        ).order_by('created_at') 
        
        data = []
        for m in messages:
            data.append({"text": m.user_message, "type": "user"})
            data.append({"text": m.bot_response, "type": "bot"})

        return JsonResponse({'success': True, 'messages': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
@require_GET
def my_applications_api(request):
    user = get_authed_user(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    
    # Fetch applications for this user
    apps = ServiceApplication.objects.filter(user_id=user['id']).order_by('-updated_at')
    
    data = []
    for app in apps:
        # Get service title safely
        svc_title = "Unknown Service"
        svc_slug = ""
        try:
            svc = Service.objects.get(service_id=app.service_type)
            svc_title = svc.title
            svc_slug = svc.service_id
        except Service.DoesNotExist:
            svc_title = app.service_type

        data.append({
            'id': str(app.id),
            'service_name': svc_title,
            'service_slug': svc_slug, # Needed for the link
            'reference_number': app.reference_number,
            'status': app.document_status or 'pending',
            'progress': app.progress,
            'step_index': app.step_index,
            'admin_notes': app.admin_notes,
            'created_at': app.created_at,
        })
    
    return JsonResponse({'success': True, 'applications': data})
from django.http import JsonResponse, HttpResponse
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
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import uuid
import time
from django.views.decorators.http import require_GET, require_POST
from pathlib import Path
from django.conf import settings
import json

supabase_admin = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
    access_token = request.COOKIES.get('sb-access-token')
    logger.debug(f"get_authed_user: sb-access-token={'present' if access_token else 'missing'}")
    
    if not access_token:
        logger.debug("get_authed_user: No sb-access-token found in cookies")
        return None

    supabase_user = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    try:
        user_resp = supabase_user.auth.get_user(access_token)
        logger.debug(f"get_authed_user: get_user response={user_resp}")
        
        user = getattr(user_resp, "user", None)
        if not user or not getattr(user, "id", None):
            logger.debug("get_authed_user: No valid user found for token")
            return None

        meta = getattr(user, "user_metadata", {}) or {}
        email = getattr(user, "email", None) or meta.get("email")

        display_name = email.split("@")[0] if email else "User"
        avatar_url = None

        try:
            user_data_resp = supabase_admin.table("users").select(
                "first_name, middle_name, last_name, age, birthdate, avatar_url, contact_number, gender, marital_status, religion, birthplace, purok, city"
            ).eq("id", user.id).execute()
            
            if user_data_resp.data and len(user_data_resp.data) > 0:
                ud = user_data_resp.data[0]
                # Build display name from user data
                first_name = ud.get("first_name") or ""
                last_name = ud.get("last_name") or ""
                if first_name or last_name:
                    display_name = f"{first_name} {last_name}".strip()
                avatar_url = ud.get("avatar_url")
            else:
                logger.debug("get_authed_user: No user data found in users table")
        except Exception as e:
            logger.error(f"get_authed_user: Error querying users table: {str(e)}")

        if not avatar_url and display_name:
            initials = "".join([part[0].upper() for part in display_name.split()[:2] if part])
            avatar_url = f"https://placehold.co/100x100/E2E8F0/4A5568?text={initials}"

        user_data_resp = supabase_admin.table("users").select(
            "first_name, middle_name, last_name, age, birthdate, avatar_url, contact_number, gender, marital_status, religion, birthplace, purok, city"
        ).eq("id", user.id).execute()
        ud = user_data_resp.data[0] if user_data_resp.data else {}

        return {
            "id": user.id,
            "email": email,
            "first_name": ud.get("first_name"),
            "middle_name": ud.get("middle_name"),
            "last_name": ud.get("last_name"),
            "display_name": display_name,
            "avatar_url": avatar_url,
            "age": ud.get("age"),
            "birthdate": ud.get("birthdate"),
            "contact_number": ud.get("contact_number"),
            "gender": ud.get("gender"),
            "marital_status": ud.get("marital_status"),
            "religion": ud.get("religion"),
            "birthplace": ud.get("birthplace"),
            "purok": ud.get("purok"),
            "city": ud.get("city"),
        }
    except Exception as e:
        logger.error(f"get_authed_user: Error validating token: {str(e)}")
        return None

@require_GET
def root_router_view(request):
    user = get_authed_user(request)
    if user:
        return redirect("landing_tab", tab="dashboard")
    return redirect("landing_tab", tab="landing")
                    
def profile_view(request):
    user = get_authed_user(request)
    logger.debug(f"profile_view: User: {user}")
    if not user:
        logger.debug("profile_view: Redirecting to login, no authenticated user")
        return redirect("login")

    if request.method == "GET" and request.headers.get('Accept') == 'application/json':
        return JsonResponse({'user': user})

    if request.method == "POST":
        try:
            first_name = request.POST.get("first_name", "").strip()
            middle_name = request.POST.get("middle_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()
            email = request.POST.get("email")
            contact_number = request.POST.get("contact_number")
            birthdate = request.POST.get("birthdate")
            age = request.POST.get("age")
            gender = request.POST.get("gender")
            marital_status = request.POST.get("marital_status")
            religion = request.POST.get("religion")
            birthplace = request.POST.get("birthplace", "").strip()
            purok = request.POST.get("purok")
            city = request.POST.get("city", "").strip()

            errors = {}
            if not first_name or not last_name:
                errors["name"] = "First name and last name are required."
            
            if first_name:
                name_error = validate_name_field(first_name, "First name")
                if name_error:
                    errors["first_name"] = name_error
            
            if middle_name:
                name_error = validate_name_field(middle_name, "Middle name")
                if name_error:
                    errors["middle_name"] = name_error
            
            if last_name:
                name_error = validate_name_field(last_name, "Last name")
                if name_error:
                    errors["last_name"] = name_error
            
            if birthplace:
                name_error = validate_name_field(birthplace, "Birthplace")
                if name_error:
                    errors["birthplace"] = name_error
            
            if city:
                name_error = validate_name_field(city, "City")
                if name_error:
                    errors["city"] = name_error
            
            if email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                errors["email"] = "Invalid email format."
            if age:
                try:
                    age_int = int(age)
                    if age_int < 0 or age_int > 120:
                        errors["age"] = "Age must be between 0 and 120."
                except ValueError:
                    errors["age"] = "Age must be a valid number."

            if errors:
                messages.error(request, "Please correct the errors in the form.")
                response = render(request, "mycebu_app/pages/profile.html", {"user": user, "errors": errors})
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
                return response

            avatar_url = user["avatar_url"]
            if "avatar" in request.FILES:
                avatar_file = request.FILES["avatar"]
                file_name = f"avatars/{user['id']}/{uuid.uuid4()}{os.path.splitext(avatar_file.name)[1]}"
                file_path = default_storage.save(file_name, ContentFile(avatar_file.read()))
                avatar_url = default_storage.url(file_path)

            user_data = {
                "first_name": first_name,
                "middle_name": middle_name if middle_name else None,
                "last_name": last_name,
                "email": email,
                "contact_number": contact_number or None,
                "birthdate": birthdate or None,
                "age": int(age) if age else None,
                "gender": gender or None,
                "marital_status": marital_status or None,
                "religion": religion or None,
                "birthplace": birthplace if birthplace else None,
                "purok": purok or None,
                "city": city if city else None,
                "avatar_url": avatar_url,
            }

            logger.debug(f"profile_view: Updating user {user['id']} with data: {user_data}")
            result = supabase_admin.table("users").update(user_data).eq("id", user["id"]).execute()
            logger.debug(f"profile_view: Update result: {result}")

            if result.data:
                messages.success(request, "Profile updated successfully.")
                user = get_authed_user(request)
                if not user:
                    logger.error("profile_view: Failed to refresh user data after update")
                    messages.error(request, "Profile updated, but failed to refresh user data.")
            else:
                logger.error(f"profile_view: Update failed, result: {result}")
                messages.error(request, "Failed to update profile in database.")

            response = render(request, "mycebu_app/pages/profile.html", {"user": user})
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
        except Exception as e:
            logger.error(f"profile_view: Update error: {str(e)}")
            messages.error(request, f"An error occurred while updating the profile: {str(e)}")
            response = render(request, "mycebu_app/pages/profile.html", {"user": user})
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response

    response = render(request, "mycebu_app/pages/profile.html", {"user": user})
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response



@csrf_exempt
def chat_view(request):
    if request.method != 'POST':
        logger.debug("chat_view: Non-POST request received")
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user = get_authed_user(request)
    if not user or not user.get("id"):
        logger.debug("chat_view: Authentication required")
        return JsonResponse({'error': 'Authentication required'}, status=401)

    try:
        data = json.loads(request.body)
        prompt = data.get('prompt', '').strip()

        if not prompt:
            logger.debug("chat_view: Prompt is empty")
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
            logger.error(f"chat_view: API failed - HTTP: {response.status_code}, Response: {response.text[:200]}")
            bot_message = "I'm having trouble connecting to my AI brain right now. Can you try asking again?"

        logger.debug(f"chat_view: Success, bot_message: {bot_message[:50]}...")
        return JsonResponse({
            'success': True,
            'message': bot_message
        })

    except requests.exceptions.RequestException as e:
        logger.error(f"chat_view: API Request Error: {str(e)}")
        return JsonResponse({'error': f'Failed to process request: {str(e)}'}, status=500)
    except Exception as e:
        logger.error(f"chat_view: General Error: {str(e)}")
        return JsonResponse({'error': f'Failed to process request: {str(e)}'}, status=500)

def chatbot_page(request):
    user = get_authed_user(request)
    logger.debug(f"chatbot_page: User: {user}")
    if not user:
        logger.debug("chatbot_page: Redirecting to login, no authenticated user")
        return redirect("login")
    
    response = render(request, 'mycebu_app/test.html', {"user": user})
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
                    
def landing_view(request, tab='landing'):
    user = get_authed_user(request)
    if tab == 'dashboard' and not user:
        logger.debug("landing_view: Redirecting to login, no authenticated user for dashboard")
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
            if q and q not in name_pos:
                return False
            if position != "all" and o.get("position") != position:
                return False
            if district != "all" and o.get("district") != district:
                return False
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
        # Load ordinances data
        json_path = os.path.join(settings.BASE_DIR, 'static', 'mycebu_app', 'data', 'ordinance.json')
        data = []
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            pass  # data remains []

        # Filter Logic
        query = request.GET.get('q', '').lower()
        category_filter = request.GET.get('category', '')
        author_filter = request.GET.get('author', '')

        filtered_data = []

        # Create lists for dropdowns
        categories_list = sorted(list(set(item['category'] for item in data if item.get('category'))))
        authors_list = sorted(list(set(item['author'] for item in data if item.get('author') and item['author'] != "TO BE UPDATED")))

        for item in data:
            # Check matches
            matches_q = query in item.get('name_or_ordinance', '').lower() or query in item.get('ordinance_number', '')
            matches_cat = category_filter == "" or item.get('category') == category_filter
            matches_auth = author_filter == "" or item.get('author') == author_filter

            if matches_q and matches_cat and matches_auth:
                filtered_data.append(item)

        context.update({
            'ordinances_data': filtered_data,
            'categories_list': categories_list,
            'authors_list': authors_list,
        })

    try:
        response = render(request, f"mycebu_app/pages/{tab}.html", context)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    except TemplateDoesNotExist:
        response = render(request, "mycebu_app/pages/coming_soon.html", context)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response


def logout_view(request):
    logger.debug(f"logout_view: Request method: {request.method}, cookies: {request.COOKIES}")
    if request.method == "POST":
        try:
            access_token = request.COOKIES.get('sb-access-token')
            if access_token:
                supabase_user = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                supabase_user.auth.sign_out()
                logger.debug("logout_view: Supabase sign_out called")
        except Exception as e:
            logger.error(f"logout_view: Supabase sign_out error: {str(e)}")
        
        request.session.flush()
        storage = messages.get_messages(request)
        for _ in storage:
            pass
        storage.used = True

        response = redirect('login')
        response.delete_cookie('sb-access-token', path='/')
        response.delete_cookie('sb-refresh-token', path='/')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        logger.debug("logout_view: Logout successful, cookies cleared")
        return response
    
    logger.debug("logout_view: Non-POST request, redirecting to login")
    return redirect('login')

def validate_name_field(name, field_label):
    """Validate that a name field contains only letters, spaces, hyphens, and apostrophes"""
    if not name:
        return None
    if not re.match(r"^[a-zA-Z\s'-]+$", name):
        return f"{field_label} should only contain letters, spaces, hyphens, and apostrophes."
    return None


def _get_service_by_id(service_id):
    data_path = Path(settings.BASE_DIR) / "static" / "mycebu_app" / "data" / "services.json"
    if not data_path.exists():
        return None
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        services = payload.get("services", [])
        return next((s for s in services if s.get("id") == service_id), None)
    except Exception as e:
        logger.error(f"_get_service_by_id: {e}")
        return None

def apply_permit_view(request, service: str):
    """
    Show the apply page for any service (service is the service id from services.json).
    Template: templates/mycebu_app/pages/apply_permit.html
    """
    user = get_authed_user(request)
    if not user:
        return redirect("login")

    svc = _get_service_by_id(service)
    if not svc:
        return HttpResponse("Service not found", status=404)

    existing_app_id = None
    try:
        resp = supabase_admin.table("service_applications").select("*") \
            .eq("user_id", user["id"]).eq("service_type", service).execute()
        rows = getattr(resp, "data", []) or []
        # consider "in-progress" only if progress>0 or step_index>0
        in_progress = [r for r in rows if (r.get("progress", 0) or 0) > 0 or (r.get("step_index", 0) or 0) > 0]
        if in_progress:
            in_progress.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
            existing_app_id = in_progress[0].get("id")
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
    """
    POST: start or restart application for given service.
    Body (json): { "restart": true/false, "reference_number": "optional-ref" }
    """
    user = get_authed_user(request)
    if not user:
        return JsonResponse({"success": False, "error": "Not authenticated"}, status=401)

    try:
        body = json.loads(request.body or "{}")
    except Exception:
        body = {}

    restart = bool(body.get("restart", False))
    reference = body.get("reference_number") or f"{service.upper()}-{int(time.time())}"

    # lookup existing record for user+service
    existing = None
    try:
        resp = supabase_admin.table("service_applications").select("*") \
            .eq("user_id", user["id"]).eq("service_type", service).execute()
        rows = getattr(resp, "data", []) or []
        existing = rows[0] if rows else None
    except Exception as e:
        logger.debug("start_service_application: lookup error: %s", e)
        existing = None

    if restart and existing:
        try:
            upd = {"progress": 0, "step_index": 0, "reference_number": reference, "updated_at": "now()"}
            res = supabase_admin.table("service_applications").update(upd).eq("id", existing.get("id")).execute()
            if getattr(res, "data", None):
                return JsonResponse({"success": True, "application_id": existing.get("id"), "restarted": True})
        except Exception as e:
            logger.error("start_service_application: restart failed: %s", e)
            return JsonResponse({"success": False, "error": "Failed to restart application"}, status=500)

    # reuse in-progress if exists and not restarting
    if not restart and existing:
        if (existing.get("progress", 0) or 0) > 0 or (existing.get("step_index", 0) or 0) > 0:
            return JsonResponse({"success": True, "application_id": existing.get("id"), "existing": True})

    # create new record (or reuse zeroed existing)
    payload = {
        "user_id": user["id"],
        "service_type": service,
        "reference_number": reference,
        "progress": 0,
        "step_index": 0,
        "created_at": "now()",
        "updated_at": "now()",
    }

    try:
        # if existing row present but zeroed, update timestamps and return
        if existing and (existing.get("progress", 0) == 0 and existing.get("step_index", 0) == 0):
            res = supabase_admin.table("service_applications").update({"updated_at": "now()", "reference_number": reference}).eq("id", existing.get("id")).execute()
            if getattr(res, "data", None):
                return JsonResponse({"success": True, "application_id": existing.get("id"), "existing": True})

        result = supabase_admin.table("service_applications").insert(payload).execute()
        if getattr(result, "data", None):
            app_id = result.data[0].get("id")
            return JsonResponse({"success": True, "application_id": app_id})
        return JsonResponse({"success": False, "error": "Failed to create application"}, status=400)
    except Exception as e:
        logger.error("start_service_application: create error: %s", e)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_POST
def update_service_application(request, service: str, app_id):
    """
    Update step_index/progress or mark completed (resets to zero).
    POST body JSON: { "step_index": int } OR { "mark_completed": true }
    """
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
        if mark_completed:
            # reset to 0 (user asked to complete -> we reset progress)
            update_data = {"step_index": 0, "progress": 0, "updated_at": "now()"}
            res = supabase_admin.table("service_applications").update(update_data).eq("id", str(app_id)).execute()
            if getattr(res, "data", None):
                return JsonResponse({"success": True, "progress": 0, "completed": True})
            return JsonResponse({"success": False, "error": "Failed to mark completed"}, status=400)

        if new_step is None:
            return JsonResponse({"success": False, "error": "step_index required"}, status=400)

        new_step = int(new_step)
        if new_step < 0:
            new_step = 0
        if new_step >= total_steps:
            new_step = total_steps - 1

        # compute progress: treat step_index 0 as first step => (step_index+1)/total_steps
        progress = int(((new_step + 1) / max(total_steps, 1)) * 100)

        update_data = {"step_index": new_step, "progress": progress, "updated_at": "now()"}
        res = supabase_admin.table("service_applications").update(update_data).eq("id", str(app_id)).execute()
        if getattr(res, "data", None):
            return JsonResponse({"success": True, "progress": progress, "step_index": new_step})
        return JsonResponse({"success": False, "error": "Failed to update application"}, status=400)
    except Exception as e:
        logger.error("update_service_application: %s", e)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def permit_progress_view(request, service: str, app_id):
    """
    Show progress page for generic service application.
    Template: templates/mycebu_app/pages/permit_progress.html
    """
    user = get_authed_user(request)
    if not user:
        return redirect("login")

    try:
        result = supabase_admin.table("service_applications").select("*").eq("id", str(app_id)).execute()
        rows = getattr(result, "data", []) or []
        if not rows:
            return HttpResponse("Application not found", status=404)
        application = rows[0]
        svc = _get_service_by_id(service)
        return render(request, "mycebu_app/pages/permit_progress.html", {
            "authed_user": user,
            "user": user,
            "service": svc,
            "app": application,
            "current_tab": "services",
        })
    except Exception as e:
        logger.error(f"permit_progress_view: {e}")
        return HttpResponse("Error loading application", status=500)
def ordinances_view(request):
    # 1. Define path to your JSON file
    # Assuming the json file is in your 'static' folder or root app folder
    # Update this path to where your actual file is located
    json_path = os.path.join(settings.BASE_DIR, 'static', 'mycebu_app', 'data', 'ordinance.json')

    data = []
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("JSON file not found")

    # 2. Filter Logic (Python side since we are using JSON)
    query = request.GET.get('q', '').lower()
    category_filter = request.GET.get('category', '')
    author_filter = request.GET.get('author', '')

    filtered_data = []
    
    # Create lists for dropdowns
    categories_list = sorted(list(set(item['category'] for item in data if item.get('category'))))
    authors_list = sorted(list(set(item['author'] for item in data if item.get('author') and item['author'] != "TO BE UPDATED")))

    for item in data:
        # Check matches
        matches_q = query in item.get('name_or_ordinance', '').lower() or query in item.get('ordinance_number', '')
        matches_cat = category_filter == "" or item.get('category') == category_filter
        matches_auth = author_filter == "" or item.get('author') == author_filter

        if matches_q and matches_cat and matches_auth:
            filtered_data.append(item)

    # 3. Pass to template
    context = {
        'ordinances_data': filtered_data,
        'categories_list': categories_list,
        'authors_list': authors_list,
    }
    return render(request, 'mycebu_app/pages/ordinances.html', context)

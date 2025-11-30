from django.urls import path
from . import views

urlpatterns = [
    path('', views.root_router_view, name='home'),
    path('test/', views.chatbot_page, name='chatbot_page'),
    path('chat/', views.chat_view, name='chat_view'),
    path('profile/', views.profile_view, name='user_profile'),
    path('logout/', views.logout_view, name='logout'),

    # --- REMOVE THE ADMIN-DASHBOARD LINE COMPLETELY ---
    # We will rely on the dynamic <str:tab> below.
    # --------------------------------------------------

    path('dashboard/', views.landing_view, {'tab': 'dashboard'}, name='dashboard'),
    path('landing/', views.landing_view, {'tab': 'landing'}, name='landing_default'),
    
    # This single line handles 'admin_dashboard', 'services', 'about', etc.
    path('<str:tab>/', views.landing_view, name='landing_tab'),
    path('admin-action/<str:action_type>/', views.admin_action_view, name='admin_action'),

    path('api/services/', views.service_list_api, name='api_service_list'),
    path('api/directory/', views.directory_list_api, name='api_directory_list'),
    # ... keep your other paths (apply, complaints) ...
    path("apply/<str:service>/", views.apply_permit_view, name="apply_permit"),
    path("apply/<str:service>/start/", views.start_service_application, name="start_service_application"),
    path("apply/<str:service>/<uuid:app_id>/", views.permit_progress_view, name="permit_progress"),
    path("apply/<str:service>/<uuid:app_id>/update/", views.update_service_application, name="update_service_application"),

    path("complaints/submit/", views.submit_complaint_view, name="submit_complaint"),
    path("complaints/list/", views.list_complaints_view, name="list_complaints"),
    path("complaints/<uuid:complaint_id>/", views.complaint_detail_view, name="complaint_detail"),
    path("complaints/<uuid:complaint_id>/status/", views.update_complaint_status_view, name="update_complaint_status"),
]
from django.urls import path
from . import views

urlpatterns = [
    path('', views.root_router_view, name='home'),
    
    path('test/', views.chatbot_page, name='chatbot_page'),
    path('chat/', views.chat_view, name='chat_view'),
    
    path('profile/', views.profile_view, name='user_profile'),

    path('logout/', views.logout_view, name='logout'),

    path('dashboard/', views.landing_view, {'tab': 'dashboard'}, name='dashboard'),
    path('landing/', views.landing_view, {'tab': 'landing'}, name='landing_default'),
    path('<str:tab>/', views.landing_view, name='landing_tab'),

    path("apply/business-permit/", views.apply_business_permit_view, name="apply_business_permit"),
    path("apply/business-permit/start/", views.start_business_permit_application, name="start_business_permit"),
    path("apply/business-permit/<uuid:app_id>/", views.permit_progress_view, name="permit_progress"),
    path("apply/business-permit/<uuid:app_id>/update/", views.update_business_permit_step, name="update_business_permit"),

]
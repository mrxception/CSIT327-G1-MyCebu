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
]
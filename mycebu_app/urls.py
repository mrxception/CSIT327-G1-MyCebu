from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name="register"),
    path('login/', views.login_view, name="login"),
    path('test/', views.chatbot_page, name='chatbot_page'),
    path('chat/', views.chat_view, name='chat_view'),
    path('register-success/', views.register_success_view, name='register_success'),
    path('password-reset-email/', views.password_reset_email_view, name='password_reset_email'),
    path('password-reset-new-password/', views.password_reset_new_password_view, name='password_reset_new_password'),
    path('password-reset-success/', views.password_reset_success_view, name='password_reset_success'),
    path('profile/', views.profile_view, name='user_profile'),

    path('logout/', views.logout_view, name='logout'),

    # Root landing
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('', views.landing_view, {'tab': 'landing'}, name='landing_default'),
    
    # Catch-all for tabs (logout won't reach here now)
    path('<str:tab>/', views.landing_view, name='landing_tab'), 
]
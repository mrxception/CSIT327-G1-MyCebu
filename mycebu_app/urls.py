from django.urls import path
from . import views

urlpatterns = [
    #path('', views.landing_view, name='landing'),
    #path('landing/', views.landing_view, name='landing'),
    path('register/', views.register_view, name="register"),
    path('login/', views.login_view, name="login"),
    path('test/', views.chatbot_page, name='chatbot_page'),
    path('chat/', views.chat_view, name='chat_view'),
    path('register-success/', views.register_success_view, name='register_success'),
    path('password-reset-email/', views.password_reset_email_view, name='password_reset_email'),
    path('password-reset-new-password/', views.password_reset_new_password_view, name='password_reset_new_password'),
    path('password-reset-success/', views.password_reset_success_view, name='password_reset_success'),

    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('', views.landing_view, {'tab': 'landing'}, name='landing_default'),
    path('<str:tab>/', views.landing_view, name='landing_tab'), 
    # path('logout/', LogoutView.as_view(), name='logout'),
    # path('register/', views.register, name='register'),
    # path('dashboard/', views.dashboard, name='dashboard'),
]